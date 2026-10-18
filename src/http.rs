//! Initial single-owner HTTP adapter. Durable jobs and hosted namespaces are future scope.
use crate::{
    application, backend,
    domain::{Artifact, ArtifactKind, Record, validate_id, validate_name},
    engine::ProfileSelector,
    store::{Metric, Store},
    zkir3,
};
use anyhow::{Context, Result, ensure};
use axum::{
    Json, Router,
    body::{Body, to_bytes},
    extract::{Path, Request, State},
    http::{HeaderMap, Method, StatusCode, header},
    middleware::{self, Next},
    response::{IntoResponse, Response},
    routing::{get, post},
};
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    io::{self, Read, Seek, SeekFrom},
    net::SocketAddr,
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    time::{Duration, Instant},
};
use tokio::{
    io::{AsyncRead, ReadBuf},
    sync::{OwnedSemaphorePermit, Semaphore, mpsc, oneshot},
};
use tokio_util::io::ReaderStream;

const MAX_UPLOAD: usize = 16 * 1024 * 1024;
pub struct Config {
    pub root: PathBuf,
    pub params_dir: Option<PathBuf>,
    pub fetch_params: bool,
    pub profile: Option<ProfileSelector>,
    pub listen: SocketAddr,
    pub token_file: Option<PathBuf>,
    pub provider_root: Option<PathBuf>,
    pub provider_limits: crate::provider_view::Limits,
    pub download_timeout: Duration,
    pub download_min_bytes_per_second: u64,
}
struct Service {
    config: Config,
    token: Option<[u8; 32]>,
    work: Arc<Semaphore>,
    generation: Arc<Semaphore>,
    downloads: Arc<Semaphore>,
    uploads: Arc<Semaphore>,
    provider_reads: Arc<Semaphore>,
    provider_waiters: Arc<Semaphore>,
}
type Shared = Arc<Service>;
#[derive(Debug)]
struct ApiError(StatusCode, &'static str);
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let mut response = (
            self.0,
            Json(json!({"schema":1,"error":{"code":self.1,"message":self.1,"retryable":matches!(self.0,StatusCode::TOO_MANY_REQUESTS|StatusCode::SERVICE_UNAVAILABLE),"availability_fallback":matches!(self.0,StatusCode::TOO_MANY_REQUESTS|StatusCode::SERVICE_UNAVAILABLE|StatusCode::NOT_FOUND)}})),
        )
            .into_response();
        if self.0 == StatusCode::UNAUTHORIZED {
            response
                .headers_mut()
                .insert(header::WWW_AUTHENTICATE, "Bearer".parse().unwrap());
        }
        if self.0 == StatusCode::TOO_MANY_REQUESTS {
            response
                .headers_mut()
                .insert(header::RETRY_AFTER, "1".parse().unwrap());
        }
        response
    }
}
fn bad(code: &'static str) -> ApiError {
    ApiError(StatusCode::BAD_REQUEST, code)
}
fn provider_read_error(error: ApiError) -> ApiError {
    if error.1 == "provider_limit" {
        ApiError(StatusCode::INTERNAL_SERVER_ERROR, error.1)
    } else {
        error
    }
}
fn classify(error: anyhow::Error) -> ApiError {
    let kind = crate::error::classify(&error);
    ApiError(
        StatusCode::from_u16(kind.status()).expect("domain HTTP status"),
        kind.code(),
    )
}
impl Service {
    async fn provider_permit(
        &self,
        wait: Duration,
    ) -> std::result::Result<OwnedSemaphorePermit, ApiError> {
        let busy = || ApiError(StatusCode::TOO_MANY_REQUESTS, "provider_reads_busy");
        if let Ok(permit) = self.provider_reads.clone().try_acquire_owned() {
            return Ok(permit);
        }
        // Bound pending work as well as expensive verification and stream IO.
        let waiting = self
            .provider_waiters
            .clone()
            .try_acquire_owned()
            .map_err(|_| busy())?;
        let permit = tokio::time::timeout(wait, self.provider_reads.clone().acquire_owned())
            .await
            .map_err(|_| busy())?
            .map_err(|_| busy())?;
        drop(waiting);
        Ok(permit)
    }
    // The permit lives in the blocking task, then follows its verified response.
    // Dropping a cancelled HTTP future must not free capacity while hashing runs.
    async fn provider_work<T, F>(
        self: &Arc<Self>,
        task: F,
    ) -> std::result::Result<(T, OwnedSemaphorePermit), ApiError>
    where
        T: Send + 'static,
        F: FnOnce() -> Result<T> + Send + 'static,
    {
        let permit = self.provider_permit(Duration::from_secs(10)).await?;
        tokio::task::spawn_blocking(move || Ok((task()?, permit)))
            .await
            .map_err(|_| ApiError(StatusCode::INTERNAL_SERVER_ERROR, "worker_failed"))?
            .map_err(classify)
    }
    async fn work<T, F>(self: &Arc<Self>, task: F) -> std::result::Result<T, ApiError>
    where
        T: Send + 'static,
        F: FnOnce(&Service, &Store) -> Result<T> + Send + 'static,
    {
        let permit = self
            .work
            .clone()
            .try_acquire_owned()
            .map_err(|_| ApiError(StatusCode::TOO_MANY_REQUESTS, "busy"))?;
        let service = self.clone();
        tokio::task::spawn_blocking(move || {
            let _permit = permit;
            let store = Store::open(&service.config.root)?;
            task(&service, &store)
        })
        .await
        .map_err(|_| ApiError(StatusCode::INTERNAL_SERVER_ERROR, "worker_failed"))?
        .map_err(classify)
    }
}

pub async fn serve(config: Config) -> Result<Value> {
    // Library callers bypass clap validation.
    ensure!(
        config.download_min_bytes_per_second > 0,
        "download minimum bytes per second must be positive"
    );
    ensure!(
        (Duration::from_secs(1)..=Duration::from_secs(3600)).contains(&config.download_timeout),
        "download timeout must be 1..3600 seconds"
    );
    let token = if let Some(path) = &config.token_file {
        let mut bytes = Vec::new();
        File::open(path)?.take(4097).read_to_end(&mut bytes)?;
        ensure!(bytes.len() <= 4096, "token file too large");
        let text = std::str::from_utf8(&bytes)?.trim();
        ensure!(
            text.len() >= 32 && text.bytes().all(|b| b.is_ascii_graphic()),
            "token must be at least 32 printable ASCII characters with no internal whitespace"
        );
        Some(Sha256::digest(text.as_bytes()).into())
    } else {
        None
    };
    ensure!(
        config.listen.ip().is_loopback() || token.is_some(),
        "non-loopback HTTP binding requires --token-file"
    );
    if let Some(provider) = &config.provider_root {
        crate::provider_view::separate_roots(provider, &config.root)?;
        ensure!(
            std::fs::symlink_metadata(provider)?.is_dir()
                && !std::fs::symlink_metadata(provider)?
                    .file_type()
                    .is_symlink(),
            "provider root must be an existing directory"
        );
    }
    // Fail before listening if configured storage/backend is unavailable.
    let store = Store::open(&config.root)?;
    let mut probe = tempfile::NamedTempFile::new_in(store.root.join("staging"))?;
    std::io::Write::write_all(&mut probe, b"ready")?;
    probe.as_file().sync_all()?;
    zkir3::call("profile", &[], None, false, None, None)?;
    crate::zkir31::call("profile", &[], None, false, None, None)?;
    let listener = tokio::net::TcpListener::bind(config.listen).await?;
    eprintln!("Forge HTTP listening on {}", listener.local_addr()?);
    let state = Arc::new(Service {
        config,
        token,
        work: Arc::new(Semaphore::new(8)),
        generation: Arc::new(Semaphore::new(1)),
        downloads: Arc::new(Semaphore::new(8)),
        uploads: Arc::new(Semaphore::new(2)),
        provider_reads: Arc::new(Semaphore::new(2)),
        provider_waiters: Arc::new(Semaphore::new(8)),
    });
    let app = Router::new()
        .route(
            "/health/live",
            get(|| async { Json(json!({"status":"live"})) }),
        )
        .route("/health/ready", get(ready))
        .route(
            "/openapi.json",
            get(|| async {
                Json(
                    serde_json::from_str::<Value>(include_str!("../docs/http/openapi.json"))
                        .unwrap(),
                )
            }),
        )
        .route("/v1/profiles", get(profiles))
        .route("/v1/stats", get(stats))
        .route("/v1/bundles", post(upload))
        .route("/v1/bundles/{id}", get(bundle))
        .route("/v1/bundles/{id}/materializations", post(materialize))
        .route("/v1/bundles/{id}/circuits/{name}/source", get(source))
        .route("/v1/objects/{digest}", get(object))
        .route("/views/{id}/{*file}", get(provider_file))
        .fallback(|| async { ApiError(StatusCode::NOT_FOUND, "not_found") })
        .layer(middleware::from_fn_with_state(state.clone(), guard))
        .with_state(state);
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown())
        .await?;
    Ok(json!({"schema":1,"status":"stopped"}))
}
async fn guard(State(state): State<Shared>, request: Request, next: Next) -> Response {
    if request.uri().path() != "/health/live" {
        if let Some(expected) = state.token {
            let supplied = request
                .headers()
                .get(header::AUTHORIZATION)
                .and_then(|v| v.to_str().ok())
                .and_then(|v| v.strip_prefix("Bearer "));
            let Some(supplied) = supplied else {
                return ApiError(StatusCode::UNAUTHORIZED, "unauthorized").into_response();
            };
            let actual: [u8; 32] = Sha256::digest(supplied.as_bytes()).into();
            if actual
                .iter()
                .zip(expected)
                .fold(0u8, |a, (x, y)| a | (x ^ y))
                != 0
            {
                return ApiError(StatusCode::UNAUTHORIZED, "unauthorized").into_response();
            }
        }
        if request.method() == Method::POST
            && request
                .headers()
                .get(header::CONTENT_TYPE)
                .and_then(|v| v.to_str().ok())
                .is_none_or(|v| v.split(';').next().unwrap_or("").trim() != "application/json")
        {
            return ApiError(
                StatusCode::UNSUPPORTED_MEDIA_TYPE,
                "application_json_required",
            )
            .into_response();
        }
    }
    let mut response = next.run(request).await;
    response
        .headers_mut()
        .insert(header::CACHE_CONTROL, "no-store".parse().unwrap());
    // Immutable objects override this below only after successful verification.
    if response.headers().contains_key(header::ETAG) {
        response.headers_mut().insert(
            header::CACHE_CONTROL,
            "private, max-age=31536000, immutable".parse().unwrap(),
        );
    }
    response
        .headers_mut()
        .insert(header::X_CONTENT_TYPE_OPTIONS, "nosniff".parse().unwrap());
    response
}
fn selected(
    raw: Option<&str>,
    configured: Option<ProfileSelector>,
) -> std::result::Result<Option<ProfileSelector>, ApiError> {
    let requested = match raw {
        None => None,
        Some("ledger8-v2") => Some(ProfileSelector::Ledger8V2),
        Some("zkir3") => Some(ProfileSelector::Zkir3),
        Some("zkir31") => Some(ProfileSelector::Zkir31),
        _ => return Err(bad("unknown_profile")),
    };
    if requested.is_some() && configured.is_some() && requested != configured {
        return Err(bad("profile_format_mismatch"));
    }
    Ok(requested.or(configured))
}
fn query<T: serde::de::DeserializeOwned>(request: &Request) -> std::result::Result<T, ApiError> {
    axum::extract::Query::<T>::try_from_uri(request.uri())
        .map(|v| v.0)
        .map_err(|_| bad("invalid_query"))
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Upload {
    name: String,
    profile: Option<String>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Selection {
    profile: Option<String>,
}
async fn upload(
    State(state): State<Shared>,
    request: Request,
) -> std::result::Result<impl IntoResponse, ApiError> {
    if request
        .headers()
        .get(header::CONTENT_LENGTH)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.parse::<u64>().ok())
        .is_some_and(|n| n > MAX_UPLOAD as u64)
    {
        return Err(ApiError(StatusCode::PAYLOAD_TOO_LARGE, "upload_too_large"));
    }
    let args: Upload = query(&request)?;
    validate_name(&args.name).map_err(|_| bad("invalid_name"))?;
    let profile = selected(args.profile.as_deref(), state.config.profile)?;
    let upload_permit = state
        .uploads
        .clone()
        .try_acquire_owned()
        .map_err(|_| ApiError(StatusCode::TOO_MANY_REQUESTS, "uploads_busy"))?;
    let bytes = tokio::time::timeout(
        std::time::Duration::from_secs(30),
        to_bytes(request.into_body(), MAX_UPLOAD),
    )
    .await
    .map_err(|_| ApiError(StatusCode::REQUEST_TIMEOUT, "body_timeout"))?
    .map_err(|_| ApiError(StatusCode::PAYLOAD_TOO_LARGE, "upload_too_large"))?;
    let value = state
        .work(move |_, store| {
            let _permit = upload_permit;
            let record =
                application::import_bytes_with_profile(store, &bytes, &args.name, profile)?;
            let ready = store.load(&record.bundle_id.0)?.1;
            record_json(&record, ready, store)
        })
        .await?;
    Ok((StatusCode::CREATED, Json(value)))
}
fn artifact_json(artifact: &Artifact) -> Value {
    json!({"kind":artifact.kind,"sha256":artifact.digest,"bytes":artifact.size,"url":format!("/v1/objects/{}",artifact.digest)})
}
fn record_json(record: &Record, ready: bool, store: &Store) -> anyhow::Result<Value> {
    let descriptor =
        crate::descriptor::ArtifactDescriptor::from_record(record, &store.read(&record.source)?)?;
    Ok(
        json!({"schema":1,"descriptor":descriptor,"bundle_id":record.bundle_id,"name":record.name,"ready":ready,"format":record.format.as_deref().unwrap_or("midnight-zkir-v2-json"),"profile":record.profile,"derivation_id":record.derivation_id,"artifact_set_id":record.artifact_set_id,"source":artifact_json(&record.source),"artifacts":if ready {record.artifacts.iter().map(artifact_json).collect::<Vec<_>>()} else {vec![]}}),
    )
}
async fn bundle(
    State(state): State<Shared>,
    Path(id): Path<String>,
) -> std::result::Result<Json<Value>, ApiError> {
    validate_id(&id).map_err(|_| bad("invalid_id"))?;
    state
        .work(move |_, store| {
            let (r, ready) = store.load(&id)?;
            Ok(Json(record_json(&r, ready, store)?))
        })
        .await
}
async fn materialize(
    State(state): State<Shared>,
    Path(id): Path<String>,
    request: Request,
) -> std::result::Result<Json<Value>, ApiError> {
    validate_id(&id).map_err(|_| bad("invalid_id"))?;
    let args: Selection = query(&request)?;
    let profile = selected(args.profile.as_deref(), state.config.profile)?;
    // No request body parameters or server paths are accepted by this initial API.
    let body = tokio::time::timeout(
        std::time::Duration::from_secs(30),
        to_bytes(request.into_body(), 1),
    )
    .await
    .map_err(|_| ApiError(StatusCode::REQUEST_TIMEOUT, "body_timeout"))?
    .map_err(|_| bad("unexpected_body"))?;
    if !body.is_empty() {
        return Err(bad("unexpected_body"));
    }
    let permit = state
        .generation
        .clone()
        .try_acquire_owned()
        .map_err(|_| ApiError(StatusCode::TOO_MANY_REQUESTS, "materializer_busy"))?;
    state
        .work(move |service, store| {
            let _permit = permit;
            let runtime = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()?;
            let result = runtime.block_on(application::ensure_with_profile(
                store,
                &id,
                &format!("/v1/bundles/{id}/materializations"),
                service.config.params_dir.as_deref(),
                service.config.fetch_params,
                None,
                profile,
            ))?;
            let (record, ready) = store.load(&id)?;
            let mut response = record_json(&record, ready, store)?;
            response["cache"] = result["cache"].clone();
            Ok(Json(response))
        })
        .await
}
async fn profiles(State(state): State<Shared>) -> std::result::Result<Json<Value>, ApiError> {
    state.work(|_,_| {
      let mut profiles = vec![json!({"selector":"ledger8-v2","profile":backend::PROFILE,"source_revision":backend::LEDGER_REV,"format":"midnight-zkir-v2-json"})];
      for (selector,spec) in [("zkir3",&zkir3::SPEC),("zkir31",&crate::zkir31::SPEC)] {
        spec.call("profile",&[],None,false,None,None)?;
        profiles.push(json!({"selector":selector,"profile":spec.profile,"source_revision":spec.revision,"ledger_revision":spec.ledger_revision,"format":spec.format,"json_versions":[format!("3.{}",spec.json_minor)]}));
      }
      Ok(Json(json!({"schema":1,"profiles":profiles})))
    }).await
}

fn redact_paths(value: &mut Value) {
    match value {
        Value::Object(map) => {
            map.remove("requested_path");
            for v in map.values_mut() {
                redact_paths(v);
            }
        }
        Value::Array(a) => {
            for v in a {
                redact_paths(v);
            }
        }
        _ => {}
    }
}
async fn stats(State(state): State<Shared>) -> std::result::Result<Json<Value>, ApiError> {
    state
        .work(|_, store| {
            let mut v = store.stats()?;
            redact_paths(&mut v);
            Ok(Json(v))
        })
        .await
}
async fn ready(State(state): State<Shared>) -> std::result::Result<Json<Value>, ApiError> {
    state
        .work(|_, store| {
            store.db.query_row("SELECT 1", [], |r| r.get::<_, u8>(0))?;
            zkir3::call("profile", &[], None, false, None, None)?;
            crate::zkir31::call("profile", &[], None, false, None, None)?;
            let probe = tempfile::NamedTempFile::new_in(store.root.join("staging"))?;
            probe.as_file().sync_all()?;
            Ok(Json(
                json!({"status":"ready","scope":"storage and backend; not all parameter sizes"}),
            ))
        })
        .await
}
async fn source(
    State(state): State<Shared>,
    Path((id, name)): Path<(String, String)>,
    headers: HeaderMap,
    method: Method,
) -> std::result::Result<Response, ApiError> {
    validate_id(&id).map_err(|_| bad("invalid_id"))?;
    validate_name(&name).map_err(|_| bad("invalid_name"))?;
    let digest = state
        .work(move |_, store| {
            let (r, _) = store.load(&id)?;
            ensure!(r.name == name, crate::error::Kind::NotFound);
            Ok(r.source.digest)
        })
        .await?;
    download(state, digest, headers, method).await
}
async fn object(
    State(state): State<Shared>,
    Path(digest): Path<String>,
    headers: HeaderMap,
    method: Method,
) -> std::result::Result<Response, ApiError> {
    download(state, digest, headers, method).await
}
const DOWNLOAD_CHUNK: usize = 256 * 1024;
fn download_lifetime(base: Duration, min_bytes_per_second: u64, length: u64) -> Duration {
    base.saturating_add(Duration::from_secs(length.div_ceil(min_bytes_per_second)))
        .min(Duration::from_secs(3600))
}
struct DownloadReader {
    receiver: mpsc::Receiver<io::Result<Vec<u8>>>,
    chunk: Vec<u8>,
    position: usize,
    expired: Arc<AtomicBool>,
    remaining: u64,
    finished: Option<oneshot::Sender<()>>,
}
impl AsyncRead for DownloadReader {
    fn poll_read(
        mut self: std::pin::Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
        buf: &mut ReadBuf<'_>,
    ) -> std::task::Poll<std::io::Result<()>> {
        if self.remaining == 0 {
            return std::task::Poll::Ready(Ok(()));
        }
        if self.expired.load(Ordering::Acquire) {
            return std::task::Poll::Ready(Err(io::Error::new(
                io::ErrorKind::TimedOut,
                "download deadline exceeded",
            )));
        }
        if buf.remaining() == 0 {
            return std::task::Poll::Ready(Ok(()));
        }
        loop {
            if self.position < self.chunk.len() {
                let n = buf.remaining().min(self.chunk.len() - self.position);
                buf.put_slice(&self.chunk[self.position..self.position + n]);
                self.position += n;
                self.remaining -= n as u64;
                if self.remaining == 0
                    && let Some(done) = self.finished.take()
                {
                    let _ = done.send(());
                }
                return std::task::Poll::Ready(Ok(()));
            }
            match self.receiver.poll_recv(cx) {
                std::task::Poll::Ready(Some(Ok(chunk))) => {
                    self.chunk = chunk;
                    self.position = 0;
                }
                std::task::Poll::Ready(Some(Err(error))) => {
                    return std::task::Poll::Ready(Err(error));
                }
                std::task::Poll::Ready(None) => {
                    return std::task::Poll::Ready(Err(io::Error::new(
                        io::ErrorKind::UnexpectedEof,
                        "download producer ended before declared length",
                    )));
                }
                std::task::Poll::Pending => return std::task::Poll::Pending,
            }
        }
    }
}
fn download_reader<R: Read + Send + 'static>(
    file: R,
    length: u64,
    permit: OwnedSemaphorePermit,
    lifetime: Duration,
) -> DownloadReader {
    let (sender, receiver) = mpsc::channel(1);
    let (finished, consumed) = oneshot::channel();
    let mut finished = Some(finished);
    if length == 0 {
        let _ = finished.take().unwrap().send(());
    }
    let expired = Arc::new(AtomicBool::new(false));
    let flag = expired.clone();
    tokio::spawn(async move {
        let closed = sender.clone();
        let produce = async move {
            let mut held = (file, permit);
            let mut left = length;
            while left > 0 {
                let read = tokio::task::spawn_blocking(move || {
                    let mut chunk = vec![0; left.min(DOWNLOAD_CHUNK as u64) as usize];
                    let count = held.0.read(&mut chunk)?;
                    if count == 0 {
                        return Err(io::Error::new(
                            io::ErrorKind::UnexpectedEof,
                            "verified file truncated",
                        ));
                    }
                    chunk.truncate(count);
                    Ok((held, chunk))
                })
                .await;
                let (next, chunk) = match read {
                    Ok(Ok(value)) => value,
                    Ok(Err(error)) => {
                        let _ = sender.send(Err(error)).await;
                        return;
                    }
                    Err(_) => {
                        let _ = sender
                            .send(Err(io::Error::other("download worker failed")))
                            .await;
                        return;
                    }
                };
                held = next;
                left -= chunk.len() as u64;
                if sender.send(Ok(chunk)).await.is_err() {
                    return;
                }
            }
            // A queued tail (including an entire small response) is not yet a
            // consumed body. Keep the deadline/lease until it is consumed.
            let _ = consumed.await;
            drop(held);
        };
        tokio::select! {
            _ = closed.closed() => {},
            result = tokio::time::timeout(lifetime, produce) => {
                if result.is_err() {
                    flag.store(true, Ordering::Release);
                    eprintln!("Forge HTTP download expired: response_bytes={length}, deadline_seconds={}", lifetime.as_secs());
                }
            }
        }
    });
    DownloadReader {
        receiver,
        chunk: Vec::new(),
        position: 0,
        expired,
        remaining: length,
        finished,
    }
}
fn range(value: &str, size: u64) -> Option<(u64, u64)> {
    let value = value.strip_prefix("bytes=")?;
    let (first, last) = value.split_once('-')?;
    if size == 0 {
        return None;
    }
    if first.is_empty() {
        let suffix = last.parse::<u64>().ok()?;
        if suffix == 0 {
            return None;
        }
        Some((size.saturating_sub(suffix), size - 1))
    } else {
        let first = first.parse::<u64>().ok()?;
        let last = if last.is_empty() {
            size - 1
        } else {
            last.parse::<u64>().ok()?.min(size - 1)
        };
        if first > last || first >= size {
            None
        } else {
            Some((first, last))
        }
    }
}
async fn download(
    state: Shared,
    digest: String,
    headers: HeaderMap,
    method: Method,
) -> std::result::Result<Response, ApiError> {
    validate_id(&digest).map_err(|_| bad("invalid_id"))?;
    let stream_permit = state
        .downloads
        .clone()
        .try_acquire_owned()
        .map_err(|_| ApiError(StatusCode::TOO_MANY_REQUESTS, "downloads_busy"))?;
    let requested = digest.clone();
    let (file, artifact) = state
        .work(move |_, store| {
            let clock = Instant::now();
            let tx = store.lock()?;
            let mut stmt = store.db.prepare("SELECT record,ready FROM bundles")?;
            let mut rows = stmt.query([])?;
            let mut found = None;
            while let Some(row) = rows.next()? {
                let r: Record = serde_json::from_str(&row.get::<_, String>(0)?)
                    .context(crate::error::Kind::IntegrityError)?;
                let ready: bool = row.get(1)?;
                if r.source.digest == requested {
                    found = Some((r.bundle_id.0, r.source));
                    break;
                }
                if ready && let Some(a) = r.artifacts.iter().find(|a| a.digest == requested) {
                    found = Some((r.bundle_id.0, a.clone()));
                    break;
                }
            }
            let (bundle, artifact) = found.context(crate::error::Kind::NotFound)?;
            let path = store.object_path(&requested)?;
            let meta = std::fs::symlink_metadata(&path).map_err(|error| {
                let kind = if error.kind() == std::io::ErrorKind::NotFound {
                    crate::error::Kind::NotFound
                } else {
                    crate::error::Kind::InternalError
                };
                anyhow::Error::new(error).context(kind)
            })?;
            ensure!(
                meta.is_file() && !meta.file_type().is_symlink(),
                crate::error::Kind::IntegrityError
            );
            let mut file = File::open(path)?;
            ensure!(
                file.metadata()?.len() == artifact.size,
                crate::error::Kind::IntegrityError
            );
            let mut hash = Sha256::new();
            let mut buffer = [0u8; 128 * 1024];
            loop {
                let n = file.read(&mut buffer)?;
                if n == 0 {
                    break;
                }
                hash.update(&buffer[..n]);
            }
            ensure!(
                hex::encode(hash.finalize()) == artifact.digest,
                crate::error::Kind::IntegrityError
            );
            file.seek(SeekFrom::Start(0))?;
            drop(rows);
            drop(stmt);
            store.record_metric(
                &Metric {
                    bundle: &bundle,
                    path: &format!("/v1/objects/{requested}"),
                    operation: "http_download",
                    outcome: "hit",
                    elapsed_ms: clock.elapsed().as_secs_f64() * 1000.0,
                    generation_ms: Some(0.0),
                    saved_ms: 0.0,
                },
                std::slice::from_ref(&artifact),
            )?;
            tx.commit()?;
            Ok((file, artifact))
        })
        .await?;
    file_response(
        file,
        artifact.size,
        &digest,
        if artifact.kind == ArtifactKind::Source {
            "application/json"
        } else {
            "application/octet-stream"
        },
        headers,
        method,
        (
            stream_permit,
            state.config.download_timeout,
            state.config.download_min_bytes_per_second,
        ),
    )
}
async fn provider_file(
    State(state): State<Shared>,
    Path((id, path)): Path<(String, String)>,
    headers: HeaderMap,
    method: Method,
) -> std::result::Result<Response, ApiError> {
    validate_id(&id).map_err(|_| bad("invalid_id"))?;
    let root = state
        .config
        .provider_root
        .clone()
        .ok_or(ApiError(StatusCode::NOT_FOUND, "not_found"))?;
    let content_type = if path.ends_with(".json") || path.ends_with(".zkir") {
        "application/json"
    } else if path.ends_with(".js") {
        "text/javascript"
    } else {
        "application/octet-stream"
    };
    let limits = state.config.provider_limits;
    let ((file, digest, size), permit) = state
        .provider_work(move || {
            let view = root.join(&id);
            if !view.exists() {
                return Err(anyhow::anyhow!(crate::error::Kind::NotFound));
            }
            crate::provider_view::read_with_limits(&view, &id, &path, limits)
        })
        .await
        .map_err(provider_read_error)?;
    file_response(
        file,
        size,
        &digest,
        content_type,
        headers,
        method,
        (
            permit,
            state.config.download_timeout,
            state.config.download_min_bytes_per_second,
        ),
    )
}
fn file_response(
    mut file: File,
    size: u64,
    digest: &str,
    content_type: &str,
    headers: HeaderMap,
    method: Method,
    stream: (OwnedSemaphorePermit, Duration, u64),
) -> std::result::Result<Response, ApiError> {
    let etag = format!("\"{}\"", digest);
    let mut builder = Response::builder()
        .header(header::ETAG, &etag)
        .header(header::ACCEPT_RANGES, "bytes")
        .header(header::CONTENT_TYPE, content_type);
    if headers
        .get(header::IF_NONE_MATCH)
        .and_then(|v| v.to_str().ok())
        .is_some_and(|v| {
            v.split(',')
                .any(|s| s.trim() == "*" || s.trim().trim_start_matches("W/") == etag)
        })
    {
        return Ok(builder
            .status(StatusCode::NOT_MODIFIED)
            .body(Body::empty())
            .unwrap());
    }
    let mut start = 0;
    let mut length = size;
    let mut status = StatusCode::OK;
    // Range applies to GET; RFC HEAD describes the complete representation.
    if method == Method::GET
        && let Some(value) = headers.get(header::RANGE)
    {
        let if_range_matches = headers
            .get(header::IF_RANGE)
            .is_none_or(|v| v.to_str().ok() == Some(&etag));
        if if_range_matches {
            if let Some((first, last)) = value.to_str().ok().and_then(|v| range(v, size)) {
                start = first;
                length = last - first + 1;
                status = StatusCode::PARTIAL_CONTENT;
                builder = builder.header(
                    header::CONTENT_RANGE,
                    format!("bytes {first}-{last}/{}", size),
                );
            } else {
                return Ok(builder
                    .status(StatusCode::RANGE_NOT_SATISFIABLE)
                    .header(header::CONTENT_RANGE, format!("bytes */{}", size))
                    .body(Body::empty())
                    .unwrap());
            }
        }
    }
    builder = builder
        .status(status)
        .header(header::CONTENT_LENGTH, length);
    let body = if method == Method::HEAD {
        Body::empty()
    } else {
        file.seek(SeekFrom::Start(start))
            .map_err(|_| ApiError(StatusCode::INTERNAL_SERVER_ERROR, "read_failed"))?;
        let reader = download_reader(
            file,
            length,
            stream.0,
            download_lifetime(stream.1, stream.2, length),
        );
        Body::from_stream(ReaderStream::with_capacity(reader, DOWNLOAD_CHUNK))
    };
    Ok(builder.body(body).unwrap())
}

async fn shutdown() {
    #[cfg(unix)]
    {
        let mut term = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("install SIGTERM handler");
        tokio::select! { _=tokio::signal::ctrl_c()=>{}, _=term.recv()=>{} }
    }
    #[cfg(not(unix))]
    {
        let _ = tokio::signal::ctrl_c().await;
    }
}

#[cfg(test)]
mod provider_admission_tests {
    use super::*;
    use std::sync::atomic::AtomicUsize;
    use tokio::io::AsyncReadExt;

    struct CountedRead {
        file: File,
        reads: Arc<AtomicUsize>,
    }
    impl Read for CountedRead {
        fn read(&mut self, bytes: &mut [u8]) -> io::Result<usize> {
            let n = self.file.read(bytes)?;
            self.reads.fetch_add(1, Ordering::Release);
            Ok(n)
        }
    }
    fn stream_file() -> File {
        use std::io::Write;
        let mut file = tempfile::tempfile().unwrap();
        file.write_all(&vec![7; 1024 * 1024]).unwrap();
        file.seek(SeekFrom::Start(0)).unwrap();
        file
    }
    async fn wait_reads(count: &AtomicUsize, expected: usize) {
        let limit = std::time::Instant::now() + Duration::from_secs(5);
        while count.load(Ordering::Acquire) < expected {
            assert!(std::time::Instant::now() < limit, "read barrier timed out");
            tokio::task::yield_now().await;
        }
        // Let the producer finish sending/parking without advancing virtual time.
        for _ in 0..8 {
            tokio::task::yield_now().await;
        }
    }
    #[tokio::test]
    #[ignore = "explicit 1GiB local throughput observation; not a timing gate"]
    async fn measure_download_reader_throughput() {
        use axum::body::HttpBody;
        use std::io::Write;
        let length = 1024 * 1024 * 1024;
        let mut file = tempfile::tempfile().unwrap();
        let block = vec![0x5a; 1024 * 1024];
        for _ in 0..1024 {
            file.write_all(&block).unwrap();
        }
        file.sync_all().unwrap();
        let permits = Arc::new(Semaphore::new(1));
        let mut samples = Vec::new();
        for round in 0..3 {
            for offset in 0..2 {
                let bounded = (round + offset) % 2 == 1;
                file.seek(SeekFrom::Start(0)).unwrap();
                let handle = file.try_clone().unwrap();
                let start = Instant::now();
                let mut body = if bounded {
                    Body::from_stream(ReaderStream::with_capacity(
                        download_reader(
                            handle,
                            length,
                            permits.clone().acquire_owned().await.unwrap(),
                            Duration::from_secs(3600),
                        ),
                        DOWNLOAD_CHUNK,
                    ))
                } else {
                    // Pre-#34 adapter: Tokio file/take and default ReaderStream capacity.
                    Body::from_stream(ReaderStream::new(
                        tokio::fs::File::from_std(handle).take(length),
                    ))
                };
                let mut bytes = 0;
                let mut frames = 0;
                while let Some(frame) =
                    std::future::poll_fn(|cx| std::pin::Pin::new(&mut body).poll_frame(cx)).await
                {
                    let data = frame.unwrap().into_data().unwrap();
                    bytes += data.len() as u64;
                    frames += 1;
                }
                assert_eq!(bytes, length);
                samples.push(json!({"path":if bounded {"bounded_producer"} else {"legacy_tokio_fs"},"round":round,"bytes":bytes,"frames":frames,"milliseconds":start.elapsed().as_secs_f64()*1000.0}));
            }
        }
        println!(
            "FORGE_DOWNLOAD_BENCHMARK={}",
            json!({"schema":1,"host":std::env::consts::OS,"architecture":std::env::consts::ARCH,"chunk_bytes":DOWNLOAD_CHUNK,"samples":samples,"scope":"local warm regular-file response-body drain; three alternating rounds; no hashing, network, TLS or remote throughput claim; temporary 1GiB file removed"})
        );
    }
    #[test]
    fn sized_deadline_rounds_up_and_caps_without_overflow() {
        let base = Duration::from_secs(300);
        let rate = 1024 * 1024;
        assert_eq!(download_lifetime(base, rate, 0).as_secs(), 300);
        assert_eq!(download_lifetime(base, rate, 1).as_secs(), 301);
        assert_eq!(
            download_lifetime(base, rate, 1024 * 1024 * 1024).as_secs(),
            1324
        );
        assert_eq!(download_lifetime(base, 1, u64::MAX).as_secs(), 3600);
        assert_eq!(
            download_lifetime(Duration::from_secs(3600), rate, 1).as_secs(),
            3600
        );
    }
    #[tokio::test]
    async fn premature_channel_close_is_not_clean_eof() {
        let (sender, receiver) = mpsc::channel(1);
        drop(sender);
        let mut reader = DownloadReader {
            receiver,
            chunk: Vec::new(),
            position: 0,
            expired: Arc::new(AtomicBool::new(false)),
            remaining: 1,
            finished: None,
        };
        assert_eq!(
            reader.read(&mut [0; 1]).await.unwrap_err().kind(),
            io::ErrorKind::UnexpectedEof
        );
    }
    #[tokio::test(start_paused = true)]
    async fn scaled_deadline_allows_slow_consumption_past_base() {
        let permits = Arc::new(Semaphore::new(1));
        let count = Arc::new(AtomicUsize::new(0));
        // Same 1324-second budget as a 1GiB response at the default 1MiB/s rate.
        let mut reader = download_reader(
            CountedRead {
                file: stream_file(),
                reads: count.clone(),
            },
            1024 * 1024,
            permits.clone().acquire_owned().await.unwrap(),
            download_lifetime(Duration::from_secs(300), 1024, 1024 * 1024),
        );
        let mut bytes = vec![0; DOWNLOAD_CHUNK];
        for chunk in 0..4 {
            wait_reads(&count, chunk + 1).await;
            tokio::time::advance(Duration::from_secs(200)).await;
            reader.read_exact(&mut bytes).await.unwrap();
            assert!(bytes.iter().all(|b| *b == 7));
        }
        let _returned = permits.acquire_owned().await.unwrap();
        tokio::time::advance(Duration::from_secs(2000)).await;
        assert_eq!(reader.read(&mut [0; 1]).await.unwrap(), 0);
    }
    #[tokio::test]
    async fn library_validation_precedes_storage() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("absent");
        let mut state = service(root.clone());
        Arc::get_mut(&mut state)
            .unwrap()
            .config
            .download_min_bytes_per_second = 0;
        let config = Arc::try_unwrap(state).ok().unwrap().config;
        assert!(
            serve(config)
                .await
                .unwrap_err()
                .to_string()
                .contains("positive")
        );
        assert!(!root.exists());
    }
    #[tokio::test(start_paused = true)]
    async fn two_unpolled_bodies_expire_and_fresh_reader_recovers() {
        let permits = Arc::new(Semaphore::new(2));
        let mut readers = Vec::new();
        for _ in 0..2 {
            let count = Arc::new(AtomicUsize::new(0));
            let reader = download_reader(
                CountedRead {
                    file: stream_file(),
                    reads: count.clone(),
                },
                1024 * 1024,
                permits.clone().acquire_owned().await.unwrap(),
                Duration::from_secs(10),
            );
            wait_reads(&count, 2).await;
            readers.push(reader);
        }
        assert_eq!(permits.available_permits(), 0);
        tokio::time::advance(Duration::from_secs(11)).await;
        let both = permits.clone().acquire_many_owned(2).await.unwrap();
        for reader in &mut readers {
            assert_eq!(
                reader.read(&mut [0; 1]).await.unwrap_err().kind(),
                io::ErrorKind::TimedOut
            );
        }
        drop(both);
        tokio::time::resume();
        let mut fresh = download_reader(
            stream_file(),
            1024 * 1024,
            permits.clone().acquire_owned().await.unwrap(),
            Duration::from_secs(300),
        );
        let mut bytes = Vec::new();
        fresh.read_to_end(&mut bytes).await.unwrap();
        assert_eq!(bytes, vec![7; 1024 * 1024]);
    }
    #[tokio::test(start_paused = true)]
    async fn trickle_does_not_reset_total_deadline_and_drop_cancels() {
        let permits = Arc::new(Semaphore::new(1));
        let count = Arc::new(AtomicUsize::new(0));
        let mut reader = download_reader(
            CountedRead {
                file: stream_file(),
                reads: count.clone(),
            },
            1024 * 1024,
            permits.clone().acquire_owned().await.unwrap(),
            Duration::from_secs(10),
        );
        wait_reads(&count, 2).await;
        for _ in 0..3 {
            assert_eq!(reader.read(&mut [0; 1]).await.unwrap(), 1);
            tokio::time::advance(Duration::from_secs(3)).await;
        }
        tokio::time::advance(Duration::from_secs(2)).await;
        let permit = permits.clone().acquire_owned().await.unwrap();
        assert_eq!(
            reader.read(&mut [0; 1]).await.unwrap_err().kind(),
            io::ErrorKind::TimedOut
        );
        drop(permit);
        let count = Arc::new(AtomicUsize::new(0));
        let disconnected = download_reader(
            CountedRead {
                file: stream_file(),
                reads: count.clone(),
            },
            1024 * 1024,
            permits.clone().acquire_owned().await.unwrap(),
            Duration::from_secs(300),
        );
        wait_reads(&count, 2).await;
        drop(disconnected);
        let _returned = permits.acquire_owned().await.unwrap();
    }
    #[tokio::test(start_paused = true)]
    async fn small_unpolled_body_and_queued_tail_still_expire() {
        for consume_first in [false, true] {
            let permits = Arc::new(Semaphore::new(1));
            let count = Arc::new(AtomicUsize::new(0));
            let mut reader = download_reader(
                CountedRead {
                    file: stream_file(),
                    reads: count.clone(),
                },
                2,
                permits.clone().acquire_owned().await.unwrap(),
                Duration::from_secs(10),
            );
            wait_reads(&count, 1).await;
            if consume_first {
                assert_eq!(reader.read(&mut [0; 1]).await.unwrap(), 1);
            }
            assert_eq!(permits.available_permits(), 0);
            tokio::time::advance(Duration::from_secs(11)).await;
            let _returned = permits.acquire_owned().await.unwrap();
            assert_eq!(
                reader.read(&mut [0; 1]).await.unwrap_err().kind(),
                io::ErrorKind::TimedOut
            );
        }
    }
    #[tokio::test]
    async fn cancelled_blocking_read_keeps_spool_permit_until_io_finishes() {
        struct Blocked {
            started: std::sync::mpsc::Sender<()>,
            finish: std::sync::mpsc::Receiver<()>,
        }
        impl Read for Blocked {
            fn read(&mut self, _: &mut [u8]) -> io::Result<usize> {
                self.started.send(()).unwrap();
                self.finish.recv().unwrap();
                Ok(0)
            }
        }
        let permits = Arc::new(Semaphore::new(1));
        let (start, started) = std::sync::mpsc::channel();
        let (finish, finished) = std::sync::mpsc::channel();
        let reader = download_reader(
            Blocked {
                started: start,
                finish: finished,
            },
            1,
            permits.clone().acquire_owned().await.unwrap(),
            Duration::from_secs(300),
        );
        tokio::task::spawn_blocking(move || started.recv_timeout(Duration::from_secs(5)))
            .await
            .unwrap()
            .unwrap();
        drop(reader);
        tokio::task::yield_now().await;
        assert_eq!(permits.available_permits(), 0);
        finish.send(()).unwrap();
        let _returned = tokio::time::timeout(Duration::from_secs(5), permits.acquire_owned())
            .await
            .unwrap()
            .unwrap();
    }
    #[tokio::test]
    async fn serving_budget_is_server_error_without_fallback() {
        let error = classify(anyhow::anyhow!(crate::error::Kind::ProviderLimit));
        assert_eq!(error.0, StatusCode::BAD_REQUEST);
        let response = provider_read_error(error).into_response();
        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
        let bytes = to_bytes(response.into_body(), 4096).await.unwrap();
        let value: Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(value["error"]["code"], "provider_limit");
        assert_eq!(value["error"]["availability_fallback"], false);
        assert_eq!(value["error"]["retryable"], false);
        assert_eq!(
            provider_read_error(bad("invalid_id")).0,
            StatusCode::BAD_REQUEST
        );
    }
    fn service(root: PathBuf) -> Arc<Service> {
        Arc::new(Service {
            config: Config {
                root,
                params_dir: None,
                fetch_params: false,
                profile: None,
                listen: "127.0.0.1:0".parse().unwrap(),
                token_file: None,
                provider_root: None,
                provider_limits: crate::provider_view::Limits::default(),
                download_timeout: Duration::from_secs(300),
                download_min_bytes_per_second: 1024 * 1024,
            },
            token: None,
            work: Arc::new(Semaphore::new(8)),
            generation: Arc::new(Semaphore::new(1)),
            downloads: Arc::new(Semaphore::new(8)),
            uploads: Arc::new(Semaphore::new(2)),
            provider_reads: Arc::new(Semaphore::new(2)),
            provider_waiters: Arc::new(Semaphore::new(8)),
        })
    }
    async fn poll_waiter(
        future: std::pin::Pin<
            &mut impl std::future::Future<Output = std::result::Result<OwnedSemaphorePermit, ApiError>>,
        >,
    ) {
        let mut future = future;
        std::future::poll_fn(|cx| {
            assert!(future.as_mut().poll(cx).is_pending());
            std::task::Poll::Ready(())
        })
        .await;
    }
    #[tokio::test]
    async fn three_artifact_burst_waits_and_waiting_cancellation_recovers() {
        let root = tempfile::tempdir().unwrap();
        let state = service(root.path().join("unused-cache"));
        let first = state.provider_permit(Duration::ZERO).await.unwrap();
        let second = state.provider_permit(Duration::ZERO).await.unwrap();
        let mut third = Box::pin(state.provider_permit(Duration::from_secs(5)));
        poll_waiter(third.as_mut()).await;
        assert_eq!(state.provider_waiters.available_permits(), 7);
        drop(first);
        let third = third.await.unwrap();
        assert_eq!(state.provider_waiters.available_permits(), 8);
        let mut cancelled = Box::pin(state.provider_permit(Duration::from_secs(5)));
        poll_waiter(cancelled.as_mut()).await;
        drop(cancelled);
        assert_eq!(state.provider_waiters.available_permits(), 8);
        drop((second, third));
        assert_eq!(state.provider_reads.available_permits(), 2);
        assert!(!state.config.root.exists());
    }
    #[tokio::test]
    async fn finite_queue_overflow_timeout_and_retry_after() {
        let root = tempfile::tempdir().unwrap();
        let state = service(root.path().join("unused-cache"));
        let active = state
            .provider_reads
            .clone()
            .acquire_many_owned(2)
            .await
            .unwrap();
        let mut waiting = Vec::new();
        for _ in 0..8 {
            let mut future = Box::pin(state.provider_permit(Duration::from_secs(5)));
            poll_waiter(future.as_mut()).await;
            waiting.push(future);
        }
        assert_eq!(state.provider_waiters.available_permits(), 0);
        let response = state
            .provider_permit(Duration::ZERO)
            .await
            .err()
            .unwrap()
            .into_response();
        assert_eq!(response.status(), StatusCode::TOO_MANY_REQUESTS);
        assert_eq!(response.headers()[header::RETRY_AFTER], "1");
        drop(waiting);
        assert_eq!(state.provider_waiters.available_permits(), 8);
        assert_eq!(
            state.provider_permit(Duration::ZERO).await.err().unwrap().1,
            "provider_reads_busy"
        );
        assert_eq!(state.provider_waiters.available_permits(), 8);
        drop(active);
        let (_, permit) = state.provider_work(|| Ok(())).await.unwrap();
        drop(permit);
        assert_eq!(state.provider_reads.available_permits(), 2);
    }
    #[tokio::test]
    async fn provider_and_cache_admission_are_independent() {
        let root = tempfile::tempdir().unwrap();
        let state = service(root.path().join("cache"));
        let cache = state.work.clone().acquire_many_owned(8).await.unwrap();
        let (_, first) = state.provider_work(|| Ok(())).await.unwrap();
        let (_, second) = state.provider_work(|| Ok(())).await.unwrap();
        assert!(
            !state.config.root.exists(),
            "provider reads opened a cache store"
        );
        assert_eq!(
            state.provider_permit(Duration::ZERO).await.err().unwrap().0,
            StatusCode::TOO_MANY_REQUESTS
        );
        drop(cache);
        state.work(|_, store| store.stats()).await.unwrap();
        drop((first, second));
        assert_eq!(state.provider_reads.available_permits(), 2);
    }
    #[tokio::test(flavor = "multi_thread", worker_threads = 2)]
    async fn cancellation_keeps_capacity_until_blocking_verification_stops() {
        let root = tempfile::tempdir().unwrap();
        let state = service(root.path().join("cache"));
        let (started_tx, started_rx) = std::sync::mpsc::channel();
        let (release_tx, release_rx) = std::sync::mpsc::channel();
        let child_state = state.clone();
        let request = tokio::spawn(async move {
            child_state
                .provider_work(move || {
                    started_tx.send(()).unwrap();
                    release_rx.recv_timeout(std::time::Duration::from_secs(5))?;
                    Ok(())
                })
                .await
        });
        tokio::task::spawn_blocking(move || {
            started_rx.recv_timeout(std::time::Duration::from_secs(5))
        })
        .await
        .unwrap()
        .unwrap();
        request.abort();
        assert!(request.await.unwrap_err().is_cancelled());
        assert_eq!(state.provider_reads.available_permits(), 1);
        let other = state.provider_reads.clone().acquire_owned().await.unwrap();
        assert_eq!(
            state.provider_permit(Duration::ZERO).await.err().unwrap().0,
            StatusCode::TOO_MANY_REQUESTS
        );
        release_tx.send(()).unwrap();
        let returned = tokio::time::timeout(
            std::time::Duration::from_secs(5),
            state.provider_reads.clone().acquire_owned(),
        )
        .await
        .unwrap()
        .unwrap();
        drop((other, returned));
        assert_eq!(state.provider_reads.available_permits(), 2);
    }
}

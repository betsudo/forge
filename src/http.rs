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
    io::{Read, Seek, SeekFrom},
    net::SocketAddr,
    path::PathBuf,
    sync::Arc,
    time::Instant,
};
use tokio::{
    io::{AsyncRead, AsyncReadExt, ReadBuf},
    sync::{OwnedSemaphorePermit, Semaphore},
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
}
struct Service {
    config: Config,
    token: Option<[u8; 32]>,
    work: Arc<Semaphore>,
    generation: Arc<Semaphore>,
    downloads: Arc<Semaphore>,
    uploads: Arc<Semaphore>,
}
type Shared = Arc<Service>;
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
fn classify(error: anyhow::Error) -> ApiError {
    let kind = crate::error::classify(&error);
    ApiError(
        StatusCode::from_u16(kind.status()).expect("domain HTTP status"),
        kind.code(),
    )
}
impl Service {
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
struct HeldReader {
    file: tokio::io::Take<tokio::fs::File>,
    _permit: OwnedSemaphorePermit,
}
impl AsyncRead for HeldReader {
    fn poll_read(
        mut self: std::pin::Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
        buf: &mut ReadBuf<'_>,
    ) -> std::task::Poll<std::io::Result<()>> {
        std::pin::Pin::new(&mut self.file).poll_read(cx, buf)
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
        stream_permit,
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
    let permit = state
        .downloads
        .clone()
        .try_acquire_owned()
        .map_err(|_| ApiError(StatusCode::TOO_MANY_REQUESTS, "downloads_busy"))?;
    let content_type = if path.ends_with(".json") || path.ends_with(".zkir") {
        "application/json"
    } else if path.ends_with(".js") {
        "text/javascript"
    } else {
        "application/octet-stream"
    };
    let (file, digest, size) = state
        .work(move |_, _| {
            let view = root.join(&id);
            if !view.exists() {
                return Err(anyhow::anyhow!(crate::error::Kind::NotFound));
            }
            crate::provider_view::read(&view, &id, &path)
        })
        .await?;
    file_response(file, size, &digest, content_type, headers, method, permit)
}
fn file_response(
    mut file: File,
    size: u64,
    digest: &str,
    content_type: &str,
    headers: HeaderMap,
    method: Method,
    stream_permit: OwnedSemaphorePermit,
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
        let reader = HeldReader {
            file: tokio::fs::File::from_std(file).take(length),
            _permit: stream_permit,
        };
        Body::from_stream(ReaderStream::new(reader))
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

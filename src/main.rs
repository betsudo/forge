use anyhow::Result;
use clap::{Parser, Subcommand};
use midnight_zkir_forge::{
    application, backend, domain::ArtifactKind, engine::ProfileSelector, http, snapshot,
    store::Store,
};
use serde_json::{Value, json};
use std::path::PathBuf;

#[derive(Parser)]
#[command(
    name = "zkir-forge",
    bin_name = "zkir-forge",
    version,
    about = "Verified local Midnight ledger8 circuit artifact cache"
)]
struct Cli {
    #[arg(long, global = true, env = "MIDNIGHT_ZKIR_FORGE_DIR")]
    cache_dir: Option<PathBuf>,
    /// Select an exact backend; otherwise detect the supported format from input.
    #[arg(long, global = true, value_enum)]
    profile: Option<ProfileSelector>,
    #[arg(long, global = true, env = "MIDNIGHT_PP")]
    params_dir: Option<PathBuf>,
    /// Explicitly allow official parameter downloads. Offline by default.
    #[arg(long, global = true)]
    fetch_params: bool,
    #[command(subcommand)]
    command: Command,
}
#[derive(Subcommand)]
enum Command {
    /// Register one JSON ZKIR circuit without generating keys.
    Import {
        input: PathBuf,
        #[arg(long)]
        name: Option<String>,
    },
    /// Ensure a registered bundle; keygen only on a verified miss.
    Ensure {
        bundle_id: String,
        #[arg(long)]
        output: Option<PathBuf>,
    },
    /// Import and ensure a circuit in one call (recommended for tests).
    Prepare {
        input: PathBuf,
        #[arg(long)]
        name: Option<String>,
        #[arg(long)]
        output: Option<PathBuf>,
    },
    Inspect {
        bundle_id: String,
    },
    /// Return persistent copied paths without triggering generation.
    Resolve {
        bundle_id: String,
        #[arg(long)]
        artifact: Option<ArtifactKind>,
    },
    /// Copy the complete provider layout to a new persistent directory.
    Export {
        bundle_id: String,
        #[arg(long)]
        output: PathBuf,
    },
    /// Evict derived CAS files; keep source, output identity and existing exports.
    Evict {
        bundle_id: String,
        #[arg(long)]
        dry_run: bool,
    },
    /// Per-file and total local hit/miss/timing statistics (JSON).
    Stats,
    /// Preserve a complete original compiler bundle as an immutable provider view.
    PublishView {
        input: PathBuf,
        #[arg(long)]
        manifest_sha256: String,
        #[arg(long)]
        provider_root: PathBuf,
        #[arg(long, default_value_t = midnight_zkir_forge::provider_view::DEFAULT_MAX_VIEW_BYTES)]
        provider_max_view_bytes: u64,
    },
    /// Audit every declared compiler-view file without modifying it.
    VerifyView {
        input: PathBuf,
        #[arg(long)]
        manifest_sha256: String,
        #[arg(long, default_value_t = midnight_zkir_forge::provider_view::DEFAULT_MAX_VIEW_BYTES)]
        provider_max_view_bytes: u64,
    },
    /// Publish a consistent verified directory snapshot of an existing store.
    Snapshot {
        #[arg(long)]
        output: PathBuf,
        #[arg(long, default_value_t = snapshot::DEFAULT_MAX_BYTES)]
        max_bytes: u64,
        #[arg(long, default_value_t = 30)]
        wait_seconds: u64,
        #[arg(long)]
        partition: Option<String>,
        #[arg(long)]
        parameter_digest: Vec<String>,
    },
    /// Restore a verified snapshot into an absent explicitly selected cache.
    Restore {
        input: PathBuf,
        #[arg(long)]
        expected_id: Option<String>,
        #[arg(long)]
        partition: Option<String>,
        #[arg(long)]
        parameter_digest: Vec<String>,
        #[arg(long, default_value_t = snapshot::DEFAULT_MAX_BYTES)]
        max_bytes: u64,
    },
    /// Fresh real keygen twice, valid proof and invalid-statement control.
    Qualify,
    /// Verify the genuine minimal fixture using already exported keys (qualification only).
    QualifyExport {
        input: PathBuf,
    },
    Profile,
    /// Serve the initial single-owner HTTP API. Remote binding requires a token.
    Serve {
        #[arg(long, default_value = "127.0.0.1:8787")]
        listen: std::net::SocketAddr,
        #[arg(long)]
        token_file: Option<PathBuf>,
        #[arg(long)]
        provider_root: Option<PathBuf>,
        #[arg(long, default_value_t = midnight_zkir_forge::provider_view::DEFAULT_MAX_VIEW_BYTES)]
        provider_max_view_bytes: u64,
        /// Base seconds plus response bytes/minimum rate, capped at 3600 seconds.
        #[arg(long, default_value_t = 300, value_parser = clap::value_parser!(u64).range(1..=3600))]
        download_timeout_seconds: u64,
        /// Rate used to size the total deadline; progress never resets it.
        #[arg(long, default_value_t = 1024 * 1024, value_parser = clap::value_parser!(u64).range(1..))]
        download_min_bytes_per_second: u64,
    },
}
#[tokio::main(flavor = "current_thread")]
async fn main() {
    let cli = Cli::parse();
    match run(cli).await {
        Ok(value) => println!(
            "{}",
            serde_json::to_string(&value).expect("serialize result")
        ),
        Err(error) => {
            eprintln!("{error:#}");
            println!(
                "{}",
                json!({"schema":1,"error":{"code":error_code(&error),"message":error_code(&error),"retryable":midnight_zkir_forge::error::classify(&error).retryable(),"availability_fallback":midnight_zkir_forge::error::classify(&error).availability_fallback()}})
            );
            std::process::exit(1);
        }
    }
}
fn error_code(error: &anyhow::Error) -> &'static str {
    midnight_zkir_forge::error::classify(error).code()
}
async fn run(cli: Cli) -> Result<Value> {
    if matches!(cli.command, Command::Profile) {
        if let Some(spec) = cli.profile.and_then(ProfileSelector::worker) {
            let (mut value, worker) = spec.call("profile", &[], None, false, None, None)?;
            if spec.format == midnight_zkir_forge::zkir31::FORMAT {
                value["ledger_revision"] = spec.ledger_revision.into();
            }
            value["worker"] = serde_json::to_value(worker)?;
            return Ok(value);
        }
        return Ok(
            json!({"schema":1,"formats":["midnight-zkir-v2-json","midnight-zkir-v3-json","midnight-zkir-v3.1-json"],"selectors":["ledger8-v2","zkir3","zkir31"],"profile":backend::PROFILE,"ledger_revision":backend::LEDGER_REV,"build_fingerprint":application::build_fingerprint()}),
        );
    }
    if matches!(cli.command, Command::Qualify) {
        if let Some(spec) = cli.profile.and_then(ProfileSelector::worker) {
            let (mut value, worker) = spec.call(
                "qualify",
                &[],
                cli.params_dir.as_deref(),
                cli.fetch_params,
                None,
                None,
            )?;
            value["worker"] = serde_json::to_value(worker)?;
            return Ok(value);
        }
        return application::qualify(cli.params_dir.as_deref(), cli.fetch_params).await;
    }
    if let Command::QualifyExport { input } = &cli.command {
        return application::qualify_export(input, cli.params_dir.as_deref()).await;
    }
    if let Command::Restore {
        input,
        expected_id,
        partition,
        max_bytes,
        parameter_digest,
    } = &cli.command
    {
        let root = cli.cache_dir.as_ref().ok_or_else(|| {
            anyhow::anyhow!("restore requires explicit --cache-dir or MIDNIGHT_ZKIR_FORGE_DIR")
        })?;
        return snapshot::restore(
            input,
            root,
            *max_bytes,
            expected_id.as_deref(),
            partition.as_deref(),
            &snapshot::Scope {
                profile: cli.profile,
                parameters: parameter_digest.clone(),
            },
        );
    }
    if let Command::PublishView {
        input,
        manifest_sha256,
        provider_root,
        provider_max_view_bytes,
    } = &cli.command
    {
        midnight_zkir_forge::provider_view::separate_roots(
            provider_root,
            &match &cli.cache_dir {
                Some(path) => path.clone(),
                None => application::default_cache_dir()?,
            },
        )?;
        return midnight_zkir_forge::provider_view::publish_with_limits(
            input,
            manifest_sha256,
            provider_root,
            midnight_zkir_forge::provider_view::Limits::new(*provider_max_view_bytes)?,
        );
    }
    if let Command::VerifyView {
        input,
        manifest_sha256,
        provider_max_view_bytes,
    } = &cli.command
    {
        return midnight_zkir_forge::provider_view::verify_with_limits(
            input,
            manifest_sha256,
            midnight_zkir_forge::provider_view::Limits::new(*provider_max_view_bytes)?,
        );
    }
    let root = match cli.cache_dir {
        Some(path) => path,
        None => application::default_cache_dir()?,
    };
    if let Command::Serve {
        listen,
        token_file,
        provider_root,
        provider_max_view_bytes,
        download_timeout_seconds,
        download_min_bytes_per_second,
    } = &cli.command
    {
        return http::serve(http::Config {
            root,
            params_dir: cli.params_dir,
            fetch_params: cli.fetch_params,
            profile: cli.profile,
            listen: *listen,
            token_file: token_file.clone(),
            provider_root: provider_root.clone(),
            provider_limits: midnight_zkir_forge::provider_view::Limits::new(
                *provider_max_view_bytes,
            )?,
            download_timeout: std::time::Duration::from_secs(*download_timeout_seconds),
            download_min_bytes_per_second: *download_min_bytes_per_second,
        })
        .await;
    }
    if let Command::Snapshot {
        output,
        max_bytes,
        wait_seconds,
        partition,
        parameter_digest,
    } = &cli.command
    {
        return snapshot::create(
            &root,
            output,
            *max_bytes,
            *wait_seconds,
            partition.clone(),
            &snapshot::Scope {
                profile: cli.profile,
                parameters: parameter_digest.clone(),
            },
        );
    }
    let store = Store::open(&root)?;
    match cli.command {
        Command::Import { input, name } => {
            let record =
                application::import_with_profile(&store, &input, name.as_deref(), cli.profile)?;
            let mut value = serde_json::to_value(&record)?;
            value["descriptor"] = serde_json::to_value(
                midnight_zkir_forge::descriptor::ArtifactDescriptor::from_record(
                    &record,
                    &store.read(&record.source)?,
                )?,
            )?;
            Ok(value)
        }
        Command::Ensure { bundle_id, output } => {
            application::ensure_with_profile(
                &store,
                &bundle_id,
                "",
                cli.params_dir.as_deref(),
                cli.fetch_params,
                output.as_deref(),
                cli.profile,
            )
            .await
        }
        Command::Prepare {
            input,
            name,
            output,
        } => {
            let path = application::absolute_input(&input)?;
            let record =
                application::import_with_profile(&store, &input, name.as_deref(), cli.profile)?;
            application::ensure_with_profile(
                &store,
                &record.bundle_id.0,
                &path,
                cli.params_dir.as_deref(),
                cli.fetch_params,
                output.as_deref(),
                cli.profile,
            )
            .await
        }
        Command::Inspect { bundle_id } => {
            let (record, ready) = store.load(&bundle_id)?;
            Ok(
                json!({"schema":1,"descriptor":midnight_zkir_forge::descriptor::ArtifactDescriptor::from_record(&record, &store.read(&record.source)?)?,"record":record,"ready":ready}),
            )
        }
        Command::Resolve {
            bundle_id,
            artifact,
        } => application::resolve(&store, &bundle_id, artifact, None),
        Command::Export { bundle_id, output } => {
            application::resolve(&store, &bundle_id, None, Some(&output))
        }
        Command::Evict { bundle_id, dry_run } => store.evict(&bundle_id, dry_run),
        Command::Stats => store.stats(),
        Command::Qualify
        | Command::QualifyExport { .. }
        | Command::Profile
        | Command::PublishView { .. }
        | Command::VerifyView { .. }
        | Command::Serve { .. }
        | Command::Snapshot { .. }
        | Command::Restore { .. } => unreachable!(),
    }
}

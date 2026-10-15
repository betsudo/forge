use anyhow::Result;
use clap::{Parser, Subcommand};
use midnight_zkir_forge::{
    application, backend, domain::ArtifactKind, engine::ProfileSelector, http, snapshot,
    store::Store, zkir3,
};
use serde_json::{Value, json};
use std::path::PathBuf;

#[derive(Parser)]
#[command(
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
    Profile,
    /// Serve the initial single-owner HTTP API. Remote binding requires a token.
    Serve {
        #[arg(long, default_value = "127.0.0.1:8787")]
        listen: std::net::SocketAddr,
        #[arg(long)]
        token_file: Option<PathBuf>,
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
                json!({"schema":1,"error":{"code":error_code(&error),"message":format!("{error:#}")}})
            );
            std::process::exit(1);
        }
    }
}
fn error_code(error: &anyhow::Error) -> &'static str {
    let text = format!("{error:#}");
    if let Some(code) = [
        "snapshot_destination_exists",
        "snapshot_profile_mismatch",
        "snapshot_partition_mismatch",
        "snapshot_schema_mismatch",
        "snapshot_unsafe_path",
        "snapshot_limit",
        "snapshot_busy",
        "snapshot_publish_failed",
    ]
    .into_iter()
    .find(|code| text.contains(code))
    {
        code
    } else if text.contains("profile_format_mismatch") {
        "profile_format_mismatch"
    } else if text.contains("unsupported_zkir_version") {
        "unsupported_zkir_version"
    } else if text.contains("worker_profile_mismatch") {
        "worker_profile_mismatch"
    } else if text.contains("artifact_identity_changed") {
        "artifact_identity_changed"
    } else if text.contains("integrity") {
        "integrity_error"
    } else if text.contains("parameter") {
        "parameters_unavailable"
    } else {
        "request_failed"
    }
}
async fn run(cli: Cli) -> Result<Value> {
    if matches!(cli.command, Command::Profile) {
        if cli.profile == Some(ProfileSelector::Zkir3) {
            let (mut value, worker) = zkir3::call("profile", &[], None, false, None, None)?;
            value["worker"] = serde_json::to_value(worker)?;
            return Ok(value);
        }
        return Ok(
            json!({"schema":1,"formats":["midnight-zkir-v2-json","midnight-zkir-v3-json"],"selectors":["ledger8-v2","zkir3"],"profile":backend::PROFILE,"ledger_revision":backend::LEDGER_REV,"build_fingerprint":application::build_fingerprint()}),
        );
    }
    if matches!(cli.command, Command::Qualify) {
        if cli.profile == Some(ProfileSelector::Zkir3) {
            let (mut value, worker) = zkir3::call(
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
    let root = match cli.cache_dir {
        Some(path) => path,
        None => application::default_cache_dir()?,
    };
    if let Command::Serve { listen, token_file } = &cli.command {
        return http::serve(http::Config {
            root,
            params_dir: cli.params_dir,
            fetch_params: cli.fetch_params,
            profile: cli.profile,
            listen: *listen,
            token_file: token_file.clone(),
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
        Command::Import { input, name } => Ok(serde_json::to_value(
            application::import_with_profile(&store, &input, name.as_deref(), cli.profile)?,
        )?),
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
            Ok(json!({"schema":1,"record":record,"ready":ready}))
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
        | Command::Profile
        | Command::Serve { .. }
        | Command::Snapshot { .. }
        | Command::Restore { .. } => unreachable!(),
    }
}

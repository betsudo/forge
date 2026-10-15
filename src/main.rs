use anyhow::Result;
use clap::{Parser, Subcommand};
use midnight_zkir_forge::{application, backend, domain::ArtifactKind, store::Store};
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
    /// Fresh real keygen twice, valid proof and invalid-statement control.
    Qualify,
    Profile,
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
    if text.contains("artifact_identity_changed") {
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
        return Ok(
            json!({"schema":1,"profile":backend::PROFILE,"ledger_revision":backend::LEDGER_REV,"build_fingerprint":application::build_fingerprint()}),
        );
    }
    if matches!(cli.command, Command::Qualify) {
        return application::qualify(cli.params_dir.as_deref(), cli.fetch_params).await;
    }
    let root = match cli.cache_dir {
        Some(path) => path,
        None => application::default_cache_dir()?,
    };
    let store = Store::open(&root)?;
    match cli.command {
        Command::Import { input, name } => Ok(serde_json::to_value(application::import(
            &store,
            &input,
            name.as_deref(),
        )?)?),
        Command::Ensure { bundle_id, output } => {
            application::ensure_artifacts(
                &store,
                &bundle_id,
                "",
                cli.params_dir.as_deref(),
                cli.fetch_params,
                output.as_deref(),
            )
            .await
        }
        Command::Prepare {
            input,
            name,
            output,
        } => {
            let path = application::absolute_input(&input)?;
            let record = application::import(&store, &input, name.as_deref())?;
            application::ensure_artifacts(
                &store,
                &record.bundle_id.0,
                &path,
                cli.params_dir.as_deref(),
                cli.fetch_params,
                output.as_deref(),
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
        Command::Qualify | Command::Profile => unreachable!(),
    }
}

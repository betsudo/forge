//! Local logical snapshot/HTTP range cost baseline; not physical device counters.
use anyhow::{Context, Result, ensure};
use midnight_zkir_forge::provider_view;
use serde_json::json;
#[cfg(unix)]
use std::os::unix::fs::MetadataExt;
use std::{
    env,
    io::{Read, Seek, SeekFrom},
    path::Path,
    time::Instant,
};

fn main() -> Result<()> {
    let args: Vec<_> = env::args().collect();
    ensure!(
        args.len() == 4,
        "VIEW MANIFEST_SHA256 INVENTORY_PATH required"
    );
    let root = Path::new(&args[1]);
    let id = &args[2];
    let path = &args[3];
    let mut rows = Vec::new();
    for (mode, chunks, parallel) in [
        ("full", 1, 1),
        ("sequential-ranges", 8, 1),
        ("concurrent-ranges", 8, 2),
    ] {
        let started = Instant::now();
        let mut spool = 0u64;
        let mut allocated = 0u64;
        let mut peak = 0u64;
        let mut returned = 0u64;
        for first in (0..chunks).step_by(parallel) {
            let snapshots = std::thread::scope(|scope| -> Result<Vec<_>> {
                let children: Vec<_> = (first..(first + parallel).min(chunks))
                    .map(|index| {
                        scope.spawn(move || Ok((index, provider_view::read(root, id, path)?)))
                    })
                    .collect();
                children
                    .into_iter()
                    .map(|child| child.join().expect("read thread panicked"))
                    .collect()
            })?;
            let mut live = 0u64;
            for (index, (mut file, _, size)) in snapshots {
                ensure!(size >= chunks as u64, "file too small for eight ranges");
                let metadata = file.metadata()?;
                spool += metadata.len();
                live += metadata.len();
                #[cfg(unix)]
                {
                    allocated += metadata.blocks() * 512;
                }
                let begin = size * index as u64 / chunks as u64;
                let end = size * (index + 1) as u64 / chunks as u64;
                file.seek(SeekFrom::Start(begin))?;
                let count = std::io::copy(&mut file.take(end - begin), &mut std::io::sink())?;
                ensure!(count == end - begin, "short verified snapshot");
                returned += count;
            }
            // All snapshots in this batch existed together after join; descriptor
            // lengths give their logical peak before consumption dropped them.
            peak = peak.max(live);
        }
        rows.push(json!({"mode":mode,"requests":chunks,"concurrency":parallel,
            "wall_ms":started.elapsed().as_secs_f64()*1000.0,"snapshot_logical_bytes":spool,
            "snapshot_allocated_bytes":allocated,"peak_live_snapshot_logical_bytes":peak,
            "returned_bytes":returned}));
    }
    println!("{}",serde_json::to_string_pretty(&json!({"schema":1,"rows":rows,
        "manifest_sha256":id,"inventory_path":path,
        "scope":"Actual provider reader; logical descriptor lengths and filesystem allocation, not physical device I/O; warm local filesystem, no HTTP in this submeasurement"})).context("receipt")?);
    Ok(())
}

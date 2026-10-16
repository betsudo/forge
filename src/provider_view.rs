//! Verified, immutable copies of complete compiler output. Separate from the key cache.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs::{self, File, OpenOptions},
    io::{Read, Seek, SeekFrom, Write},
    path::Path,
};
const MANIFEST: &str = "compiler/contract-manifest.json";
const MAX_JSON: u64 = 4 * 1024 * 1024;
const MAX_FILE: u64 = 1024 * 1024 * 1024;
const MAX_TOTAL: u64 = 4 * MAX_FILE;
const MAX_FILES: usize = 4096;
#[derive(Clone)]
struct Entry {
    size: u64,
    hash: String,
}
fn component(name: &str) -> Result<()> {
    ensure!(
        !name.is_empty()
            && name.len() <= 255
            && name != "."
            && name != ".."
            && name
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b)),
        "invalid provider path"
    );
    Ok(())
}
fn open(root: &Path, path: &str) -> Result<File> {
    let mut current = root.to_path_buf();
    ensure!(
        fs::symlink_metadata(&current)?.is_dir()
            && !fs::symlink_metadata(&current)?.file_type().is_symlink(),
        "invalid provider directory"
    );
    let mut parts = path.split('/').peekable();
    while let Some(part) = parts.next() {
        component(part)?;
        current.push(part);
        let metadata = fs::symlink_metadata(&current)?;
        ensure!(!metadata.file_type().is_symlink(), "provider symlink");
        ensure!(
            if parts.peek().is_some() {
                metadata.is_dir()
            } else {
                metadata.is_file()
            },
            "unsupported provider entry"
        );
    }
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK);
    }
    let file = options.open(current)?;
    ensure!(file.metadata()?.is_file(), "provider entry is not a file");
    Ok(file)
}
fn bytes(root: &Path, path: &str, limit: u64) -> Result<Vec<u8>> {
    let file = open(root, path)?;
    ensure!(file.metadata()?.len() <= limit, "provider file limit");
    let mut out = Vec::new();
    file.take(limit + 1).read_to_end(&mut out)?;
    ensure!(out.len() as u64 <= limit, "provider file limit");
    Ok(out)
}
fn json_bytes(raw: &[u8]) -> Result<Value> {
    crate::domain::validate_json(raw)?;
    Ok(serde_json::from_slice(raw)?)
}
fn inventory(root: &Path, prefix: &str, files: &mut BTreeSet<String>) -> Result<()> {
    for item in fs::read_dir(root.join(prefix))? {
        let item = item?;
        let name = item
            .file_name()
            .into_string()
            .map_err(|_| anyhow::anyhow!("non UTF8 path"))?;
        component(&name)?;
        let path = if prefix.is_empty() {
            name
        } else {
            format!("{prefix}/{name}")
        };
        let meta = fs::symlink_metadata(item.path())?;
        ensure!(!meta.file_type().is_symlink(), "provider symlink");
        if meta.is_dir() {
            ensure!(prefix.is_empty(), "nested provider directories unsupported");
            let count = files.len();
            inventory(root, &path, files)?;
            ensure!(files.len() > count, "empty provider directory unsupported");
        } else {
            ensure!(meta.is_file(), "unsupported provider entry");
            files.insert(path);
            ensure!(files.len() <= MAX_FILES, "provider file count limit");
        }
    }
    Ok(())
}
fn entries(root: &Path, id: &str) -> Result<BTreeMap<String, Entry>> {
    crate::domain::validate_id(id)?;
    let raw = bytes(root, MANIFEST, MAX_JSON)?;
    ensure!(
        hex::encode(Sha256::digest(&raw)) == id,
        "provider manifest identity mismatch"
    );
    let manifest = json_bytes(&raw)?;
    let map = manifest.as_object().context("manifest object required")?;
    ensure!(
        manifest["manifest-version"] == "1",
        "unsupported manifest version"
    );
    let metadata = [
        "manifest-version",
        "compiler-version",
        "language-version",
        "runtime-version",
    ];
    for key in metadata {
        ensure!(
            manifest[key].as_str().is_some_and(|v| !v.is_empty()),
            "missing manifest metadata"
        );
    }
    let mut result = BTreeMap::new();
    result.insert(
        MANIFEST.into(),
        Entry {
            size: raw.len() as u64,
            hash: id.into(),
        },
    );
    let mut total = raw.len() as u64;
    for (dir, value) in map {
        if metadata.contains(&dir.as_str()) || dir == "compiler-commit" {
            continue;
        }
        component(dir)?;
        let obj = value.as_object().context("manifest directory required")?;
        ensure!(value["type"] == "directory", "manifest directory required");
        for (name, item) in obj {
            if name == "type" {
                continue;
            }
            component(name)?;
            ensure!(
                name != "contract-manifest.json",
                "nested manifest forbidden"
            );
            let obj = item.as_object().context("manifest file required")?;
            ensure!(
                obj.len() == 3 && item["type"] == "file",
                "unsupported manifest entry"
            );
            let size = item["size"].as_u64().context("manifest size required")?;
            ensure!(size <= MAX_FILE, "provider file limit");
            total = total.checked_add(size).context("size overflow")?;
            ensure!(total <= MAX_TOTAL, "provider total limit");
            let hash = item["hash"].as_str().context("manifest hash required")?;
            crate::domain::validate_id(hash)?;
            result.insert(
                format!("{dir}/{name}"),
                Entry {
                    size,
                    hash: hash.into(),
                },
            );
            ensure!(result.len() <= MAX_FILES, "provider file count limit");
        }
    }
    ensure!(
        result.contains_key("contract/index.js")
            && result.contains_key("compiler/contract-info.json"),
        "missing compiler runtime metadata"
    );
    let info_raw = bytes(root, "compiler/contract-info.json", MAX_JSON)?;
    let info_entry = result
        .get("compiler/contract-info.json")
        .context("missing compiler info")?;
    ensure!(
        info_raw.len() as u64 == info_entry.size
            && hex::encode(Sha256::digest(&info_raw)) == info_entry.hash,
        "compiler info digest mismatch"
    );
    let info = json_bytes(&info_raw)?;
    for key in &metadata[1..] {
        ensure!(info[key] == manifest[key], "compiler metadata mismatch");
    }
    if manifest.get("compiler-commit").is_some() || info.get("compiler-commit").is_some() {
        ensure!(
            manifest["compiler-commit"]
                .as_str()
                .is_some_and(|v| !v.is_empty())
                && info["compiler-commit"] == manifest["compiler-commit"],
            "compiler commit mismatch"
        );
    }
    let circuits = info["circuits"]
        .as_array()
        .context("circuits roster required")?;
    let mut names = BTreeSet::new();
    let mut expected = BTreeSet::new();
    for circuit in circuits {
        let name = circuit["name"].as_str().context("circuit name required")?;
        component(name)?;
        ensure!(names.insert(name), "duplicate circuit");
        let proof = circuit["proof"]
            .as_bool()
            .context("circuit proof flag required")?;
        if proof {
            for path in [
                format!("zkir/{name}.zkir"),
                format!("zkir/{name}.bzkir"),
                format!("keys/{name}.prover"),
                format!("keys/{name}.verifier"),
            ] {
                ensure!(result.contains_key(&path), "incomplete circuit artifacts");
                expected.insert(path);
            }
        }
    }
    ensure!(!expected.is_empty(), "no provable circuit");
    for path in result
        .keys()
        .filter(|p| p.starts_with("zkir/") || p.starts_with("keys/"))
    {
        ensure!(expected.contains(path), "unexpected circuit artifact");
    }
    let mut actual = BTreeSet::new();
    inventory(root, "", &mut actual)?;
    ensure!(
        actual == result.keys().cloned().collect(),
        "provider tree does not match manifest"
    );
    Ok(result)
}
fn verified_copy<W: Write>(root: &Path, path: &str, entry: &Entry, output: &mut W) -> Result<()> {
    let mut input = open(root, path)?;
    ensure!(
        input.metadata()?.len() == entry.size,
        "provider size mismatch"
    );
    let mut hash = Sha256::new();
    let mut size = 0u64;
    let mut buffer = [0u8; 128 * 1024];
    loop {
        let n = input.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        size += n as u64;
        ensure!(size <= entry.size, "provider file grew");
        hash.update(&buffer[..n]);
        output.write_all(&buffer[..n])?;
    }
    ensure!(
        size == entry.size && hex::encode(hash.finalize()) == entry.hash,
        "provider digest mismatch"
    );
    Ok(())
}
/// Verify pinned metadata/tree and the requested representation, without hashing siblings.
pub fn read(root: &Path, id: &str, path: &str) -> Result<(File, String, u64)> {
    let entries = entries(root, id).context(crate::error::Kind::IntegrityError)?;
    let requested = entries.get(path).context(crate::error::Kind::NotFound)?;
    let mut output = tempfile::tempfile()?;
    verified_copy(root, path, requested, &mut output)
        .context(crate::error::Kind::IntegrityError)?;
    output.seek(SeekFrom::Start(0))?;
    Ok((output, requested.hash.clone(), requested.size))
}
/// Full integrity audit; never writes a reusable verification marker.
pub fn verify(root: &Path, id: &str) -> Result<Value> {
    let entries = entries(root, id).context(crate::error::Kind::IntegrityError)?;
    let mut total = 0u64;
    for (name, entry) in &entries {
        verified_copy(root, name, entry, &mut std::io::sink())
            .context(crate::error::Kind::IntegrityError)?;
        total += entry.size;
    }
    Ok(json!({"schema":1,"view_id":id,"files":entries.len(),"bytes":total,"verified":true}))
}
pub fn publish(input: &Path, id: &str, root: &Path) -> Result<Value> {
    crate::domain::validate_id(id)?;
    fs::create_dir_all(root)?;
    ensure!(
        !fs::symlink_metadata(root)?.file_type().is_symlink(),
        "provider root symlink"
    );
    let manifest = entries(input, id)?;
    let target = root.join(id);
    if fs::symlink_metadata(&target).is_ok() {
        verify(&target, id)?;
        return Ok(json!({"schema":1,"view_id":id,"path":target,"reused":true}));
    }
    let stage = tempfile::Builder::new()
        .prefix(".provider-stage-")
        .tempdir_in(root)?;
    for (name, entry) in &manifest {
        let destination = stage.path().join(name);
        fs::create_dir_all(destination.parent().unwrap())?;
        let mut output = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(destination)?;
        verified_copy(input, name, entry, &mut output)?;
        output.sync_all()?;
    }
    // Re-inventory catches added/removed entries during publication; verify staging too.
    entries(input, id)?;
    verify(stage.path(), id)?;
    for item in fs::read_dir(stage.path())? {
        let p = item?.path();
        if p.is_dir() {
            File::open(p)?.sync_all()?;
        }
    }
    File::open(stage.path())?.sync_all()?;
    if let Err(error) = crate::filesystem::publish_directory(stage.path(), &target) {
        if target.exists() {
            verify(&target, id)?;
            return Ok(json!({"schema":1,"view_id":id,"path":target,"reused":true}));
        }
        return Err(error);
    }
    Ok(json!({"schema":1,"view_id":id,"path":target,"reused":false}))
}

/// Provider views must not become members or parents of cache snapshots.
pub fn separate_roots(provider: &Path, cache: &Path) -> Result<()> {
    fn resolved(path: &Path) -> Result<std::path::PathBuf> {
        let absolute = if path.is_absolute() {
            path.to_path_buf()
        } else {
            std::env::current_dir()?.join(path)
        };
        ensure!(
            !absolute
                .components()
                .any(|c| matches!(c, std::path::Component::ParentDir)),
            "parent components forbidden in managed roots"
        );
        let mut ancestor = absolute.as_path();
        let mut suffix = Vec::new();
        while !ancestor.exists() {
            suffix.push(
                ancestor
                    .file_name()
                    .context("invalid managed root")?
                    .to_os_string(),
            );
            ancestor = ancestor.parent().context("invalid managed root")?;
        }
        let mut out = fs::canonicalize(ancestor)?;
        for part in suffix.into_iter().rev() {
            out.push(part);
        }
        Ok(out)
    }
    let provider = resolved(provider)?;
    let cache = resolved(cache)?;
    ensure!(
        !provider.starts_with(&cache) && !cache.starts_with(&provider),
        "provider root and cache root must be separate non-nested directories"
    );
    Ok(())
}

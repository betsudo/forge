//! Shared durable, atomic no-replace publication for managed directories.
use anyhow::{Context, Result, ensure};
use std::{fs::File, path::Path};

pub(crate) fn publish_directory(stage: &Path, target: &Path) -> Result<()> {
    #[cfg(unix)]
    {
        use std::{ffi::CString, os::unix::ffi::OsStrExt};
        let from = CString::new(stage.as_os_str().as_bytes())?;
        let to = CString::new(target.as_os_str().as_bytes())?;
        #[cfg(target_os = "linux")]
        let result = unsafe {
            libc::syscall(
                libc::SYS_renameat2,
                libc::AT_FDCWD,
                from.as_ptr(),
                libc::AT_FDCWD,
                to.as_ptr(),
                libc::RENAME_NOREPLACE,
            )
        };
        #[cfg(target_os = "macos")]
        let result = unsafe { libc::renamex_np(from.as_ptr(), to.as_ptr(), libc::RENAME_EXCL) };
        #[cfg(not(any(target_os = "linux", target_os = "macos")))]
        anyhow::bail!("atomic directory publication unsupported on this OS");
        #[cfg(any(target_os = "linux", target_os = "macos"))]
        ensure!(
            result == 0,
            "directory_publish_failed: {}",
            std::io::Error::last_os_error()
        );
    }
    #[cfg(not(unix))]
    anyhow::bail!("atomic directory publication unsupported on this OS");
    File::open(target.parent().context("destination parent missing")?)?.sync_all()?;
    Ok(())
}

/// Available bytes for the current user on the destination filesystem.
pub(crate) fn available_space(path: &Path) -> Result<u64> {
    use std::os::fd::AsRawFd;
    let directory = File::open(path)?;
    let mut stats = std::mem::MaybeUninit::<libc::statvfs>::uninit();
    // fstatvfs initializes the structure on success; use the opened destination FD.
    ensure!(
        unsafe { libc::fstatvfs(directory.as_raw_fd(), stats.as_mut_ptr()) } == 0,
        "destination space query failed: {}",
        std::io::Error::last_os_error()
    );
    let stats = unsafe { stats.assume_init() };
    u64::try_from(u128::from(stats.f_bavail) * u128::from(stats.f_frsize))
        .context("destination space overflow")
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn publication_never_replaces_an_empty_destination() {
        let root = tempfile::tempdir().unwrap();
        let stage = root.path().join("stage");
        let target = root.path().join("target");
        std::fs::create_dir(&stage).unwrap();
        std::fs::write(stage.join("manifest"), b"complete").unwrap();
        std::fs::create_dir(&target).unwrap();
        assert!(publish_directory(&stage, &target).is_err());
        assert!(std::fs::read_dir(&target).unwrap().next().is_none());
        assert!(stage.join("manifest").exists());
        std::fs::remove_dir(&target).unwrap();
        publish_directory(&stage, &target).unwrap();
        assert_eq!(std::fs::read(target.join("manifest")).unwrap(), b"complete");
        assert!(!stage.exists());
    }
}

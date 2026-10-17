//! Cargo compatibility launcher. Installed Nix/portable aliases remain unchanged.
use std::{env, io, process::Command};

#[cfg(unix)]
fn launch() -> io::Result<()> {
    use std::os::unix::{fs::MetadataExt, process::CommandExt};
    let executable = env::current_exe()?.canonicalize()?;
    let primary = executable.with_file_name("zkir-forge");
    let source = executable.metadata()?;
    let target = primary.metadata()?;
    if source.dev() == target.dev() && source.ino() == target.ino() {
        return Err(io::Error::other(
            "primary command points to the compatibility launcher",
        ));
    }
    Err(Command::new(primary).args(env::args_os().skip(1)).exec())
}

fn main() {
    if let Err(error) = launch() {
        eprintln!(
            "midnight-zkir-forge: cannot execute sibling zkir-forge: {error}; install both commands"
        );
        std::process::exit(1);
    }
}

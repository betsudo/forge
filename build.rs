fn main() {
    let rustc = std::env::var_os("RUSTC").expect("Cargo supplies RUSTC");
    let output = std::process::Command::new(rustc)
        .arg("-vV")
        .output()
        .expect("rustc version");
    assert!(output.status.success());
    let version = String::from_utf8(output.stdout)
        .expect("UTF-8 rustc version")
        .replace('\n', ";");
    println!("cargo:rustc-env=FORGE_RUSTC_VERSION={version}");
    println!("cargo:rerun-if-changed=build.rs");
}

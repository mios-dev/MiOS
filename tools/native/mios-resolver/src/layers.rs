// AI-hint: Tier and fragment discovery -- builds the figment provider stack in vendor < vendor.d < host < host.d < user < user.d precedence order.
// AI-related: usr/share/mios/mios.toml, /etc/mios/mios.toml, /usr/lib/mios/mios.d
use figment::providers::{Format, Toml};
use figment::Figment;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

pub fn normalize_path_str(p: &str) -> String {
    if p.is_empty() {
        return String::new();
    }
    let mut normalized = p.replace('\\', "/");
    if normalized.starts_with('/') && normalized.len() > 2 {
        let bytes = normalized.as_bytes();
        if bytes[1].is_ascii_alphabetic() && bytes[2] == b'/' {
            let drive = (bytes[1] as char).to_ascii_lowercase();
            normalized = format!("{}:/{}", drive, &normalized[3..]);
        }
    }
    normalized
}

pub fn normalize_path(p: &Path) -> PathBuf {
    PathBuf::from(normalize_path_str(&p.to_string_lossy()))
}

fn _frags(dirpath: &Path) -> Vec<PathBuf> {
    if !dirpath.exists() || !dirpath.is_dir() {
        return Vec::new();
    }
    let mut entries = Vec::new();
    if let Ok(read_dir) = fs::read_dir(dirpath) {
        for entry in read_dir.flatten() {
            let path = entry.path();
            if path.is_file() && path.extension().map_or(false, |ext| ext == "toml") {
                entries.push(normalize_path(&path));
            }
        }
    }
    entries.sort_by(|a, b| {
        let a_base = a.file_name().unwrap_or_default();
        let b_base = b.file_name().unwrap_or_default();
        a_base.cmp(b_base)
    });
    entries
}

pub fn resolve_tier_dirs(root_dir: Option<&Path>) -> (PathBuf, PathBuf, PathBuf, PathBuf, PathBuf, PathBuf) {
    let root_str = root_dir
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|| env::var("MIOS_TOML_ROOT").unwrap_or_default());
    let root = normalize_path_str(&root_str);

    let vendor = env::var("MIOS_VENDOR_TOML")
        .or_else(|_| env::var("MIOS_TOML"))
        .unwrap_or_else(|_| {
            if !root.is_empty() {
                format!("{}/usr/share/mios/mios.toml", root)
            } else {
                "usr/share/mios/mios.toml".to_string()
            }
        });

    let host = env::var("MIOS_HOST_TOML")
        .unwrap_or_else(|_| {
            if !root.is_empty() {
                format!("{}/etc/mios/mios.toml", root)
            } else {
                "etc/mios/mios.toml".to_string()
            }
        });

    let user = env::var("MIOS_USER_TOML").unwrap_or_else(|_| {
        // Mirror userenv.sh: ${XDG_CONFIG_HOME:-$HOME/.config}. A literal "~"
        // never expands here, so resolve HOME (USERPROFILE on Windows) instead
        // or the whole user tier is silently dropped.
        let xdg = env::var("XDG_CONFIG_HOME").unwrap_or_else(|_| {
            let home = env::var("HOME")
                .or_else(|_| env::var("USERPROFILE"))
                .unwrap_or_default();
            format!("{}/.config", home)
        });
        format!("{}/mios/mios.toml", xdg)
    });

    let vendor_d = env::var("MIOS_VENDOR_TOML_D").unwrap_or_else(|_| {
        if !root.is_empty() {
            format!("{}/usr/lib/mios/mios.d", root)
        } else {
            "usr/lib/mios/mios.d".to_string()
        }
    });

    let host_p = Path::new(&host);
    let host_dir = host_p.parent().unwrap_or_else(|| Path::new("."));
    let host_d = env::var("MIOS_HOST_TOML_D")
        .unwrap_or_else(|_| host_dir.join("mios.d").to_string_lossy().to_string());

    let user_p = Path::new(&user);
    let user_dir = user_p.parent().unwrap_or_else(|| Path::new("."));
    let user_d = env::var("MIOS_USER_TOML_D")
        .unwrap_or_else(|_| user_dir.join("mios.d").to_string_lossy().to_string());

    (
        normalize_path(Path::new(&vendor)),
        normalize_path(Path::new(&vendor_d)),
        normalize_path(Path::new(&host)),
        normalize_path(Path::new(&host_d)),
        normalize_path(Path::new(&user)),
        normalize_path(Path::new(&user_d)),
    )
}

pub fn resolve_layer_paths(root_dir: Option<&Path>) -> Vec<PathBuf> {
    let (vendor, vendor_d, host, host_d, user, user_d) = resolve_tier_dirs(root_dir);
    let mut paths = Vec::new();

    if vendor.exists() {
        paths.push(vendor);
    }
    paths.extend(_frags(&vendor_d));

    if host.exists() {
        paths.push(host);
    }
    paths.extend(_frags(&host_d));

    if user.exists() {
        paths.push(user);
    }
    paths.extend(_frags(&user_d));

    paths
}

pub fn create_figment(root_dir: Option<&Path>) -> Figment {
    let mut fig = Figment::new();
    for p in resolve_layer_paths(root_dir) {
        fig = fig.merge(Toml::file(p));
    }
    fig
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::{self, File};
    use tempfile::tempdir;

    #[test]
    fn test_path_normalization() {
        assert_eq!(normalize_path_str("/c/MiOS/usr/share"), "c:/MiOS/usr/share");
        assert_eq!(normalize_path_str("C:\\MiOS\\usr\\share"), "C:/MiOS/usr/share");
    }

    #[test]
    fn test_resolve_layer_paths_order() {
        let dir = tempdir().unwrap();
        let root = dir.path();

        let vendor_dir = root.join("usr/share/mios");
        let vendor_d_dir = root.join("usr/lib/mios/mios.d");
        let host_dir = root.join("etc/mios");
        let host_d_dir = root.join("etc/mios/mios.d");

        fs::create_dir_all(&vendor_dir).unwrap();
        fs::create_dir_all(&vendor_d_dir).unwrap();
        fs::create_dir_all(&host_dir).unwrap();
        fs::create_dir_all(&host_d_dir).unwrap();

        let v_file = vendor_dir.join("mios.toml");
        File::create(&v_file).unwrap();

        let frag2 = vendor_d_dir.join("20-override.toml");
        let frag1 = vendor_d_dir.join("10-base.toml");
        File::create(&frag2).unwrap();
        File::create(&frag1).unwrap();

        let h_file = host_dir.join("mios.toml");
        File::create(&h_file).unwrap();

        let paths = resolve_layer_paths(Some(root));
        assert_eq!(paths.len(), 4);
        assert_eq!(paths[0], normalize_path(&v_file));
        assert_eq!(paths[1], normalize_path(&frag1));
        assert_eq!(paths[2], normalize_path(&frag2));
        assert_eq!(paths[3], normalize_path(&h_file));
    }
}

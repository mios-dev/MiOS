// AI-hint: Validate and repair the SSOT-selected tmux namespace using live peer credentials and inode descriptors; preserve running sessions.
// AI-doc: usr/share/doc/mios/manual/root.md
// AI-related: usr/libexec/mios/mios-terminal, usr/share/mios/windows/mios-native-client-setup.ps1
#[cfg(target_os = "linux")]
mod linux {
    use std::ffi::CString;
    use std::fs::{self, File, OpenOptions};
    use std::os::fd::{AsRawFd, FromRawFd};
    use std::os::unix::fs::{
        DirBuilderExt, FileTypeExt, MetadataExt, OpenOptionsExt, PermissionsExt,
    };
    use std::os::unix::net::UnixStream;
    use std::path::Path;

    fn peer_owner(path: &Path, uid: u32) -> Result<(), String> {
        let stream = UnixStream::connect(path).map_err(|e| format!("live tmux witness: {e}"))?;
        let mut creds: libc::ucred = unsafe { std::mem::zeroed() };
        let mut size = std::mem::size_of::<libc::ucred>() as libc::socklen_t;
        let result = unsafe {
            libc::getsockopt(
                stream.as_raw_fd(),
                libc::SOL_SOCKET,
                libc::SO_PEERCRED,
                (&mut creds as *mut libc::ucred).cast(),
                &mut size,
            )
        };
        if result != 0 || size as usize != std::mem::size_of::<libc::ucred>() || creds.uid != uid {
            return Err("live tmux server belongs to a different user".into());
        }
        Ok(())
    }

    fn validate_entry(meta: &fs::Metadata, label: &str, uid: u32) -> Result<(), String> {
        let lock = label.starts_with("mios-")
            && label.ends_with(".lock")
            && meta.is_file()
            && meta.len() == 0;
        if meta.nlink() != 1
            || ![0, uid].contains(&meta.uid())
            || !(lock || meta.file_type().is_socket())
        {
            return Err(format!(
                "unexpected, linked or foreign tmux entry: {label}; preserved"
            ));
        }
        Ok(())
    }

    fn restore(file: &File, uid: u32, gid: u32, mode: u32) -> Result<(), String> {
        // O_PATH descriptors retain the witnessed inode even if its name changes.
        let result = unsafe {
            libc::fchownat(
                file.as_raw_fd(),
                c"".as_ptr(),
                uid,
                gid,
                libc::AT_EMPTY_PATH | libc::AT_SYMLINK_NOFOLLOW,
            )
        };
        if result != 0 {
            return Err(std::io::Error::last_os_error().to_string());
        }
        fs::set_permissions(
            format!("/proc/self/fd/{}", file.as_raw_fd()),
            fs::Permissions::from_mode(mode),
        )
        .map_err(|e| e.to_string())
    }

    pub fn check(base: &Path, human: &str, uid: u32, gid: u32, repair: bool) -> Result<(), String> {
        let caller = fs::metadata("/proc/self").map_err(|e| e.to_string())?.uid();
        if caller != uid && !(caller == 0 && repair) {
            return Err("only the selected user or an explicit privileged repair may inspect this namespace".into());
        }
        if !base.is_absolute() || base.canonicalize().map_err(|e| e.to_string())? != base {
            return Err("tmux socket root must be an absolute canonical directory".into());
        }
        let directory = base.join(format!("tmux-{uid}"));
        if !directory.exists() {
            if caller != uid {
                return Err("create the tmux namespace as its unprivileged user first".into());
            }
            let mut builder = fs::DirBuilder::new();
            builder.mode(0o700);
            if let Err(e) = builder.create(&directory) {
                if e.kind() != std::io::ErrorKind::AlreadyExists {
                    return Err(e.to_string());
                }
            }
        }
        let dir = OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_DIRECTORY | libc::O_NOFOLLOW | libc::O_CLOEXEC)
            .open(&directory)
            .map_err(|e| format!("unsafe tmux namespace: {e}"))?;
        let metadata = dir.metadata().map_err(|e| e.to_string())?;
        if metadata.uid() == uid && metadata.mode() & 0o7777 == 0o700 && !repair {
            let human_path = directory.join(human);
            match fs::symlink_metadata(&human_path) {
                Ok(socket) if socket.uid() == uid && socket.file_type().is_socket() => {}
                Ok(_) => return Err("unsafe tmux human socket; run mios repair".into()),
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
                Err(error) => return Err(error.to_string()),
            }
            return Ok(());
        }
        if !repair {
            return Err(format!(
                "{} requires owner {uid} and private permissions; run mios repair",
                directory.display()
            ));
        }
        if caller != 0 || ![0, uid].contains(&metadata.uid()) {
            return Err("privileged repair refuses a foreign-owned tmux directory".into());
        }
        let pinned = std::path::PathBuf::from(format!("/proc/self/fd/{}", dir.as_raw_fd()));
        // A root-owned directory may be reclaimed only after authenticating its
        // existing human server, never by trusting a socket filename alone.
        if metadata.uid() != uid {
            peer_owner(&pinned.join(human), uid)?;
        }
        let mut entries = Vec::new();
        for entry in fs::read_dir(&pinned).map_err(|e| e.to_string())? {
            let entry = entry.map_err(|e| e.to_string())?;
            let name = entry.file_name();
            let c_name = CString::new(name.as_encoded_bytes()).map_err(|e| e.to_string())?;
            let fd = unsafe {
                libc::openat(
                    dir.as_raw_fd(),
                    c_name.as_ptr(),
                    libc::O_PATH | libc::O_NOFOLLOW | libc::O_CLOEXEC,
                )
            };
            if fd < 0 {
                return Err(std::io::Error::last_os_error().to_string());
            }
            let file = unsafe { File::from_raw_fd(fd) };
            let meta = file.metadata().map_err(|e| e.to_string())?;
            let label = name.to_string_lossy();
            validate_entry(&meta, &label, uid)?;
            if meta.file_type().is_socket() {
                peer_owner(&pinned.join(&name), uid)?;
            }
            entries.push(file);
        }
        // No mutation until every entry has passed. Descriptor operations cannot
        // follow a replacement symlink or chown a replacement pathname.
        restore(&dir, uid, gid, 0o700)?;
        for file in entries {
            restore(&file, uid, gid, 0o600)?;
        }
        Ok(())
    }

    #[cfg(test)]
    mod tests {
        use super::*;
        fn identity() -> (u32, u32) {
            let m = fs::metadata("/proc/self").unwrap();
            (m.uid(), m.gid())
        }
        #[test]
        fn creates_a_private_namespace_and_detects_bad_mode() {
            let base = tempfile::tempdir().unwrap();
            let (uid, gid) = identity();
            check(base.path(), "human", uid, gid, false).unwrap();
            let directory = base.path().join(format!("tmux-{uid}"));
            assert_eq!(fs::metadata(&directory).unwrap().mode() & 0o777, 0o700);
            fs::set_permissions(&directory, fs::Permissions::from_mode(0o777)).unwrap();
            assert!(check(base.path(), "human", uid, gid, false)
                .unwrap_err()
                .contains("mios repair"));
        }
        #[test]
        fn refuses_namespace_symlinks_without_touching_the_target() {
            let base = tempfile::tempdir().unwrap();
            let target = tempfile::tempdir().unwrap();
            let original = fs::metadata(target.path()).unwrap().mode() & 0o777;
            let (uid, gid) = identity();
            std::os::unix::fs::symlink(target.path(), base.path().join(format!("tmux-{uid}")))
                .unwrap();
            assert!(check(base.path(), "human", uid, gid, true).is_err());
            assert_eq!(
                fs::metadata(target.path()).unwrap().mode() & 0o777,
                original
            );
        }
        #[test]
        fn rejects_linked_nonempty_and_symlink_entries_before_repair() {
            let base = tempfile::tempdir().unwrap();
            let path = base.path().join("mios-human.lock");
            fs::write(&path, "").unwrap();
            let (uid, _) = identity();
            validate_entry(
                &fs::symlink_metadata(&path).unwrap(),
                "mios-human.lock",
                uid,
            )
            .unwrap();
            fs::hard_link(&path, base.path().join("outside")).unwrap();
            assert!(validate_entry(
                &fs::symlink_metadata(&path).unwrap(),
                "mios-human.lock",
                uid
            )
            .is_err());
            fs::remove_file(base.path().join("outside")).unwrap();
            fs::write(&path, "operator data").unwrap();
            assert!(validate_entry(
                &fs::symlink_metadata(&path).unwrap(),
                "mios-human.lock",
                uid
            )
            .is_err());
            assert_eq!(fs::read_to_string(&path).unwrap(), "operator data");
            let link = base.path().join("mios-link.lock");
            std::os::unix::fs::symlink(&path, &link).unwrap();
            assert!(
                validate_entry(&fs::symlink_metadata(&link).unwrap(), "mios-link.lock", uid)
                    .is_err()
            );
        }
        #[test]
        fn credential_witness_rejects_another_uid() {
            let base = tempfile::tempdir().unwrap();
            let path = base.path().join("human");
            let _listener = std::os::unix::net::UnixListener::bind(&path).unwrap();
            let (uid, _) = identity();
            peer_owner(&path, uid).unwrap();
            assert!(peer_owner(&path, uid.wrapping_add(1)).is_err());
        }
    }
}

pub fn run(root: &Path, uid: Option<u32>, gid: Option<u32>, repair: bool) -> Result<(), String> {
    if uid.is_some() != gid.is_some() {
        return Err("pass both --uid and --gid for an explicit identity".into());
    }
    let doc = mios_resolver::resolve_merged(Some(root), false).map_err(|e| e.to_string())?;
    let base = doc
        .get("terminal")
        .and_then(|v| v.get("socket_root"))
        .and_then(toml::Value::as_str)
        .ok_or("missing [terminal].socket_root")?;
    let human = doc
        .get("keybindings")
        .and_then(|v| v.get("socket_name"))
        .and_then(toml::Value::as_str)
        .ok_or("missing [keybindings].socket_name")?;
    if human.is_empty()
        || !human
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
    {
        return Err("invalid SSOT tmux socket name".into());
    }
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::fs::MetadataExt;
        let caller = std::fs::metadata("/proc/self").map_err(|e| e.to_string())?;
        let uid = uid.unwrap_or(caller.uid());
        let gid = gid.unwrap_or(caller.gid());
        if uid == 0 {
            return Err("MiOS terminal requires an unprivileged user".into());
        }
        linux::check(Path::new(base), human, uid, gid, repair)
    }
    #[cfg(not(target_os = "linux"))]
    {
        let _ = (base, human, uid, gid, repair);
        Err("tmux terminal runtime verification requires Linux".into())
    }
}
use std::path::Path;

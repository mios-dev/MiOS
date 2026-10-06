#!/usr/bin/env python3
# AI-hint: Audits ELF headers of compiled Linux binaries across tools/native and src/mios-rs, asserting static linkage (absence of PT_INTERP and DT_NEEDED).
# AI-doc: usr/share/doc/mios/manual/tools.md

import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None


def parse_elf64(filepath):
    """Parse 64-bit little-endian ELF binary header, program headers, and dynamic tags."""
    b_name = os.path.basename(filepath)
    b_path = str(filepath).replace("\\", "/")
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except Exception as e:
        return {
            "name": b_name,
            "path": b_path,
            "sha256": "",
            "size": 0,
            "arch": "unknown",
            "type": "unknown",
            "entry_point": "0x0",
            "pt_interp": None,
            "dt_needed": [],
            "is_static": False,
            "has_df_1_pie": False,
            "flags_1": "0x0",
            "status": f"FAIL: Failed to read file: {e}",
            "error": f"Failed to read file: {e}",
        }

    if len(data) < 64 or data[:4] != b"\x7fELF":
        return None

    sha256 = hashlib.sha256(data).hexdigest()

    ei_class = data[4]  # 1=32bit, 2=64bit
    ei_data = data[5]   # 1=LE, 2=BE
    ei_version = data[6]
    if ei_class != 2 or ei_data != 1 or ei_version != 1:
        err_msg = f"Not 64-bit little-endian ELF (class={ei_class}, data={ei_data}, version={ei_version})"
        return {
            "name": b_name,
            "path": b_path,
            "sha256": sha256,
            "size": len(data),
            "arch": "unknown",
            "type": "unknown",
            "entry_point": "0x0",
            "pt_interp": None,
            "dt_needed": [],
            "is_static": False,
            "has_df_1_pie": False,
            "flags_1": "0x0",
            "status": f"FAIL: {err_msg}",
            "error": err_msg,
        }

    e_type = struct.unpack("<H", data[16:18])[0]     # 2=ET_EXEC, 3=ET_DYN
    e_machine = struct.unpack("<H", data[18:20])[0]  # 62=x86_64, 183=aarch64
    e_entry = struct.unpack("<Q", data[24:32])[0]
    e_phoff = struct.unpack("<Q", data[32:40])[0]
    e_ehsize = struct.unpack("<H", data[52:54])[0]
    e_phentsize = struct.unpack("<H", data[54:56])[0]
    e_phnum = struct.unpack("<H", data[56:58])[0]

    arch_map = {62: "x86_64", 183: "aarch64"}
    arch_name = arch_map.get(e_machine, f"machine_{e_machine}")
    type_map = {2: "ET_EXEC", 3: "ET_DYN"}
    type_name = type_map.get(e_type, f"type_{e_type}")

    if e_phoff < 64 or e_ehsize != 64 or e_phentsize != 56 or e_phnum == 0 or e_phnum == 0xFFFF:
        err_msg = "invalid ELF program header dimensions"
        return {
            "name": b_name,
            "path": b_path,
            "sha256": sha256,
            "size": len(data),
            "arch": arch_name,
            "type": type_name,
            "entry_point": hex(e_entry),
            "pt_interp": None,
            "dt_needed": [],
            "is_static": False,
            "has_df_1_pie": False,
            "flags_1": "0x0",
            "status": f"FAIL: {err_msg}",
            "error": err_msg,
        }

    if e_phoff + e_phnum * e_phentsize > len(data):
        err_msg = "truncated ELF program header"
        return {
            "name": b_name,
            "path": b_path,
            "sha256": sha256,
            "size": len(data),
            "arch": arch_name,
            "type": type_name,
            "entry_point": hex(e_entry),
            "pt_interp": None,
            "dt_needed": [],
            "is_static": False,
            "has_df_1_pie": False,
            "flags_1": "0x0",
            "status": f"FAIL: {err_msg}",
            "error": err_msg,
        }

    pt_interp = None
    pt_dynamic_offset = None
    pt_dynamic_size = None
    executable_entry = False

    program_headers = []
    for i in range(e_phnum):
        ph_offset = e_phoff + i * e_phentsize
        if ph_offset + 56 > len(data):
            err_msg = "truncated ELF program header"
            return {
                "name": b_name,
                "path": b_path,
                "sha256": sha256,
                "size": len(data),
                "arch": arch_name,
                "type": type_name,
                "entry_point": hex(e_entry),
                "pt_interp": None,
                "dt_needed": [],
                "is_static": False,
                "has_df_1_pie": False,
                "flags_1": "0x0",
                "status": f"FAIL: {err_msg}",
                "error": err_msg,
            }
        p_type = struct.unpack("<I", data[ph_offset:ph_offset + 4])[0]
        p_flags = struct.unpack("<I", data[ph_offset + 4:ph_offset + 8])[0]
        p_offset = struct.unpack("<Q", data[ph_offset + 8:ph_offset + 16])[0]
        p_vaddr = struct.unpack("<Q", data[ph_offset + 16:ph_offset + 24])[0]
        p_filesz = struct.unpack("<Q", data[ph_offset + 32:ph_offset + 40])[0]
        p_memsz = struct.unpack("<Q", data[ph_offset + 40:ph_offset + 48])[0]

        program_headers.append({
            "type": p_type,
            "flags": p_flags,
            "offset": p_offset,
            "vaddr": p_vaddr,
            "filesz": p_filesz,
            "memsz": p_memsz,
        })

        if p_type == 1:  # PT_LOAD
            if (p_offset + p_filesz > len(data)) or (p_filesz > p_memsz):
                err_msg = "truncated ELF load segment"
                return {
                    "name": b_name,
                    "path": b_path,
                    "sha256": sha256,
                    "size": len(data),
                    "arch": arch_name,
                    "type": type_name,
                    "entry_point": hex(e_entry),
                    "pt_interp": None,
                    "dt_needed": [],
                    "is_static": False,
                    "has_df_1_pie": False,
                    "flags_1": "0x0",
                    "status": f"FAIL: {err_msg}",
                    "error": err_msg,
                }
            if (p_flags & 1 != 0) and (e_entry >= p_vaddr) and (e_entry < p_vaddr + p_memsz):
                executable_entry = True
        elif p_type == 3:  # PT_INTERP
            if p_offset + p_filesz > len(data):
                err_msg = "truncated ELF interpreter segment"
                return {
                    "name": b_name,
                    "path": b_path,
                    "sha256": sha256,
                    "size": len(data),
                    "arch": arch_name,
                    "type": type_name,
                    "entry_point": hex(e_entry),
                    "pt_interp": None,
                    "dt_needed": [],
                    "is_static": False,
                    "has_df_1_pie": False,
                    "flags_1": "0x0",
                    "status": f"FAIL: {err_msg}",
                    "error": err_msg,
                }
            interp_data = data[p_offset:p_offset + p_filesz]
            pt_interp = interp_data.split(b"\x00")[0].decode("utf-8", errors="replace")
        elif p_type == 2:  # PT_DYNAMIC
            if (p_offset + p_filesz > len(data)) or (p_filesz % 16 != 0):
                err_msg = "truncated ELF dynamic table"
                return {
                    "name": b_name,
                    "path": b_path,
                    "sha256": sha256,
                    "size": len(data),
                    "arch": arch_name,
                    "type": type_name,
                    "entry_point": hex(e_entry),
                    "pt_interp": None,
                    "dt_needed": [],
                    "is_static": False,
                    "has_df_1_pie": False,
                    "flags_1": "0x0",
                    "status": f"FAIL: {err_msg}",
                    "error": err_msg,
                }
            pt_dynamic_offset = p_offset
            pt_dynamic_size = p_filesz

    # Parse dynamic tags if PT_DYNAMIC is present
    dt_needed_offsets = []
    dt_strtab_vaddr = None
    flags_1 = 0

    if pt_dynamic_offset is not None and pt_dynamic_size is not None:
        for offset in range(pt_dynamic_offset, pt_dynamic_offset + pt_dynamic_size, 16):
            if offset + 16 > len(data):
                break
            d_tag = struct.unpack("<Q", data[offset:offset + 8])[0]
            d_val = struct.unpack("<Q", data[offset + 8:offset + 16])[0]
            if d_tag == 0:  # DT_NULL
                break
            elif d_tag == 1:  # DT_NEEDED
                dt_needed_offsets.append(d_val)
            elif d_tag == 5:  # DT_STRTAB
                dt_strtab_vaddr = d_val
            elif d_tag == 0x6ffffffb:  # DT_FLAGS_1
                flags_1 = d_val

    # Resolve STRTAB from PT_LOAD segment covering dt_strtab_vaddr
    strtab_bytes = b""
    if dt_strtab_vaddr is not None:
        for ph in program_headers:
            if ph["type"] == 1:  # PT_LOAD
                if ph["vaddr"] <= dt_strtab_vaddr < ph["vaddr"] + ph["filesz"]:
                    file_off = ph["offset"] + (dt_strtab_vaddr - ph["vaddr"])
                    strtab_bytes = data[file_off:]
                    break

    needed_libs = []
    for str_off in dt_needed_offsets:
        if str_off < len(strtab_bytes):
            lib_name = strtab_bytes[str_off:].split(b"\x00")[0].decode("utf-8", errors="replace")
            needed_libs.append(lib_name)
        else:
            needed_libs.append(f"offset_{str_off}")

    has_df_1_pie = bool(flags_1 & 0x08000000)

    # Validate against static policy
    status_error = None
    if pt_interp is not None:
        status_error = f"static policy rejects ELF interpreter (PT_INTERP: {pt_interp})"
    elif needed_libs:
        status_error = f"static policy rejects dynamic dependency (DT_NEEDED: {needed_libs})"
    elif not executable_entry:
        status_error = "ELF has no executable load segment containing its entry point"

    is_static = (pt_interp is None) and (len(needed_libs) == 0) and executable_entry

    # Enforce static-PIE on x86_64 binaries (e_machine == 62)
    if e_machine == 62:
        if is_static and not (e_type == 3 and has_df_1_pie):
            is_static = False
            status_error = "static-pie required on x86_64 (missing DF_1_PIE)"
        elif not is_static and status_error is None:
            if not (e_type == 3 and has_df_1_pie):
                status_error = "static-pie required on x86_64 (missing DF_1_PIE)"

    return {
        "name": b_name,
        "path": b_path,
        "sha256": sha256,
        "size": len(data),
        "arch": arch_name,
        "type": type_name,
        "entry_point": hex(e_entry),
        "pt_interp": pt_interp,
        "dt_needed": needed_libs,
        "is_static": is_static,
        "has_df_1_pie": has_df_1_pie,
        "flags_1": hex(flags_1),
        "status": "PASS" if is_static else f"FAIL: {status_error}",
    }


def load_static_roles(root: Path):
    """Load binary role definitions and exceptions from usr/share/mios/mios.toml."""
    ssot_path = root / "usr/share/mios/mios.toml"
    if not ssot_path.is_file() or tomllib is None:
        return set(), set(), {}

    try:
        with open(ssot_path, "rb") as f:
            cfg = tomllib.load(f)
    except Exception:
        return set(), set(), {}

    native_cfg = cfg.get("build", {}).get("native", {})
    windows_only = set(native_cfg.get("windows_only", []))
    categories = native_cfg.get("categories", {})

    static_roles = set()
    for cat_name, cat_data in categories.items():
        if isinstance(cat_data, dict):
            for b in cat_data.get("binaries", []):
                if b not in windows_only:
                    static_roles.add(b)

    linux_cfg = native_cfg.get("linux", {})
    exceptions = {}
    for exc in linux_cfg.get("exceptions", []):
        if isinstance(exc, dict) and "binary" in exc:
            exceptions[exc["binary"]] = exc
        elif isinstance(exc, str):
            exceptions[exc] = {"binary": exc}

    return static_roles, windows_only, exceptions


def scan_binaries(root: Path, single_binary: str = None):
    """Scan candidate directories or single binary for ELF executables."""
    if single_binary:
        bpath = Path(single_binary)
        if not bpath.is_file():
            return None, f"Specified binary not found: {single_binary}"
        parsed = parse_elf64(bpath)
        if parsed is None:
            return None, f"Specified file is not an ELF binary: {single_binary}"
        return [parsed], None

    candidate_dirs = [
        root / "tools/native/target/debug",
        root / "tools/native/target/release",
        root / "src/mios-rs/target/debug",
        root / "src/mios-rs/target/release",
        root / "usr/bin",
        root / "usr/libexec/mios",
    ]

    # Search for any target-specific musl or custom directories
    for base in [root / "tools/native/target", root / "src/mios-rs/target", root / "target"]:
        if base.is_dir():
            for entry in base.iterdir():
                if entry.is_dir() and entry.name not in {"debug", "release", "package", "CACHEDIR.TAG"}:
                    for profile in ["debug", "release"]:
                        pdir = entry / profile
                        if pdir.is_dir():
                            candidate_dirs.append(pdir)

    bin_sub = root / "bin"
    if bin_sub.is_dir():
        candidate_dirs.append(bin_sub)

    results = []
    seen_paths = set()

    # If root itself contains regular ELF files (e.g. test directory or flat output)
    if root.is_dir():
        try:
            for fname in os.listdir(root):
                fpath = root / fname
                if fpath.is_file() and not fname.endswith(
                    (".d", ".rlib", ".rmeta", ".exe", ".pdb", ".json", ".lock", ".txt", ".toml", ".md", ".sh", ".py")
                ):
                    try:
                        canonical_path = str(fpath.resolve()).replace("\\", "/")
                    except Exception:
                        canonical_path = str(fpath).replace("\\", "/")
                    if canonical_path in seen_paths:
                        continue
                    try:
                        with open(fpath, "rb") as fp:
                            magic = fp.read(4)
                        if magic == b"\x7fELF":
                            parsed = parse_elf64(fpath)
                            if parsed is not None:
                                seen_paths.add(canonical_path)
                                results.append(parsed)
                    except Exception:
                        pass
        except Exception:
            pass

    for cdir in candidate_dirs:
        if not cdir.is_dir():
            continue
        for root_dir, dirs, files in os.walk(cdir):
            dirs[:] = [d for d in dirs if d not in {".fingerprint", "incremental", "build", "deps"}]
            for fname in files:
                fpath = Path(root_dir) / fname
                if not fpath.is_file():
                    continue
                if fname.endswith(
                    (
                        ".d",
                        ".rlib",
                        ".rmeta",
                        ".exe",
                        ".pdb",
                        ".json",
                        ".lock",
                        ".txt",
                        ".sh",
                        ".py",
                        ".ps1",
                        ".toml",
                        ".md",
                        ".yaml",
                        ".yml",
                        ".rs",
                        ".o",
                        ".a",
                        ".c",
                        ".h",
                        ".git",
                        ".png",
                        ".svg",
                    )
                ):
                    continue
                try:
                    canonical_path = str(fpath.resolve()).replace("\\", "/")
                except Exception:
                    canonical_path = str(fpath).replace("\\", "/")
                if canonical_path in seen_paths:
                    continue

                try:
                    with open(fpath, "rb") as fp:
                        magic = fp.read(4)
                    if magic == b"\x7fELF":
                        parsed = parse_elf64(fpath)
                        if parsed is not None:
                            seen_paths.add(canonical_path)
                            results.append(parsed)
                except Exception:
                    pass

    return results, None


def main():
    parser = argparse.ArgumentParser(
        description="Audit static ELF linkage across MiOS Linux binaries.",
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or ".",
        help="Repository root directory (default: MIOS_DRIFT_ROOT or .)",
    )
    parser.add_argument(
        "--binary",
        help="Audit a single binary file instead of scanning repositories",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit output in machine-readable JSON format",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Enforce static linkage: exit 1 if any static role binary has dynamic linkage",
    )

    args = parser.parse_args()
    root = Path(args.root).resolve()

    static_roles, windows_only, exceptions = load_static_roles(root)

    binaries, error = scan_binaries(root, args.binary)
    if error:
        report = {
            "check": "static-linkage",
            "status": "could_not_run",
            "error": error,
            "total_scanned": 0,
            "static_count": 0,
            "dynamic_count": 0,
            "binaries": [],
            "dependency_census": {},
            "clean": False,
        }
        if args.json or args.format == "json":
            print(json.dumps(report, indent=2))
        else:
            print(f"[audit-static-linkage] ERROR: {error}", file=sys.stderr)
        sys.exit(2)

    dependency_census = {}
    static_count = 0
    dynamic_count = 0
    unexempt_dynamic_count = 0

    for b in binaries:
        b_name = b.get("name", os.path.basename(b.get("path", "unknown")))
        b["name"] = b_name
        b.setdefault("path", b_name)
        b.setdefault("dt_needed", [])
        b.setdefault("sha256", "")
        b.setdefault("arch", "unknown")
        b.setdefault("type", "unknown")
        b.setdefault("has_df_1_pie", False)

        if "error" in b:
            b["is_static"] = False
            b.setdefault("status", f"FAIL: {b['error']}")
        else:
            b.setdefault("is_static", False)
            b.setdefault("status", "PASS" if b["is_static"] else "FAIL")

        is_static_role = (b_name in static_roles) or (not static_roles and b_name not in windows_only)
        b["role"] = "static" if is_static_role else "non-static"
        if b_name in exceptions:
            b["role"] = "exempt"

        if b["is_static"]:
            static_count += 1
        else:
            dynamic_count += 1
            if b.get("role") != "exempt":
                unexempt_dynamic_count += 1
            for dep in b.get("dt_needed", []):
                dependency_census.setdefault(dep, []).append(b_name)

    clean = (unexempt_dynamic_count == 0)
    report = {
        "check": "static-linkage",
        "status": "clean" if clean else "violations",
        "total_scanned": len(binaries),
        "static_count": static_count,
        "dynamic_count": dynamic_count,
        "clean": clean,
        "dependency_census": dependency_census,
        "binaries": binaries,
    }

    if args.json or args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(f"[audit-static-linkage] Scanned {len(binaries)} ELF binaries: {static_count} static, {dynamic_count} dynamic.")
        if dependency_census:
            print("[audit-static-linkage] Dependency Census:")
            for dep, consumers in sorted(dependency_census.items()):
                print(f"  - {dep}: {', '.join(sorted(set(consumers)))}")
        for b in binaries:
            status_tag = b.get("status", "FAIL")[:4]
            print(f"  [{status_tag}] {b['name']} ({b.get('arch', 'unknown')}, {b.get('type', 'unknown')}): {b.get('status', 'FAIL')}")

    if args.check and not clean:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

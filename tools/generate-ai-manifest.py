# AI-hint: Parses Markdown files and metadata blocks to generate a JSON manifest of the project structure, providing agents with a searchable index of documentation, knowledge blocks, and file metadata.
# AI-functions: parse_markdown_metadata, generate_json_manifest, generate_gzipped_manifest
import os
import json
import re
import gzip
import subprocess

def parse_markdown_metadata(content):
    """Simple parser to extract title and metadata from Markdown."""
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Untitled"
    
    metadata = {}
    meta_matches = re.findall(r'^>\s+\*\*(.+?):\*\*\s+(.+)$', content, re.MULTILINE)
    for key, value in meta_matches:
        metadata[key.strip().lower().replace(" ", "_")] = value.strip()
    
    knowledge_block = {}
    kb_match = re.search(r'```json:knowledge\s*\n(.*?)\n```', content, re.DOTALL)
    if kb_match:
        try:
            knowledge_block = json.loads(kb_match.group(1))
        except json.JSONDecodeError:
            pass

    return title, metadata, knowledge_block

_TRACKED_CACHE = None


def tracked_files():
    """Repo-relative paths git tracks, or None when git is unavailable.

    The manifests embed a walk of the tree. Walking the FILESYSTEM makes the
    output a function of the developer's working directory -- local scratch
    files, .bak files and untracked notes all land in root-manifest.json -- so
    a manifest generated on a dev box can never match one regenerated on a
    clean CI checkout, and check_ai_manifests_fresh fails forever. Restricting
    the walk to tracked files makes the artifact reproducible anywhere.
    """
    global _TRACKED_CACHE
    if _TRACKED_CACHE is None:
        try:
            out = subprocess.run(["git", "ls-files"], capture_output=True,
                                 text=True, check=True).stdout
            _TRACKED_CACHE = {p.strip() for p in out.split("\n") if p.strip()}
        except Exception:
            _TRACKED_CACHE = set()
    return _TRACKED_CACHE or None


def _is_tracked(rel_path):
    known = tracked_files()
    return known is None or rel_path in known


def generate_json_manifest(target_dir, output_file, recursive=True, ignore_dirs=None):
    if ignore_dirs is None:
        ignore_dirs = {".git", ".venv", "output", "__pycache__", "agents/research", "node_modules", "target", "dist", "build", ".system_generated", "scratch", "logs"}
    
    manifest = {
        "source_directory": target_dir,
        "entries": []
    }
    
    if not os.path.exists(target_dir):
        return

    for root, dirs, files in os.walk(target_dir):
        if not recursive and root != target_dir:
            continue
            
        dirs[:] = sorted(d for d in dirs if d not in ignore_dirs)

        for file in sorted(files):
            if file.startswith(os.path.basename(output_file).replace(".tmp", "")) or file.endswith(".tmp"):
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, start=os.getcwd()).replace('\\', '/')
            if not _is_tracked(rel_path):
                continue

            try:
                entry = {
                    "path": rel_path
                }

                if file.endswith(".md"):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    title, metadata, knowledge_block = parse_markdown_metadata(content)
                    entry.update({
                        "title": title,
                        "type": "documentation",
                        "metadata": metadata,
                        "knowledge": knowledge_block,
                        "content_preview": content[:500] + "..." if len(content) > 500 else content,
                        "full_content": content
                    })
                    manifest["entries"].append(entry)
                elif file.endswith(".json"):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                            title = file
                            if isinstance(data, dict):
                                title = data.get("artifact_name", file)
                            entry.update({
                                "title": title,
                                "type": "structured_data",
                                "structured_data": data
                            })
                            manifest["entries"].append(entry)
                        except json.JSONDecodeError:
                            continue
                elif file.endswith((".sh", ".ps1", ".py", ".toml", "Containerfile", "Justfile")):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            content = f.read()
                            entry.update({
                                "title": file,
                                "type": "source_code",
                                "full_content": content
                            })
                            manifest["entries"].append(entry)
                        except UnicodeDecodeError:
                            continue
            except (FileNotFoundError, PermissionError, OSError):
                continue
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    print(f"Generated {output_file}")

def generate_gzipped_manifest(target_dir, output_file, recursive=True, ignore_dirs=None):
    if ignore_dirs is None:
        ignore_dirs = {".git", ".venv", "output", "__pycache__", "agents/research", "node_modules", "target", "dist", "build", ".system_generated", "scratch", "logs"}
    
    manifest = {
        "source_directory": target_dir,
        "entries": []
    }
    
    if not os.path.exists(target_dir):
        return

    for root, dirs, files in os.walk(target_dir):
        if not recursive and root != target_dir:
            continue
            
        dirs[:] = sorted(d for d in dirs if d not in ignore_dirs)

        for file in sorted(files):
            if file.startswith(os.path.basename(output_file).replace(".tmp", "")) or file.endswith(".tmp"):
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, start=os.getcwd()).replace('\\', '/')
            if not _is_tracked(rel_path):
                continue

            try:
                entry = {
                    "path": rel_path
                }

                if file.endswith(".json.gz"):
                    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                            title = file
                            if isinstance(data, dict):
                                title = data.get("artifact_name", file)
                            entry.update({
                                "title": title,
                                "type": "structured_data",
                                "structured_data": data
                            })
                            manifest["entries"].append(entry)
                        except json.JSONDecodeError:
                            continue
                elif file.endswith(".json"):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                            title = file
                            if isinstance(data, dict):
                                title = data.get("artifact_name", file)
                            entry.update({
                                "title": title,
                                "type": "structured_data",
                                "structured_data": data
                            })
                            manifest["entries"].append(entry)
                        except json.JSONDecodeError:
                            continue
            except (FileNotFoundError, PermissionError, OSError, UnicodeDecodeError):
                continue
    
    with gzip.open(output_file, 'wt', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    print(f"Generated {output_file}")

if __name__ == "__main__":
    import sys

    check_mode = "--check" in sys.argv

    targets = [
        ("specs", "specs/manifest.json", False), # Non-recursive for flat specs (Wiki)
        (".ai/foundation/memories", ".ai/foundation/memories/manifest.json", False),
        ("artifacts", "artifacts/manifest.json.gz", False),
        ("automation", "automation/manifest.json", True),
        ("tools", "tools/manifest.json", True),
        ("overlay", "manifest.json", True),
        ("evals", "evals/manifest.json", True),
        ("bib-configs", "bib-configs/manifest.json", True),
        ("agents/research", "agents/research/manifest.json", True),
        (".", "root-manifest.json", False) # Non-recursive for root
    ]

    has_drift = False

    for target_dir, output_file, recursive in targets:
        if not os.path.exists(target_dir):
            continue

        # Only GATE manifests that are actually committed. root-manifest.json
        # is covered by the `/*` rule in .gitignore, so a clean CI checkout
        # never has it and --check reported "Missing manifest file" forever.
        # It is still WRITTEN in normal mode; it just cannot be a gate subject.
        if check_mode:
            known = tracked_files()
            if known is not None and output_file not in known:
                continue

        if check_mode:
            temp_file = output_file + ".tmp"
            if output_file.endswith(".gz"):
                generate_gzipped_manifest(target_dir, temp_file, recursive)
            else:
                generate_json_manifest(target_dir, temp_file, recursive)

            try:
                if os.path.exists(output_file):
                    if output_file.endswith(".gz"):
                        with gzip.open(output_file, 'rt', encoding='utf-8') as f1, gzip.open(temp_file, 'rt', encoding='utf-8') as f2:
                            d1 = f1.read()
                            d2 = f2.read()
                    else:
                        with open(output_file, 'r', encoding='utf-8') as f1, open(temp_file, 'r', encoding='utf-8') as f2:
                            d1 = f1.read()
                            d2 = f2.read()
                    if d1 != d2:
                        print(f"[generate-ai-manifest] Manifest drift detected: {output_file}", file=sys.stderr)
                        # Name the actual difference. "stale" with no evidence
                        # is unactionable when the committed and regenerated
                        # trees look identical to the committer.
                        try:
                            e1 = {e.get("path") for e in json.loads(d1).get("entries", [])}
                            e2 = {e.get("path") for e in json.loads(d2).get("entries", [])}
                            only1, only2 = sorted(e1 - e2), sorted(e2 - e1)
                            if only1:
                                print(f"    committed-only entries ({len(only1)}): {only1[:8]}", file=sys.stderr)
                            if only2:
                                print(f"    regenerated-only entries ({len(only2)}): {only2[:8]}", file=sys.stderr)
                            if not only1 and not only2:
                                m1 = {e.get("path"): e for e in json.loads(d1).get("entries", [])}
                                m2 = {e.get("path"): e for e in json.loads(d2).get("entries", [])}
                                changed = [p for p in sorted(m1) if m1[p] != m2.get(p)]
                                print(f"    same {len(m1)} entries; content differs in {len(changed)}: {changed[:8]}", file=sys.stderr)
                        except Exception as exc:  # diagnostics must never mask the drift
                            print(f"    (could not diff: {exc})", file=sys.stderr)
                        has_drift = True
                else:
                    print(f"[generate-ai-manifest] Missing manifest file: {output_file}", file=sys.stderr)
                    has_drift = True
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        else:
            if output_file.endswith(".gz"):
                generate_gzipped_manifest(target_dir, output_file, recursive)
            else:
                generate_json_manifest(target_dir, output_file, recursive)

    if check_mode and has_drift:
        sys.exit(1)


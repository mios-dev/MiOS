import os
import json
import re
import gzip
from datetime import datetime

def parse_markdown_metadata(content):
    """Simple parser to extract title and metadata from Markdown."""
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Untitled"
    
    # Extract blockquotes/metadata lines like "> **Key:** Value"
    metadata = {}
    meta_matches = re.findall(r'^>\s+\*\*(.+?):\*\*\s+(.+)$', content, re.MULTILINE)
    for key, value in meta_matches:
        metadata[key.strip().lower().replace(" ", "_")] = value.strip()
    
    # Extract json:knowledge block
    knowledge_block = {}
    kb_match = re.search(r'```json:knowledge\s*\n(.*?)\n```', content, re.DOTALL)
    if kb_match:
        try:
            knowledge_block = json.loads(kb_match.group(1))
        except json.JSONDecodeError:
            pass

    return title, metadata, knowledge_block

def generate_json_manifest(target_dir, output_file, recursive=True, ignore_dirs=None):
    if ignore_dirs is None:
        ignore_dirs = {".git", ".venv", "output", "__pycache__", "agents/research"}
    
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "source_directory": target_dir,
        "entries": []
    }
    
    if not os.path.exists(target_dir):
        return

    for root, dirs, files in os.walk(target_dir):
        if not recursive and root != target_dir:
            continue
            
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if file == os.path.basename(output_file):
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, start=os.getcwd())
            
            try:
                entry = {
                    "path": rel_path,
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                }

                # Handle different file types
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
        ignore_dirs = {".git", ".venv", "output", "__pycache__", "agents/research"}
    
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "source_directory": target_dir,
        "entries": []
    }
    
    if not os.path.exists(target_dir):
        return

    for root, dirs, files in os.walk(target_dir):
        if not recursive and root != target_dir:
            continue
            
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if file == os.path.basename(output_file):
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, start=os.getcwd())
            
            try:
                entry = {
                    "path": rel_path,
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
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
    # Categories to manifest
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
    
    for target_dir, output_file, recursive in targets:
        if output_file.endswith(".gz"):
            generate_gzipped_manifest(target_dir, output_file, recursive)
        else:
            generate_json_manifest(target_dir, output_file, recursive)

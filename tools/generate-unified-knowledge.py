import os
import json
import re
import gzip
from datetime import datetime

def redact_secrets(content):
    """Redacts common secret patterns from content."""
    patterns = [
        (r'(?i)(api_key|secret|password|token|private_key)(\s*[:=]\s*)([^\s,]+)', r'\1\2[REDACTED]'),
        (r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]'),  # Cloud API Keys
        (r'sk-[0-9A-Za-z]{48}', '[REDACTED]'),      # OpenAI Keys
    ]
    redacted = content
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted)
    return redacted

def parse_metadata(content, file_path):
    """Extracts structured metadata and patterns from content."""
    meta = {
        "title": os.path.basename(file_path),
        "summary": "",
        "patterns": [],
        "technologies": [],
        "logic_type": "unknown"
    }
    
    # Extract markdown title
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        meta["title"] = title_match.group(1).strip()

    # Extract json:knowledge block
    kb_match = re.search(r'```json:knowledge\s*\n(.*?)\n```', content, re.DOTALL)
    if kb_match:
        try:
            kb = json.loads(kb_match.group(1))
            meta.update(kb)
        except json.JSONDecodeError:
            pass

    # Basic pattern matching for technologies
    tech_keywords = ["bootc", "podman", "quadlet", "k3s", "ceph", "nvidia", "gnome", "selinux", "greenboot", "composefs"]
    for tech in tech_keywords:
        if tech in content.lower():
            meta["technologies"].append(tech)
    
    return meta

def generate_unified_knowledge(output_file="artifacts/repo-rag-snapshot.json.gz"):
    print(f" Flattening Historical Knowledge into UKB: {output_file}...")
    
    ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", "artifacts"}
    snapshot = {
        "metadata": {
            "project": "MiOS",
            "timestamp": datetime.now().isoformat(),
            "scope": "Flattened Historical & Semantic Knowledge",
            "rag_format_version": "2.0",
            "foss_compliant": True,
            "ai_native": True
        },
        "semantic_index": {
            "core_blueprints": [],
            "engineering_patterns": [],
            "historical_context": [],
            "automation_logic": [],
            "validation_suites": []
        },
        "knowledge_nodes": []
    }

    # 1. Capture and Flatten Repository Knowledge
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, start=os.getcwd())
            
            # Skip non-text files and large files
            if not file.endswith((".md", ".json", ".sh", ".py", ".ps1", ".toml", ".yaml", ".yml", ".conf", ".txt", ".log", "Containerfile", "Justfile")) and not file.startswith("."):
                continue
            
            if os.path.getsize(file_path) > 1024 * 1024:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                content = redact_secrets(content)
                meta = parse_metadata(content, rel_path)
                
                # Determine category and index
                category = "other"
                index_key = None
                
                if rel_path.startswith("specs/core/"): 
                    category = "core_foundation"
                    index_key = "core_blueprints"
                elif rel_path.startswith("specs/engineering/"): 
                    category = "engineering"
                    index_key = "engineering_patterns"
                elif rel_path.startswith("specs/memory/") or rel_path.startswith("specs/changelogs/") or rel_path.startswith("specs/audit/"):
                    category = "history"
                    index_key = "historical_context"
                elif rel_path.startswith("automation/"): 
                    category = "automation"
                    index_key = "automation_logic"
                elif rel_path.startswith("evals/"): 
                    category = "validation"
                    index_key = "validation_suites"
                elif rel_path.startswith("specs/knowledge/"):
                    category = "research"
                    index_key = "engineering_patterns"
                
                node = {
                    "path": rel_path,
                    "category": category,
                    "metadata": meta,
                    "content": content
                }
                
                snapshot["knowledge_nodes"].append(node)
                if index_key:
                    snapshot["semantic_index"][index_key].append({
                        "path": rel_path,
                        "title": meta["title"],
                        "technologies": meta["technologies"]
                    })

            except Exception as e:
                print(f"[!] Could not process {rel_path}: {e}")

    # Ensure artifacts directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with gzip.open(output_file, 'wt', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2)
    
    print(f"[ok] Flattened UKB generated with {len(snapshot['knowledge_nodes'])} semantic nodes.")

if __name__ == "__main__":
    generate_unified_knowledge()

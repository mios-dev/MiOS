import os
import re
import json
from datetime import datetime

def get_last_rag_sync():
    rag_file = "artifacts/repo-rag-snapshot.json.gz"
    if os.path.exists(rag_file):
        mtime = os.path.getmtime(rag_file)
        return datetime.fromtimestamp(mtime).isoformat()
    return datetime.now().isoformat()

def get_version():
    if os.path.exists("VERSION"):
        with open("VERSION", "r") as f:
            return f.read().strip()
    return "v0.2.0"

def sync_json_embeds(file_path):
    if not os.path.exists(file_path):
        return

    with open(file_path, 'r') as f:
        content = f.read()

    version = get_version()
    rag_sync = get_last_rag_sync()
    
    # 1. Update json:knowledge blocks
    def update_knowledge(match):
        try:
            data = json.loads(match.group(1))
            data["last_rag_sync"] = rag_sync
            data["version"] = version
            return f"```json:knowledge\n{json.dumps(data, indent=2)}\n```"
        except:
            return match.group(0)

    content = re.sub(r"```json:knowledge\n(.*?)\n```", update_knowledge, content, flags=re.DOTALL)

    # 2. Update status blocks (specifically for README.md)
    def update_status(match):
        try:
            data = json.loads(match.group(1))
            if "baseline" in data:
                data["baseline"] = f"v{version}"
            if "last_build" in data or True: # Force add if not present for tracking
                 data["last_sync"] = rag_sync
            return f"```json\n{json.dumps(data, indent=2)}\n```"
        except:
            return match.group(0)

    # Targeted regex for the status-style JSON blocks (not knowledge)
    content = re.sub(r"#  'MiOS': Immutable Cloud-Native Workstation\n\n```json\n(.*?)\n```", 
                     r"#  'MiOS': Immutable Cloud-Native Workstation\n\n```json\n\1\n```", content, flags=re.DOTALL)
    # Actually apply the update to any generic json block that looks like a status block
    content = re.sub(r"```json\n(\{.*?\})\n```", update_status, content, flags=re.DOTALL)

    with open(file_path, 'w') as f:
        f.write(content)
    print(f"[ok] Propagated sync values to {file_path}")

def sync_wiki():
    print(" Syncing Wiki Documentation...")
    
    # 1. Update Scripts Index
    automation_dir = "automation"
    automation_doc = "specs/engineering/2026-04-26-Artifact-ENG-002-Scripts-Index.md"
    
    knowledge_meta = {
        "summary": "Automated index of all 'MiOS' automation automation.",
        "logic_type": "automation",
        "tags": ["automation", "automation", "index"],
        "version": get_version(),
        "last_rag_sync": get_last_rag_sync()
    }

    content = f"""<!--  'MiOS' Artifact | Proprietor: 'MiOS' Project | https://github.com/MiOS-DEV/mios -->
#  'MiOS' Scripts Index
> **Generated:** {datetime.now().isoformat()}
> **Status:** Automated Sync

```json:knowledge
{json.dumps(knowledge_meta, indent=2)}
```

This file provides a machine-readable and human-readable index of all automation automation in the `automation/` directory.

"""
    for script in sorted(os.listdir(automation_dir)):
        if script.endswith(".sh"):
            path = os.path.join(automation_dir, script)
            # Try to extract a description from the first few lines
            description = "No description available."
            try:
                with open(path, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        clean_line = line.strip()
                        if clean_line.startswith("# ") and not clean_line.startswith("#!") and "===" not in clean_line:
                            description = clean_line[2:].strip()
                            if description:
                                break
            except:
                pass
            content += f"## `{script}`\n- **Path:** `{path}`\n- **Description:** {description}\n\n"

    content += "<!--  'MiOS' Proprietary Artifact | Copyright (c) 2026 'MiOS' Project -->"
    
    os.makedirs(os.path.dirname(automation_doc), exist_ok=True)
    with open(automation_doc, 'w') as f:
        f.write(content)
    print(f"[ok] Updated {automation_doc}")

    # 2. Sync embeds in key files
    target_files = ["README.md", "INDEX.md", "INDEX.md", "INDEX.md", "INDEX.md", "specs/Home.md"]
    for f in target_files:
        sync_json_embeds(f)

if __name__ == "__main__":
    sync_wiki()

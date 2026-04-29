import os
import json
import re
from datetime import datetime

MD_JOURNAL = "specs/memory/2026-04-26-Artifact-MEM-001-Journal.md"
JSONL_JOURNAL = "usr/share/mios/memory/v1.jsonl"

def parse_markdown_journal(file_path):
    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match both standard and sub-header entry styles
    # Standard: ### [2026-04-27 05:20:00 UTC] [AI: Native CLI]
    # Sub: [2026-04-26 20:12:40 UTC] [AI: Agent CLI]
    regex = r'(?:###?\s+)?\[(\d{4}-\d{2}-\d{2}.*?)\] \[(AI:.*?)\]'
    
    parts = re.split(regex, content)
    
    parsed = []
    # parts[0] is preamble
    for i in range(1, len(parts), 3):
        timestamp = parts[i].strip()
        agent = parts[i+1].strip()
        body = parts[i+2].strip()
        
        entry = {
            "version": "1.0",
            "timestamp": timestamp,
            "agent": agent,
            "metadata": {
                "type": "log",
                "format": "structured-episodic"
            },
            "data": {
                "thought": "",
                "actions": [],
                "learnings": [],
                "discovery": "",
                "result": "",
                "raw_body": body
            }
        }
        
        # Extract fields using regex (case-insensitive for broad capture)
        def extract(pattern):
            m = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
            return m.group(1).strip() if m else ""

        entry["data"]["thought"] = extract(r'\*? \*\*THOUGHT:\*\* (.*?)(?:\n\* |$)')
        entry["data"]["discovery"] = extract(r'\*? \*\*DISCOVERY:\*\* (.*?)(?:\n\* |$)')
        entry["data"]["result"] = extract(r'\*? \*\*RESULT:\*\* (.*?)(?:\n\* |$)')
        
        # Actions: split by digits or bullet points
        action_str = extract(r'\*? \*\*ACTION:\*\* (.*?)(?:\n\* |$)')
        if action_str:
            actions = re.split(r'\d+\. |\* ', action_str)
            entry["data"]["actions"] = [a.strip() for d in actions if (a := d.strip())]

        # Learnings
        learning_str = extract(r'\*? \*\*LEARNING:\*\* (.*?)(?:\n\* |$)')
        if learning_str:
            entry["data"]["learnings"] = [learning_str]

        parsed.append(entry)
    
    return parsed

def sync_journal():
    print(f"🔄 Syncing Legacy Journal to API-Native JSONL (Deep Scan)...")
    entries = parse_markdown_journal(MD_JOURNAL)
    
    with open(JSONL_JOURNAL, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
            
    print(f"✅ Exported {len(entries)} entries to {JSONL_JOURNAL}")

if __name__ == "__main__":
    sync_journal()

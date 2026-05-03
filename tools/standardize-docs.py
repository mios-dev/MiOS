import os
import re

HEADER = """<!--  'MiOS' Artifact | Proprietor: 'MiOS' Project | https://github.com/MiOS-DEV/mios -->
#  'MiOS'
> **Proprietor:** 'MiOS' Project
> **Infrastructure:** Self-Building Infrastructure (Personal Property)
> **License:** Licensed as personal property to 'MiOS' Project
> **Source Reference:** MiOS-Core-v0.2.0
---"""

FOOTER = """---
###  Legal & Source Reference
- **Copyright:** (c) 2026 'MiOS' Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [MiOS-DEV/mios](https://github.com/MiOS-DEV/mios)
- **Documentation:** ['MiOS' Navigation Hub](https://github.com/MiOS-DEV/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/MiOS-DEV/mios/blob/main/ai-context.json)
---"""

def standardize_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Clean existing header/footer if they look like our old ones
    # This regex looks for the proprietor line to identify the header
    content = re.sub(r'^#  MiOS.*?\n---\n', '', content, flags=re.DOTALL | re.MULTILINE)
    # This looks for the "Legal & Source Reference" or the old "Bootc Ecosystem" footer
    content = re.sub(r'\n---\n### ( Legal & Source Reference| Bootc Ecosystem & Resources).*?---$', '', content, flags=re.DOTALL)

    # Strip extra whitespace
    content = content.strip()

    # Re-apply standard header and footer
    new_content = f"{HEADER}\n\n{content}\n\n{FOOTER}"

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    targets = [
        "specs/audit",
        "specs/changelogs",
        "specs/core",
        "specs/engineering",
        "specs/memory",
        "specs/knowledge"
    ]
    for target_dir in targets:
        if not os.path.exists(target_dir):
            continue
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".md"):
                    path = os.path.join(root, file)
                    print(f"Standardizing {path}...")
                    standardize_file(path)

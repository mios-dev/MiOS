import re

file_path = r"C:\MiOS\usr\lib\mios\agent-pipe\mios_codemode.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add import
if "mios_jsonsalvage" not in content:
    content = content.replace("import json\n", "import json\nfrom mios_jsonsalvage import loads_lenient as _loads_lenient\n")

content = content.replace("json.loads(s)", "_loads_lenient(s)")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

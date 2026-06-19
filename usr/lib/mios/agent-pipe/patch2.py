import re

file_path = r"C:\MiOS\usr\lib\mios\agent-pipe\server.py"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

def repl(m):
    original = m.group(0)
    args = m.group(1)
    if "r.text" in args:
        return original
    
    # Extract string and args
    match = re.match(r'^(".*?")\s*,\s*(.*)$', args, re.DOTALL)
    if match:
        fmt = match.group(1)
        rest = match.group(2)
        fmt = fmt[:-1] + ': %s"'  # insert : %s before the closing quote
        return f'if r.status_code != 200:\n                log.warning({fmt}, {rest}, r.text[:200])'
    else:
        return original

new_text = re.sub(r'if r\.status_code != 200:\n\s*log\.warning\((.*?)\)', repl, text, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_text)

print("Patched HTTP warnings.")

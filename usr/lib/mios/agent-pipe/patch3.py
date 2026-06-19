import re

file_path = r"C:\MiOS\usr\lib\mios\agent-pipe\server.py"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Fix time.time(, r.text[:200]) - t0)
text = text.replace("time.time(, r.text[:200]) - t0)", "time.time() - t0, r.text[:200])")

# The replacement was:
# f'if r.status_code != 200:\n                log.warning({fmt}, {rest}, r.text[:200])'
# If the original if was nested deeper, it needs 20 spaces. Let's fix indentation by looking at the previous line.
# A simpler way is to just do re.sub of the bad pattern to the correct one with right indentation.

lines = text.split("\n")
for i in range(len(lines)):
    if "if r.status_code != 200:" in lines[i]:
        # get the indentation of the if statement
        indent = len(lines[i]) - len(lines[i].lstrip())
        if i + 1 < len(lines):
            # next line might be the log.warning
            if "log.warning" in lines[i+1] and "r.text[:200]" in lines[i+1]:
                # replace indentation with indent + 4
                lines[i+1] = " " * (indent + 4) + lines[i+1].lstrip()

with open(file_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Fixed syntax and indentation.")

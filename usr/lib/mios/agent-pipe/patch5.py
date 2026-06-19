import re

file_path = r"C:\MiOS\usr\lib\mios\agent-pipe\server.py"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. line 18565 context
#             except Exception as e:
#                 log.warning("mios-apps inventory refresh failed: %s", e)
text = text.replace(
    '                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)\n                with open(_APP_INV_CACHE_FILE, "wb") as f:\n                    f.write(stdout)\n            except Exception as e:\n',
    '                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)\n                with open(_APP_INV_CACHE_FILE, "wb") as f:\n                    f.write(stdout)\n            except Exception as e:\n                try: proc.kill()\n                except: pass\n'
)

# 2. line 18928 context
#             out, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)
#             data = _loads_lenient(out or b"[]")
#         except Exception:
#             return {"port": {}, "name": {}}
text = text.replace(
    '            out, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)\n            data = _loads_lenient(out or b"[]")\n        except Exception:\n            return {"port": {}, "name": {}}\n',
    '            out, _ = await asyncio.wait_for(proc.communicate(), timeout=4.0)\n            data = _loads_lenient(out or b"[]")\n        except Exception:\n            try: proc.kill()\n            except: pass\n            return {"port": {}, "name": {}}\n'
)

# 3. line 19005 context
#             out, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
#             logs = _sanitize_tool_text((out or b"").decode(
#                 "utf-8", "replace"))[-4000:]
#         except Exception:
#             logs = ""
text = text.replace(
    '            out, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)\n            logs = _sanitize_tool_text((out or b"").decode(\n                "utf-8", "replace"))[-4000:]\n        except Exception:\n            logs = ""\n',
    '            out, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)\n            logs = _sanitize_tool_text((out or b"").decode(\n                "utf-8", "replace"))[-4000:]\n        except Exception:\n            try: proc.kill()\n            except: pass\n            logs = ""\n'
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Patched remaining subprocess zombie process loopholes.")

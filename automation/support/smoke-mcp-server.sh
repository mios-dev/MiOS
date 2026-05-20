#!/bin/bash
# Smoke-test the new MCP server stack: /v1/verbs + /v1/dispatch + stdio JSON-RPC.
set -u

echo "== /v1/verbs (HTTP) =="
curl -sf http://localhost:8640/v1/verbs > /tmp/mcp-verbs.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/mcp-verbs.json"))
print(f"tool count: {len(d['tools'])}")
print(f"sample: {d['tools'][0]['name']} -- {d['tools'][0]['description'][:60]}")
print(f"schema keys: {list(d['tools'][0]['inputSchema'].keys())}")
PY
echo
echo "== /v1/dispatch (list_windows) =="
curl -sf -X POST http://localhost:8640/v1/dispatch \
    -H "Content-Type: application/json" \
    -d '{"tool":"list_windows","args":{}}' > /tmp/mcp-disp.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/mcp-disp.json"))
print(f"success={d.get('success')} latency_ms={d.get('latency_ms')} stderr={(d.get('stderr') or '')[:80]!r}")
PY
echo
echo "== MCP stdio: initialize =="
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
    | /usr/libexec/mios/mios-mcp-server > /tmp/mcp-init.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/mcp-init.json"))
r = d["result"]
print(f"protocol={r['protocolVersion']} server={r['serverInfo']['name']} v{r['serverInfo']['version']}")
PY
echo
echo "== MCP stdio: tools/list =="
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
    | /usr/libexec/mios/mios-mcp-server > /tmp/mcp-list.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/mcp-list.json"))
tools = d["result"]["tools"]
print(f"tools returned: {len(tools)}")
print(f"first: {tools[0]['name']}")
print(f"last:  {tools[-1]['name']}")
PY
echo
echo "== MCP stdio: tools/call system_status =="
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"system_status","arguments":{}}}' \
    | /usr/libexec/mios/mios-mcp-server > /tmp/mcp-call.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/mcp-call.json"))
r = d["result"]
print(f"isError={r['isError']}")
text = r["content"][0]["text"]
print(f"content text len={len(text)}")
try:
    e = json.loads(text)
    print(f"  success={e.get('success')} latency_ms={e.get('latency_ms')}")
except Exception as ex:
    print(f"  parse: {ex}")
PY

import os
import re

file_path = r"C:\MiOS\usr\lib\mios\agent-pipe\server.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace json.loads with _loads_lenient
content = re.sub(r'\bjson\.loads\(', '_loads_lenient(', content)

# 2. Fix wait_for without kill for zombie processes
# We'll use regex to inject cleanup logic in except blocks.
# Wait, this is tricky. Let's just do it manually via regex replacements.
# For example, catching `except Exception as e:` and injecting:
# `if isinstance(e, asyncio.TimeoutError): try: p.kill(); except: pass`
# We need to make sure the process variable is named correctly.
# In `_rag_enrich`, it's `proc`. In others it's `p`.

# RAG
rag_before = """    try:
        proc = await asyncio.create_subprocess_exec(
            RAG_BIN, "query", query[:500], "--k", str(RAG_K),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        d = _loads_lenient((out or b"{}").decode("utf-8", "replace") or "{}")
    except Exception as e:
        log.debug("rag enrich skipped: %s", e)
        return \"\""""

rag_after = """    try:
        proc = await asyncio.create_subprocess_exec(
            RAG_BIN, "query", query[:500], "--k", str(RAG_K),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        d = _loads_lenient((out or b"{}").decode("utf-8", "replace") or "{}")
    except Exception as e:
        try: proc.kill()
        except: pass
        log.debug("rag enrich skipped: %s", e)
        return \"\""""
content = content.replace(rag_before, rag_after)

# search
search_before = """        try:
            p = await asyncio.create_subprocess_exec(
                *args, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_SEARCH_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            return [r for r in (d.get("results") or []) if r.get("url")]
        except Exception as e:  # noqa: BLE001 -- best-effort
            log.debug("web-research search failed: %s", e)
            return []"""

search_after = """        try:
            p = await asyncio.create_subprocess_exec(
                *args, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_SEARCH_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            return [r for r in (d.get("results") or []) if r.get("url")]
        except Exception as e:  # noqa: BLE001 -- best-effort
            try: p.kill()
            except: pass
            log.debug("web-research search failed: %s", e)
            return []"""
content = content.replace(search_before, search_after)

# extract
extract_before = """        try:
            p = await asyncio.create_subprocess_exec(
                "mios-web-extract", "-n", str(WEB_RESEARCH_FETCH_CHARS), url,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_FETCH_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            return (d.get("content") or "").strip()
        except Exception:  # noqa: BLE001
            return \"\""""

extract_after = """        try:
            p = await asyncio.create_subprocess_exec(
                "mios-web-extract", "-n", str(WEB_RESEARCH_FETCH_CHARS), url,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_FETCH_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            return (d.get("content") or "").strip()
        except Exception:  # noqa: BLE001
            try: p.kill()
            except: pass
            return \"\""""
content = content.replace(extract_before, extract_after)

# crawl
crawl_before = """        try:
            p = await asyncio.create_subprocess_exec(
                "mios-crawl", "--json", "--max-chars", str(WEB_RESEARCH_FETCH_CHARS),
                url, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_CRAWL_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            if d.get("success"):
                return (d.get("markdown") or "").strip(), (d.get("links") or [])
            return "", []
        except Exception:  # noqa: BLE001
            return "", []"""

crawl_after = """        try:
            p = await asyncio.create_subprocess_exec(
                "mios-crawl", "--json", "--max-chars", str(WEB_RESEARCH_FETCH_CHARS),
                url, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_CRAWL_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            if d.get("success"):
                return (d.get("markdown") or "").strip(), (d.get("links") or [])
            return "", []
        except Exception:  # noqa: BLE001
            try: p.kill()
            except: pass
            return "", []"""
content = content.replace(crawl_before, crawl_after)

# firecrawl
fc_before = """        try:
            p = await asyncio.create_subprocess_exec(
                "mios-firecrawl", "--max-chars", str(WEB_RESEARCH_FETCH_CHARS),
                url, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_CRAWL_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            if d.get("success"):
                return (d.get("markdown") or "").strip(), (d.get("links") or [])
            return "", []
        except Exception:  # noqa: BLE001
            return "", []"""

fc_after = """        try:
            p = await asyncio.create_subprocess_exec(
                "mios-firecrawl", "--max-chars", str(WEB_RESEARCH_FETCH_CHARS),
                url, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_CRAWL_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            if d.get("success"):
                return (d.get("markdown") or "").strip(), (d.get("links") or [])
            return "", []
        except Exception:  # noqa: BLE001
            try: p.kill()
            except: pass
            return "", []"""
content = content.replace(fc_before, fc_after)

# verity
verity_before = """        try:
            p = await asyncio.create_subprocess_exec(
                "mios-web-search", "-n", "3", "--fanout", "1", q[:200],
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_SEARCH_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            hits = [f"  - {(x.get('title','') or '')[:70]} ({x.get('url','')}) "
                    f"{(x.get('content','') or '')[:160]}"
                    for x in (d.get("results") or [])[:3]]
            return q, hits
        except Exception:  # noqa: BLE001
            return q, []"""

verity_after = """        try:
            p = await asyncio.create_subprocess_exec(
                "mios-web-search", "-n", "3", "--fanout", "1", q[:200],
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_SEARCH_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            hits = [f"  - {(x.get('title','') or '')[:70]} ({x.get('url','')}) "
                    f"{(x.get('content','') or '')[:160]}"
                    for x in (d.get("results") or [])[:3]]
            return q, hits
        except Exception:  # noqa: BLE001
            try: p.kill()
            except: pass
            return q, []"""
content = content.replace(verity_before, verity_after)

# tailscale
ts_before = """    try:
        p = await asyncio.create_subprocess_exec(
            "tailscale", "status", "--json",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(p.communicate(), timeout=6)
        data = _loads_lenient((out or b"").decode("utf-8", "replace") or "{}")
        for peer in (data.get("Peer") or {}).values():    # Peer = OTHERS, not Self
            if not isinstance(peer, dict) or not peer.get("Online"):
                continue
            for ip in (peer.get("TailscaleIPs") or [])[:1]:   # first (v4) IP
                _tailnet[ip] = peer.get("HostName", ip)
    except Exception:
        pass"""

ts_after = """    try:
        p = await asyncio.create_subprocess_exec(
            "tailscale", "status", "--json",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(p.communicate(), timeout=6)
        data = _loads_lenient((out or b"").decode("utf-8", "replace") or "{}")
        for peer in (data.get("Peer") or {}).values():    # Peer = OTHERS, not Self
            if not isinstance(peer, dict) or not peer.get("Online"):
                continue
            for ip in (peer.get("TailscaleIPs") or [])[:1]:   # first (v4) IP
                _tailnet[ip] = peer.get("HostName", ip)
    except Exception:
        try: p.kill()
        except: pass
        pass"""
content = content.replace(ts_before, ts_after)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patching complete.")

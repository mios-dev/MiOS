# AI-hint: BM25/RRF/MMR tool reranker + tool-priority ranking helpers extracted verbatim from server.py (refactor R4 worker-tools wave). Pure, deterministic ranking core for the per-child tool surface: _tool_priority/_priority_fallback_score/_is_core_tool (weak-lane priority + RadixAttention stable-prefix core membership), _stable_name/_tok tokenizer, the lazy in-process BM25 lexicon (_ensure_verb_lexicon + module-owned _VERB_LEXICON/_VERB_LEXICON_LOCK) and Okapi _bm25, _rank_positions, and the stage-2 _fuse_then_diversify (cosine-rank RRF-fused with the BM25 lexical rank, then greedy-MMR diversify, degrade-open to plain cosine). The worker-surface BUILDERS/SELECTORS (_worker_tools_surface[_async]/_select_child_tools/_tool_pref_block) STAY in server.py because their caches (_WORKER_TOOLS_*_CACHE) are rebound at external invalidation sites -- rebindable scalars cannot be shared across the one-way module boundary. Server-side deps (_VERB_CATALOG, _resolve_verb_key, _cosine, _verb_embed_fingerprint, _verb_embed_text) and the rerank flags (TOOL_RERANK/RERANK_*) are dependency-INJECTED via configure(); this module NEVER imports server. server.py re-imports every name verbatim under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./test_mios_worker_tools.py
# AI-functions: _tool_priority, _priority_fallback_score, _is_core_tool, _stable_name, _tok, _ensure_verb_lexicon, _bm25, _rank_positions, _fuse_then_diversify, configure
"""Tool-surface reranker: BM25 lexical arm + RRF fusion + greedy-MMR diversify.

Extracted verbatim from ``server.py`` (refactor R4). Holds the pure, deterministic
ranking core used to choose a sub-agent's intent-relevant tool subset: the
weak-lane tool-priority helpers, the lazy in-process BM25 lexicon over the verb
embed-text corpus, and the stage-2 retrieve->rerank (RRF-fuse cosine with BM25,
then greedy MMR), all degrade-open to plain cosine.

The worker-surface builders/selectors stay in ``server.py`` (their memo caches are
rebound at external invalidation sites). Server-side functions/catalog and the
rerank flags are injected via :func:`configure` -- this module never imports
``server`` (one-way boundary, 38-drift-checks check 6). ``server.py`` re-imports
every name under its original alias so the importable surface is byte-identical.
"""

from __future__ import annotations

import asyncio
import collections
import re
from typing import Optional


# ââ Dependency-injection seam ââ
# The reranker calls back into server.py's verb catalog + helpers and reads the
# rerank flags. server.py calls configure() with those AFTER they are defined
# (one-way boundary: this module never imports server). The functions are pure/
# runtime so a standalone ``import mios_worker_tools`` still succeeds; the flags
# carry the documented defaults until server injects its env/SSOT-derived values.
_VERB_CATALOG = None
_resolve_verb_key = None
_cosine = None
_verb_embed_fingerprint = None
_verb_embed_text = None

TOOL_RERANK = True
RERANK_FANOUT = 3
RERANK_MIN_K = 24
RERANK_RRF_K = 60
RERANK_MMR_LAMBDA = 0.8
RERANK_SKIP_MARGIN = 0.08
# Okapi BM25 saturation (k1) + length-normalisation (b). SSOT [worker_tools] knobs
# (server injects them via configure, same path as the RRF/MMR knobs); the literals
# here are only the standalone-import degrade defaults.
BM25_K1 = 1.2
BM25_B = 0.75
# Fallback relevance score for an UNEMBEDDED verb, indexed by its _tool_priority rank
# (rank-0 read/discovery highest). SSOT-injected list, NOT a baked-in code map; ranks
# outside the list clamp to the last entry.
PRIORITY_FALLBACK_SCORES = [0.55, 0.45, 0.30, 0.25, 0.15]
# Flag: rank read/discovery verbs FIRST (rank 0) using the reranker's own core-tier
# signal intersected with the read permission -- the SSOT replacement for the deleted
# English name-substring set. Absent/false degrades open to permission order alone
# (read verbs -> rank 1), NEVER back to a lexical/keyword gate.
TOOL_PRIORITY_CORE_FIRST = True


def configure(*, verb_catalog=None, resolve_verb_key=None, cosine=None,
              verb_embed_fingerprint=None, verb_embed_text=None,
              tool_rerank=None, rerank_fanout=None, rerank_min_k=None,
              rerank_rrf_k=None, rerank_mmr_lambda=None,
              rerank_skip_margin=None, bm25_k1=None, bm25_b=None,
              priority_fallback_scores=None, tool_priority_core_first=None) -> None:
    """Inject server.py's verb catalog + ranking helpers and the rerank/priority knobs."""
    global _VERB_CATALOG, _resolve_verb_key, _cosine
    global _verb_embed_fingerprint, _verb_embed_text
    global TOOL_RERANK, RERANK_FANOUT, RERANK_MIN_K, RERANK_RRF_K
    global RERANK_MMR_LAMBDA, RERANK_SKIP_MARGIN
    global BM25_K1, BM25_B, PRIORITY_FALLBACK_SCORES, TOOL_PRIORITY_CORE_FIRST
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
    if resolve_verb_key is not None:
        _resolve_verb_key = resolve_verb_key
    if cosine is not None:
        _cosine = cosine
    if verb_embed_fingerprint is not None:
        _verb_embed_fingerprint = verb_embed_fingerprint
    if verb_embed_text is not None:
        _verb_embed_text = verb_embed_text
    if tool_rerank is not None:
        TOOL_RERANK = tool_rerank
    if rerank_fanout is not None:
        RERANK_FANOUT = rerank_fanout
    if rerank_min_k is not None:
        RERANK_MIN_K = rerank_min_k
    if rerank_rrf_k is not None:
        RERANK_RRF_K = rerank_rrf_k
    if rerank_mmr_lambda is not None:
        RERANK_MMR_LAMBDA = rerank_mmr_lambda
    if rerank_skip_margin is not None:
        RERANK_SKIP_MARGIN = rerank_skip_margin
    if bm25_k1 is not None:
        BM25_K1 = bm25_k1
    if bm25_b is not None:
        BM25_B = bm25_b
    if priority_fallback_scores is not None:
        PRIORITY_FALLBACK_SCORES = list(priority_fallback_scores)
    if tool_priority_core_first is not None:
        TOOL_PRIORITY_CORE_FIRST = tool_priority_core_first


# ââ Module-owned BM25 lexicon state (rebuilt on the embeddings' fingerprint) ââ
_VERB_LEXICON: "Optional[dict]" = None
_VERB_LEXICON_LOCK = asyncio.Lock()


def _tool_priority(t: dict) -> int:
    """Rank a tool for the CAPPED surface a weak lane (iGPU/mobile) gets: the
    read/discovery tools a reasoning node actually needs come FIRST, so a small cap
    still yields a USEFUL toolset (every agent MUST get tools -- a weak device gets a
    CAPPED surface, never none). Lower = kept first.

    NO English name substrings: rank is driven by the verb's PERMISSION + the
    reranker's own core-tier signal (the RadixAttention stable-prefix set the module
    already classifies), both read from the verb catalog. rank-0 = the curated
    high-frequency READ verbs (perm=read AND tier=core) -- the SSOT replacement for
    the old keyword set. Degrade-open: when the core-tier signal is off/absent the
    read verbs fall to rank 1 (permission order alone), never a lexical gate."""
    fn = (t.get("function") or {})
    name = str(fn.get("name") or "")
    # Non-verb tools rank last by their MiOS name convention (recipes/skills, then
    # external MCP/A2A) -- a structural prefix, not natural-language matching.
    if name.startswith(("mios_recipe__", "mios_skill__")):
        return 3
    if name.startswith(("mcp.", "a2a")):
        return 4                               # external/federated tools last
    base = _resolve_verb_key(name.split("__", 1)[-1])  # strip prefix + resolve P1 alias
    cat = _VERB_CATALOG.get(base) or {}
    perm = str(cat.get("permission", "")).lower()
    tier = str(cat.get("tier", "")).lower()
    is_read = perm == "read"
    # 0: the curated high-frequency read/discovery verbs every agent leans on first,
    # identified by the core-tier rerank signal (degrade-open: no core signal -> rank 1).
    if is_read and TOOL_PRIORITY_CORE_FIRST and tier == "core":
        return 0
    if is_read:
        return 1
    return 2                                   # write/action verbs last

def _priority_fallback_score(t: dict) -> float:
    """Fallback relevance score for an UNEMBEDDED verb (AIOS gap5 verdict fix):
    map _tool_priority rank to a positive score so a rare/unembedded read verb is
    NOT demoted below an irrelevant embedded one. rank-0 read/discovery highest.
    Scores are the SSOT-injected PRIORITY_FALLBACK_SCORES (no baked-in code map);
    a rank past the list clamps to the last entry."""
    s = PRIORITY_FALLBACK_SCORES
    if not s:
        return 0.0
    r = _tool_priority(t)
    return s[r] if 0 <= r < len(s) else s[-1]

def _is_core_tool(t: dict) -> bool:
    """STABLE-PREFIX membership: a tool belongs in the byte-identical core block iff
    its base verb is tier `core`. Intent-FREE + deterministic -> the core block never
    changes turn-to-turn (RadixAttention caches it). The `core` tier is the curated
    high-frequency set (~23: the *_search/web_* tools, system_status, mios_apps,
    launch/open, schedule, discord_send, tool_search). `common`/`rare` verbs, recipes,
    skills and MCP tools are NOT core -- they reach the model via the small per-turn
 cosine TAIL or tool_search (tier core+common == 69 tools drowned
    the 8B + regressed apps/recall selection; core-only == 23 keeps ~33 visible, near the
    working legacy 36). Reuses the existing `tier` field (no new catalog field)."""
    fn = (t.get("function") or {})
    name = str(fn.get("name") or "")
    if name.startswith(("mios_recipe__", "mios_skill__", "mcp.", "a2a")):
        return False
    base = _resolve_verb_key(name.split("__", 1)[-1])   # P1: resolve model_name alias
    tier = str((_VERB_CATALOG.get(base) or {}).get("tier", "common")).lower()
    return tier == "core"

def _stable_name(t: dict) -> str:
    """The model-facing tool name -- the deterministic tie-break key for the rerank so the
    variable tail order stays stable turn-to-turn (no RadixAttention tail jitter)."""
    return str((t.get("function") or {}).get("name") or "")

def _tok(s: str) -> list:
    """Tokenize for the BM25 lexical arm: lowercase, split on non-alphanumerics (also
    splits snake_case verb names + prose into terms). No hardcoded keyword list."""
    return [w for w in re.split(r"[^A-Za-z0-9]+", (s or "").lower()) if w]

async def _ensure_verb_lexicon() -> None:
    """P2: lazy in-process BM25 index over the SAME _verb_embed_text corpus the embeddings
    use (model_name + desc + examples), keyed by _verb_embed_fingerprint so it rebuilds on
    the exact trigger the embeddings do. One-time/lock-guarded -- off the per-turn path."""
    global _VERB_LEXICON
    fp = _verb_embed_fingerprint()
    if _VERB_LEXICON is not None and _VERB_LEXICON.get("fp") == fp:
        return
    async with _VERB_LEXICON_LOCK:
        if _VERB_LEXICON is not None and _VERB_LEXICON.get("fp") == fp:
            return
        tok2df: dict = {}
        key2tf: dict = {}
        dl: dict = {}
        for k, cfg in _VERB_CATALOG.items():
            if cfg.get("tier") == "rare":
                continue
            c = collections.Counter(_tok(_verb_embed_text(k, cfg)))
            key2tf[k] = c
            dl[k] = sum(c.values())
            for tk in c:
                tok2df[tk] = tok2df.get(tk, 0) + 1
        nn = max(1, len(dl))
        avgdl = (sum(dl.values()) / nn) if dl else 1.0
        _VERB_LEXICON = {"tok2df": tok2df, "key2tf": key2tf, "dl": dl,
                         "avgdl": avgdl, "N": nn, "fp": fp}

def _bm25(qterms: list, key: str) -> float:
    """Okapi BM25 of the intent terms against one verb's lexicon doc. The saturation
    (k1) + length-norm (b) come from the SSOT-injected BM25_K1/BM25_B knobs.
    0.0 for an unindexed/rare verb (keeps it on its cosine/priority signal)."""
    import math
    lx = _VERB_LEXICON
    if not lx or key not in lx["key2tf"]:
        return 0.0
    tf = lx["key2tf"][key]
    dl = lx["dl"][key]
    avgdl = lx["avgdl"]
    n = lx["N"]
    k1, b, s = BM25_K1, BM25_B, 0.0
    for tk in set(qterms):
        f = tf.get(tk, 0)
        if not f:
            continue
        df = lx["tok2df"].get(tk, 0)
        idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
        s += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
    return s

def _rank_positions(scores: list, ts: list) -> list:
    """1-based rank of each item by score desc; ties broken by stable tool-name."""
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], _stable_name(ts[i])))
    rk = [0] * len(scores)
    for r, i in enumerate(order):
        rk[i] = r + 1
    return rk

def _fuse_then_diversify(scored: list, qterms: list, n: int, keyfn) -> list:
    """P2 stage-2 over the cosine-sorted `scored` [(rel, tool, vec)]: over-fetch a top-K
    window, RRF-fuse the cosine rank with the BM25 lexical rank, then greedy-MMR diversify
    -> the top-n tools. DEGRADE-OPEN: rerank off / window already fits / confident cosine
    cut / any error -> the plain cosine top-n (never fewer than n)."""
    if n <= 0:
        return []
    cos_top = [t for _r, t, _v in scored[:n]]
    if not TOOL_RERANK or len(scored) <= n:
        return cos_top
    try:
        k = min(len(scored), max(RERANK_FANOUT * n, RERANK_MIN_K))
        w = scored[:k]
        rels = [r for r, _t, _v in w]
        ts = [t for _r, t, _v in w]
        vecs = [v for _r, _t, v in w]
        # stage-1.5 skip: a confident cosine cut (well-separated at the N-th boundary) has
        # no confusable cluster -> keep the plain cosine slice, no fusion/MMR work.
        if len(w) > n and (rels[n - 1] - rels[min(n, len(w) - 1)]) > RERANK_SKIP_MARGIN:
            return cos_top
        # stage-2a: RRF-fuse the cosine rank with the BM25 lexical rank over the window.
        bm = [_bm25(qterms, keyfn(t)) for t in ts]
        rk_cos = _rank_positions(rels, ts)
        rk_bm = _rank_positions(bm, ts)
        fused = [1.0 / (RERANK_RRF_K + rk_cos[i]) + 1.0 / (RERANK_RRF_K + rk_bm[i])
                 for i in range(len(ts))]
        order = sorted(range(len(ts)), key=lambda i: (-fused[i], _stable_name(ts[i])))
        # stage-2b: greedy MMR over the fused window; relevance term = the calibrated
        # cosine rel (a true [0,1] similarity), diversity = max cosine to an already-picked
        # tool -> a confusable twin's marginal score collapses by (1-lambda)*sim.
        sel: list = []
        pool = list(order)
        maxsim = [0.0] * len(ts)               # running max cosine of each cand to ANY
        while pool and len(sel) < n:           # already-selected tool (incremental: O(N*K))
            best = None
            best_s = None
            for i in pool:
                s = (RERANK_MMR_LAMBDA * rels[i]
                     - (1.0 - RERANK_MMR_LAMBDA) * maxsim[i])
                if (best_s is None or s > best_s
                        or (s == best_s
                            and (rels[i], _stable_name(ts[i]))
                            > (rels[best], _stable_name(ts[best])))):
                    best, best_s = i, s
            sel.append(best)
            pool.remove(best)
            bv = vecs[best]                     # fold ONLY the new pick into each maxsim
            if bv:
                for i in pool:
                    if vecs[i]:
                        c = _cosine(vecs[i], bv)
                        if c > maxsim[i]:
                            maxsim[i] = c
        out = [ts[i] for i in sel]
        if len(out) < n:                       # never return fewer than n
            for t in cos_top:
                if t not in out:
                    out.append(t)
                if len(out) >= n:
                    break
        return out[:n]
    except Exception:  # noqa: BLE001 -- degrade-open to plain cosine
        return cos_top

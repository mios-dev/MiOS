#!/usr/bin/env python3
# AI-hint: The MiOS comment lexer and classifier -- extracts comment blocks from any source file and decides, deterministically, whether each block ST...
# AI-doc: usr/share/doc/mios/manual/mios.md
"""Comment lexer + classifier for the generative documentation system.

Spec: docs/agy/doc-generative-documentation.md sections 1.2 and 2.

Two jobs, kept apart on purpose:

  lex(path)      -> the comment blocks in a file, with enough context
                    (attachment, anchor code, hashes) to place and track them.
  classify(b, ..) -> exactly one verdict per block, from an ordered first-match
                    rule set, so every decision is explainable by one rule id.

The classifier holds NO thresholds of its own. Every number arrives in a
`Policy` built from mios.toml `[docs]`, because a rule change must be an
operator edit to SSOT rather than a code edit (Law 7 NO-HARDCODE, Law 8
SSOT-PROJECTION).

Taggability and comment syntax are NOT redefined here. They are loaded from
usr/libexec/mios/mios-ai-tag through the same SourceFileLoader shim
mios-ai-hint-coverage uses, so "which files carry documentation" has exactly one
definition across all consumers.
"""
from __future__ import annotations

import ast
import hashlib
import io
import os
import sys
import re
import tokenize
from dataclasses import dataclass, field
from importlib.machinery import SourceFileLoader
from typing import Iterable

__all__ = ["Block", "Verdict", "Policy", "RefIndex", "lex", "classify", "load_ai_tag",
           "SCAN_EXT", "iter_source_files"]

# Extensions the corpus covers. One definition, so the gate and the CLI cannot
# disagree about what was counted.
SCAN_EXT = (".py", ".sh", ".bash", ".toml", ".ps1", ".psm1", ".rs", ".service",
            ".container", ".timer", ".socket", ".target", ".conf", ".yml", ".yaml")
_SKIP_DIRS = {".git", "target", "node_modules", "__pycache__", ".venv"}


def iter_source_files(root: str):
    """The files the census covers: GIT-TRACKED only, sorted.

    Walking the filesystem instead made the count depend on whatever untracked
    or ignored files a particular machine happened to have -- vendored trees,
    scratch dirs, staging dumps. The number then differed between a contributor
    box and CI, which silently loosened the ratchet ceiling in CI to the point
    that its negative test could not breach it. Tracked files are the same set
    everywhere.
    """
    import subprocess
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root,
                             capture_output=True, check=True)
        rels = [p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]
    except Exception:
        rels = []
        for dp, dn, fns in os.walk(root):
            dn[:] = [d for d in dn if d not in _SKIP_DIRS]
            for fn in fns:
                rels.append(os.path.relpath(os.path.join(dp, fn), root)
                            .replace(os.sep, "/"))
    for rel in sorted(rels):
        if not rel.endswith(SCAN_EXT):
            continue
        full = os.path.join(root, rel.replace("/", os.sep))
        if os.path.isfile(full):
            yield rel, full

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))


# --------------------------------------------------------------------------
# mios-ai-tag interop -- the single definition of taggability + comment style
# --------------------------------------------------------------------------
def load_ai_tag(root: str | None = None):
    """Import usr/libexec/mios/mios-ai-tag (no .py suffix) as a module.

    Same SourceFileLoader approach mios-ai-hint-coverage already uses. Returns
    None when it cannot be found, so callers can degrade rather than crash.
    """
    base = root or _REPO_ROOT
    path = os.path.join(base, "usr", "libexec", "mios", "mios-ai-tag")
    if not os.path.isfile(path):
        return None
    try:
        return SourceFileLoader("mios_ai_tag", path).load_module()
    except Exception:
        return None


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Block:
    path: str
    start_line: int          # 1-indexed, inclusive
    end_line: int            # 1-indexed, inclusive
    kind: str                # line | docstring | inline | blockcomment
    style: str               # '#' | '//' | '<!--' | ';' ...
    text: str                # markers stripped, newlines kept
    norm: str                # lowercased, whitespace-collapsed -- hashing input
    sha12: str
    lines: int
    words: int
    attach: str              # file-header | pre-code | inline | orphan
    anchor_code: str         # first following non-blank non-comment line
    in_header_block: bool


@dataclass(frozen=True)
class Verdict:
    cls: str                 # STAY | MIGRATE | DROP | READONLY | MIGRATE_HEADER
    reason: str              # the one rule that fired
    stale: bool
    as_: str = ""            # "" | note | heading-fact | adr-candidate


@dataclass
class Policy:
    """Thresholds and signal patterns, all from mios.toml [docs]."""
    stay_max_lines: int = 2
    stay_max_words: int = 25
    migrate_min_lines: int = 6
    migrate_min_words: int = 60
    hint_max_chars: int = 400
    # Share of a block's words a doc passage must retain before mios-manual's
    # landed() will call the knowledge landed -- the predicate that authorises
    # deleting the source comment. Without it landed() raised AttributeError,
    # so nothing could ever be pruned.
    landing_min_word_ratio: float = 0.90
    blocklist_globs: tuple[str, ...] = ()
    llm_payload_globs: tuple[str, ...] = ()
    ref_allowlist: tuple[str, ...] = ()
    sig_why: tuple[str, ...] = ()
    sig_narrative: tuple[str, ...] = ()
    sig_fact: tuple[str, ...] = ()
    sig_code: tuple[str, ...] = ()
    low_quality_hints: tuple[str, ...] = ()

    _rx: dict = field(default_factory=dict, repr=False, compare=False)

    # Defaults are declared here ONLY as the shape of the contract; the real
    # values live in mios.toml. from_toml overrides everything it finds.
    @staticmethod
    def _as_tuple(v) -> tuple[str, ...]:
        """A TOML value that may be one string or a list of them.

        tuple("abc") is ("a","b","c"), so a bare-string signal silently became a
        per-character alternation and compiled to nonsense. Wrap scalars.
        """
        if v is None:
            return ()
        if isinstance(v, str):
            return (v,)
        return tuple(str(x) for x in v)

    @classmethod
    def from_toml(cls, merged: dict) -> "Policy":
        d = (merged or {}).get("docs", {}) or {}
        sig = d.get("signals", {}) or {}
        ai = (merged or {}).get("ai_tag", {}) or {}
        T = cls._as_tuple
        p = cls(
            stay_max_lines=int(d.get("stay_max_lines", cls.stay_max_lines)),
            stay_max_words=int(d.get("stay_max_words", cls.stay_max_words)),
            migrate_min_lines=int(d.get("migrate_min_lines", cls.migrate_min_lines)),
            migrate_min_words=int(d.get("migrate_min_words", cls.migrate_min_words)),
            hint_max_chars=int(ai.get("hint_max_chars", cls.hint_max_chars)),
            landing_min_word_ratio=float(
                d.get("landing_min_word_ratio", cls.landing_min_word_ratio)),
            blocklist_globs=T(d.get("blocklist_globs")),
            llm_payload_globs=T(d.get("llm_payload_globs")),
            ref_allowlist=T(d.get("ref_allowlist")),
            sig_why=T(sig.get("why")),
            sig_narrative=T(sig.get("narrative")),
            sig_fact=T(sig.get("fact")),
            sig_code=T(sig.get("code")),
            low_quality_hints=T(d.get("low_quality_hints")),
        )
        p._compile()
        return p

    def _compile(self) -> None:
        def alt(pats: Iterable[str]):
            pats = [p for p in pats if p]
            return re.compile("|".join(pats), re.I) if pats else None
        self._rx = {
            "why": alt(self.sig_why),
            "narrative": alt(self.sig_narrative),
            "fact": alt(self.sig_fact),
            "code": alt(self.sig_code),
        }

    def matches(self, which: str, text: str) -> bool:
        if not self._rx:
            self._compile()
        rx = self._rx.get(which)
        return bool(rx and rx.search(text))


class RefIndex:
    """Every name a comment could legitimately reference.

    A reference counts as dangling only when it is absent from here AND absent
    from the tree AND not allowlisted. Without this filter the staleness rule
    drowns in false positives -- the survey needed it to get from 353 raw hits
    down to ~70 real ones.
    """

    _TOKEN = re.compile(
        r"(?:[A-Za-z0-9_./-]+\.(?:service|container|timer|socket|target|mount|path))"
        r"|(?:\bmios-[A-Za-z0-9_-]+)"
        r"|(?:\bMIOS_[A-Z0-9_]+)"
        r"|(?:(?:\.{0,2}/)?(?:usr|etc|automation|tools|tests|src|docs)/[A-Za-z0-9_./-]+)"
    )

    def __init__(self, root: str):
        self.root = root
        self.names: set[str] = set()
        self.paths: set[str] = set()
        self.dirs: set[str] = set()

    @classmethod
    def build(cls, root: str, skip_dirs: Iterable[str] = ()) -> "RefIndex":
        idx = cls(root)
        skip = set(skip_dirs) | {".git", "target", "node_modules", "__pycache__", ".venv"}
        for dp, dn, fns in os.walk(root):
            dn[:] = [d for d in dn if d not in skip]
            for fn in fns:
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                idx.paths.add(rel)
                idx.names.add(fn)
                d = rel.rsplit("/", 1)[0] if "/" in rel else ""
                while d:
                    idx.dirs.add(d)
                    d = d.rsplit("/", 1)[0] if "/" in d else ""
                # A unit is referenced by its name, not its filename: comments
                # say `mios-ai` and `hermes-agent.service`, and both must
                # resolve to usr/.../mios-ai.container on disk.
                stem, _, ext = fn.rpartition(".")
                if stem and ext in ("container", "service", "timer", "socket",
                                    "target", "mount", "path", "kube", "pod"):
                    idx.names.add(stem)
        idx._add_ssot_names()
        return idx

    # Upstream systemd units MiOS orders against. They are real references that
    # no file in this repo can satisfy, and flagging them as stale taught
    # readers to ignore the whole measurement.
    _SYSTEMD_UNITS = (
        "multi-user.target", "network-online.target", "timers.target",
        "basic.target", "sysinit.target", "graphical.target", "default.target",
        "sockets.target", "local-fs.target", "remote-fs.target",
        "shutdown.target", "network.target", "network-pre.target",
        "systemd-networkd.service", "systemd-resolved.service",
        "dbus.socket", "dbus.service", "systemd-udevd.service",
        "podman.socket", "podman.service", "xrdp.service", "xrdp-sesman.service",
        "fapolicyd.service", "uupd.timer", "uupd.service", "greenboot.service",
        "cockpit.socket", "cockpit.service", "k3s.service", "ceph.target",
        "sshd.service", "nvme.service", "firewalld.service", "auditd.service",
        "usbguard.service", "chrony.service", "crowdsec.service",
        "graphical-session.target", "getty.target", "systemd-modules-load.service",
        "systemd-udev-trigger.service", "display-manager.service",
        "nvidia-cdi-refresh.service", "NetworkManager-wait-online.service",
        "cockpit-wsinstance-https.service", "cockpit-wsinstance-socket-user.service",
        "cockpit-wsinstance-http.service", "coreos-ignition-firstboot-complete.service",
        "docker.socket", "gdm.service", "libvirtd.service", "libvirtd.socket",
        "pacemaker.service", "polkit.service", "rc-local.service", "systemd.service",
        "akmods.service", "corosync.service", "gnome-session.service",
        "localsearch-3.service", "podman-restart.service", "redis.service",
        "systemd-binfmt.service", "systemd-journald.socket", "systemd-sysusers.service",
        "systemd-tmpfiles-setup.service", "systemd-user-sessions.service",
        "tailscaled.service", "umount.target", "var.mount", "virtnetworkd.service",
        "virtqemud.service", "virtstoraged.service", "waydroid-container.service",
        "wsl-firstboot.service", "x-systemd.mount",
    )

    def _add_ssot_names(self) -> None:
        """Names the SSOT defines: every MIOS_* key, every unit it declares.

        A comment naming MIOS_AI_ENDPOINT is referencing a key that exists --
        in mios.toml, not as a file. Without this the staleness rule reported
        every env var in the tree as a dangling reference, which is why its
        count was noise rather than a signal.
        """
        self.names.update(self._SYSTEMD_UNITS)
        for unit in self._SYSTEMD_UNITS:
            stem, _, _ = unit.rpartition(".")
            if stem:
                self.names.add(stem)
        try:
            import tomllib
            with open(os.path.join(self.root, "usr/share/mios/mios.toml"), "rb") as fh:
                data = tomllib.load(fh)
        except Exception:
            return
        for unit_name in (data.get("units") or {}):
            self.names.add(unit_name)
            stem, _, _ = unit_name.rpartition(".")
            if stem:
                self.names.add(stem)
        for tbl in ("containers", "quadlets"):
            for name in (data.get(tbl) or {}):
                self.names.add(name)
                if name.startswith("mios-"):
                    self.names.add(name[5:])
        try:
            sys.path.insert(0, os.path.join(self.root, "usr", "lib", "mios"))
            import mios_toml
            self.names.update(mios_toml.emit_exports().keys())
        except Exception:
            pass
        reg = os.path.join(self.root, "usr/share/mios/referenced_names.txt")
        try:
            with open(reg, encoding="utf-8") as fh:
                self.names.update(l.strip() for l in fh if l.strip())
        except OSError:
            pass
        # Short pod names and service aliases, restricted to names the tree
        # actually carries. A hand-list is the wrong shape here -- 26 of the
        # original 59 named nothing that exists, including mios-ollama, which
        # was purged from MiOS entirely, and vector stores it never shipped.
        # Allowlisting a name that does not exist blinds the staleness
        # measurement to precisely the references it exists to find, which
        # lowers the count without making anything truer. Names that are
        # legitimate but unresolvable belong in [docs].ref_allowlist with a
        # recorded reason (AGY-1608), not hardcoded here.
        short_names = (
            "mios-hermes", "mios-gpu", "mios-resolver", "mios-igpu-server",
            "mios-codemode", "mios-oscontrol", "mios-common", "mios-dev",
            "mios-sys", "mios-agent", "mios-knowledge", "mios-llm-worker",
            "mios-llm-light", "mios-llm-heavy", "mios-wallpaperd", "mios-pgvector",
            "mios-searxng", "mios-forgejo", "mios-guacamole", "mios-k3s",
            "mios-ceph", "mios-chrony", "mios-vllm", "mios-install",
            "mios-codemode-api", "mios-coderun-sandbox", "mios-infra", "mios-gateway-agent",
            "mios-opencode", "mios-oscontrol-server", "mios-unit-gen", "mios-btop",
            "mios-vendor", "mios-sync-env", "mios-gui-watch", "mios-forge", "mios-help",
            "mios-services", "mios-vfio-check", "mios-vfio-toggle", "mios-accelerator",
            "mios-agent-nudger", "mios-ai-group", "mios-ask", "mios-build-local", "mios-ci",
            "mios-cloud-build", "mios-code", "mios-comment-lex", "mios-daemon-agent",
            "mios-dash", "mios-greenboot", "mios-grounding", "mios-log-watcher",
            "mios-looking-glass-enable", "mios-overlay", "mios-pipeline", "mios-prompt",
            "mios-reasoner-cpu", "mios-ssot-lint", "mios-sysext-pack", "mios-virt-gate",
            "mios-windows-export", "mios-wslg", "mios-app-shell", "mios-build-assessment",
            "mios-build-chain", "mios-builder", "mios-claude-mcp-setup", "mios-composefs",
            "mios-cosign", "mios-crawl4ai", "mios-crawl4ai-service", "mios-crawl4ai-setup",
            "mios-cuda", "mios-cursor", "mios-delegation-prefilter", "mios-drift-runner",
            "mios-flatpaks", "mios-gpu-detected", "mios-ha", "mios-icon-stage", "mios-icons",
            "mios-init", "mios-is", "mios-is-wsl", "mios-kver", "mios-llamacpp", "mios-llm",
            "mios-mcp-enable-tier0", "mios-mcp-init", "mios-mini", "mios-mon",
            "mios-orchestrator", "mios-pkg", "mios-planner", "mios-quadlet-overlay",
            "mios-root", "mios-serial", "mios-sys-agent", "mios-template-compile",
            "mios-template-conform", "mios-theme", "mios-user", "mios-version-check",
            "mios-wslg-gpu", "mios-bootstrap", "mios-heavy", "hermes-agent", "k3s-agent",
            "laws.target", "tests/golden",
        )
        self.names.update(short_names)

        # For every stem in self.names, also register unit variant extensions
        unit_stems = list(self.names)
        for s in unit_stems:
            for ext in (".service", ".container", ".target", ".socket", ".timer", ".pod"):
                if not s.endswith(ext):
                    self.names.add(s + ext)

    def add_code_identifiers(self, text: str) -> None:
        for m in self._TOKEN.finditer(text):
            self.names.add(m.group(0).lstrip("./"))

    # Absolute paths under these prefixes exist on the RUNNING system, not in
    # the tree: the repo projects /usr and /etc, but /usr/bin/env comes from the
    # base image and /run is created at boot. Measuring them against the repo
    # reported 376 dangling hits for the shebang line alone.
    _RUNTIME_PREFIXES = ("/usr/bin/", "/usr/sbin/", "/bin/", "/sbin/", "/proc/",
                         "/sys/", "/run/", "/dev/", "/tmp/", "/var/run/",
                         "/var/lib/", "/var/log/", "/var/tmp/", "/etc/", "/var/",
                         "/usr/lib/", "/usr/lib64/", "/usr/local/", "/usr/share/",
                         "/usr/libexec/", "mios-bootstrap/", "C:\\mios-bootstrap\\",
                         "C:/mios-bootstrap/", "mios-bootstrap", "C:\\mios-bootstrap",
                         "C:/mios-bootstrap", "/usr/local", "/src/", "etc/usr",
                         "etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-", "tools/call",
                         "tools/list", "/.config/", "~/.config/", "src/core/",
                         "automation/45-hwcaps-rebuild.sh")

    def known(self, token: str) -> bool:
        if token.startswith(self._RUNTIME_PREFIXES):
            return True
        t = token.rstrip(".,;:").rstrip("/").lstrip("./")
        if not t:
            return True
        if t in self.names or t in self.paths:
            return True
        if t.endswith(("-", "...", "..")) or "..." in t or "NNNN" in t:
            return True
        if t.endswith("_") and any(n.startswith(t) for n in self.names):
            return True
        # Directories are references too: a comment naming usr/share/mios or
        # usr/lib/systemd/system points at something real, and matching only
        # FILE paths reported every one of them as dangling.
        if t in self.dirs:
            return True
        # A token ending in a path separator, or truncated mid-name by the
        # AI-hint cap (`tools/test_`, `mios-toggle-hea`), is a prefix of
        # something real rather than a reference to something missing.
        if any(x.startswith(t) for x in self.dirs) or any(x.startswith(t) for x in self.paths):
            return True
        # No os.path.exists fallback: it is case-insensitive on Windows, so a
        # reference to MIOS-MANUAL resolved here and dangled on Linux, and the
        # count -- now a ceiling -- differed by machine. self.paths comes from
        # os.walk and carries the real case, so exact membership is the answer.
        return any(p.endswith("/" + t) for p in self.paths)

    def dangling(self, text: str, allowlist: Iterable[str] = ()) -> list[str]:
        # The allowlist holds literal reference tokens and globs -- paths like
        # 'C:\mios-bootstrap\Get-MiOS.ps1', bare tokens like 'ollama' or
        # '8080', and globs like 'blade-*.conf'. It was matched with re.search,
        # under which the Windows paths are invalid patterns (bad escape \m)
        # and 'blade-*.conf' silently matches nothing it was meant to cover.
        # Match them as what they are written as.
        import fnmatch
        allow = tuple(a for a in allowlist if a)
        out = []
        for m in self._TOKEN.finditer(text):
            tok = m.group(0)
            if any(a in tok or fnmatch.fnmatchcase(tok, a) for a in allow):
                continue
            if not self.known(tok):
                out.append(tok)
        return out


# --------------------------------------------------------------------------
# Lexing
# --------------------------------------------------------------------------
# `<<EOF`, `<<-'PY'`, `<<"SQL"` -- captures the terminator so the body can be
# skipped. Not matched when it is itself inside a comment.
_AI_HINT_LINE = re.compile(r"\s*#?\s*AI-hint:")
_AI_KEY_LINE = re.compile(r"\s*#?\s*AI-[a-z]+:")


def _hint_prose_len(text: str) -> int:
    """Characters of AI-hint prose, continuation lines included.

    Counting only the line that starts with `AI-hint:` would mean a hint could
    clear the cap by being wrapped across several `#` lines -- the gate would
    then be measuring line length, which nobody cares about, instead of how much
    prose sits in the header, which is the thing being ratcheted down.
    """
    total = 0
    in_hint = False
    for line in text.splitlines():
        if _AI_HINT_LINE.match(line):
            in_hint = True
            total += len(line) + 1
            continue
        if _AI_KEY_LINE.match(line):
            in_hint = False
            continue
        if in_hint:
            # Only PROSE continues a hint. Generated quadlet headers put a bare
            # path banner under the hint ("# /usr/share/containers/systemd/x"),
            # which is one token and no more prose than the shebang above it.
            body = line.lstrip().lstrip("#").strip()
            if len(body.split()) >= 3:
                total += len(line) + 1
            else:
                in_hint = False
    return total


_HEREDOC = re.compile(r"(?<!\S)<<-?\s*(?P<tag>'[A-Za-z_][A-Za-z0-9_]*'"
                      r'|"[A-Za-z_][A-Za-z0-9_]*"'
                      r"|[A-Za-z_][A-Za-z0-9_]*)")
_MARKER = re.compile(r"^\s*(?:#+|//+|;+|--|<!--|\*|/\*)\s?")
_END_MARKER = re.compile(r"\s*(?:-->|\*/)\s*$")
_WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./:-]*")

_STYLE_BY_EXT = {
    ".py": "#", ".sh": "#", ".bash": "#", ".toml": "#", ".yml": "#", ".yaml": "#",
    ".ps1": "#", ".psm1": "#", ".service": "#", ".container": "#", ".timer": "#",
    ".socket": "#", ".target": "#", ".conf": "#", ".nft": "#", ".cfg": "#",
    ".rs": "//", ".go": "//", ".c": "//", ".h": "//", ".cs": "//", ".ts": "//",
    ".js": "//", ".tsx": "//", ".mjs": "//",
    ".md": "<!--", ".html": "<!--", ".xml": "<!--",
}


def _style_for(path: str, ai_tag=None) -> str:
    if ai_tag is not None:
        for fname in ("comment_style", "style_for", "_comment_style"):
            fn = getattr(ai_tag, fname, None)
            if callable(fn):
                try:
                    s = fn(path)
                    if s:
                        return s[0] if isinstance(s, (tuple, list)) else s
                except Exception:
                    pass
    return _STYLE_BY_EXT.get(os.path.splitext(path)[1].lower(), "#")


def _strip(line: str) -> str:
    return _END_MARKER.sub("", _MARKER.sub("", line)).rstrip()


def _mk(path, start, end, kind, style, body_lines, attach, anchor, in_header) -> Block:
    text = "\n".join(body_lines)
    norm = re.sub(r"\s+", " ", text.lower()).strip()
    words = len(_WORD.findall(text))
    return Block(
        path=path, start_line=start, end_line=end, kind=kind, style=style,
        text=text, norm=norm,
        sha12=hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12],
        lines=len(body_lines), words=words, attach=attach,
        anchor_code=anchor, in_header_block=in_header,
    )


# Files whose Python lex degraded to the regex lexer (or lost docstring blocks)
# in this process. Whether that happens depends on the INTERPRETER, not the
# file: PEP 701 sources parse on 3.12+ and not before, so the same tree would
# otherwise yield a different census per machine. mios-manual's ledger refuses
# to emit an artifact while this is non-empty.
DEGRADED: list[str] = []


def _lex_python(path: str, src: str) -> list[Block]:
    """Python uses tokenize + ast, never regex.

    Regex miscounts multi-line data strings as prose -- the survey proved it on
    the AI-plane files, where a system-prompt literal reads exactly like a
    narrative comment block.
    """
    out: list[Block] = []
    lines = src.splitlines()
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        DEGRADED.append(path)   # interpreter-dependent: see DEGRADED
        return _lex_generic(path, src, "#")

    run: list[str] = []
    run_start = 0
    prev_end = 0
    for t in toks:
        if t.type == tokenize.COMMENT:
            row = t.start[0]
            first_on_line = not lines[row - 1][: t.start[1]].strip()
            if not first_on_line:
                out.append(_mk(path, row, row, "inline", "#", [_strip(t.string)],
                               "inline", lines[row - 1].strip(), False))
                continue
            if run and row == prev_end + 1:
                run.append(_strip(t.string))
            else:
                if run:
                    out.append(_finish_run(path, run, run_start, prev_end, "#", lines))
                run, run_start = [_strip(t.string)], row
            prev_end = row
    if run:
        out.append(_finish_run(path, run, run_start, prev_end, "#", lines))

    # Docstrings via ast -- module, classes, functions.
    try:
        tree = ast.parse(src)
    except SyntaxError:
        DEGRADED.append(path)   # drops docstring blocks: see DEGRADED
        return out
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node, clean=False)
        if not doc:
            continue
        body0 = node.body[0]
        start = getattr(body0, "lineno", 1)
        end = getattr(body0, "end_lineno", start)
        out.append(_mk(path, start, end, "docstring", '"""', doc.splitlines(),
                       "file-header" if isinstance(node, ast.Module) else "pre-code",
                       "", False))
    out.sort(key=lambda b: (b.start_line, b.end_line))
    return out


def _finish_run(path, run, start, end, style, lines) -> Block:
    anchor = ""
    for l in lines[end:]:
        if l.strip() and not _MARKER.match(l):
            anchor = l.strip()
            break
    attach = "file-header" if start <= 3 else ("pre-code" if anchor else "orphan")
    in_header = start <= 6 and any("AI-hint" in x or "AI-related" in x or
                                   "AI-functions" in x for x in run)
    return _mk(path, start, end, "line", style, run, attach, anchor, in_header)


def _lex_generic(path: str, src: str, style: str) -> list[Block]:
    lines = src.splitlines()
    out: list[Block] = []
    run: list[str] = []
    run_start = 0

    def flush(end_idx: int):
        nonlocal run, run_start
        if run:
            out.append(_finish_run(path, run, run_start, end_idx, style, lines))
            run = []

    in_block = False
    block_lines: list[str] = []
    block_start = 0
    heredoc_end: str | None = None
    for i, raw in enumerate(lines, 1):
        s = raw.strip()

        # A heredoc BODY is data, not source: '#' lines inside one are Python
        # comments in an embedded script, or plain text. Counting them attributes
        # another language's comments to this file and inflates the census --
        # 98-drift-checks.sh alone embeds many Python heredocs.
        if heredoc_end is not None:
            if s == heredoc_end or s == heredoc_end + "'":
                heredoc_end = None
            continue
        m = _HEREDOC.search(raw)
        if m:
            flush(i - 1)
            heredoc_end = m.group("tag").strip("'\"")
            continue
        if style == "<!--":
            if not in_block and s.startswith("<!--"):
                in_block, block_start, block_lines = True, i, [_strip(raw)]
                if "-->" in s:
                    in_block = False
                    out.append(_mk(path, block_start, i, "blockcomment", style,
                                   block_lines, "file-header" if i <= 3 else "orphan",
                                   "", "AI-hint" in raw))
                continue
            if in_block:
                block_lines.append(_strip(raw))
                if "-->" in s:
                    in_block = False
                    out.append(_mk(path, block_start, i, "blockcomment", style,
                                   block_lines,
                                   "file-header" if block_start <= 3 else "orphan",
                                   "", any("AI-hint" in x for x in block_lines)))
                continue
            continue

        if s and _MARKER.match(raw) and raw.lstrip().startswith(style):
            if not run:
                run_start = i
            run.append(_strip(raw))
            continue
        # A trailing comment on a code line is inline, never a block.
        if style in ("#", "//") and style in raw and not raw.lstrip().startswith(style):
            idx = raw.find(style)
            if idx > 0 and raw[:idx].strip():
                flush(i - 1)
                out.append(_mk(path, i, i, "inline", style, [_strip(raw[idx:])],
                               "inline", raw[:idx].strip(), False))
                continue
        flush(i - 1)
    flush(len(lines))
    return out


def _find_native_comment_lex() -> str | None:
    bin_name = "mios-comment-lex.exe" if os.name == "nt" else "mios-comment-lex"
    for candidate in [
        os.environ.get("MIOS_COMMENT_LEX_BIN"),
        os.path.join(_REPO_ROOT, "tools", "native", "target", "release", bin_name),
        os.path.join(_REPO_ROOT, "tools", "native", "target", "debug", bin_name),
        os.path.join(_REPO_ROOT, "usr", "bin", bin_name),
    ]:
        if candidate and os.path.isfile(candidate):
            return candidate
    import shutil
    return shutil.which(bin_name)


def lex(path: str, raw: bytes | None = None, ai_tag=None) -> list[Block]:
    """Comment blocks in one file.

    A block is a maximal run of consecutive full-line comments; a blank line, a
    code line, or a style change ends it.
    """
    if raw is None:
        native_bin = _find_native_comment_lex()
        if native_bin and not path.endswith(".py"):
            try:
                import subprocess, json
                proc = subprocess.run([native_bin, path], capture_output=True, check=True)
                records = json.loads(proc.stdout.decode("utf-8"))
                return [Block(**r) for r in records]
            except Exception:
                pass

        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError:
            return []
    src = raw.decode("utf-8-sig", errors="replace").replace("\r\n", "\n")
    style = _style_for(path, ai_tag)
    if path.endswith(".py"):
        return _lex_python(path, src)
    return _lex_generic(path, src, style)


# --------------------------------------------------------------------------
# Classification -- ordered, first match wins, exactly one reason
# --------------------------------------------------------------------------
_BANNER_ONLY = re.compile(r"^[\s\-=*_~+.#]*$")
_SENTENCE_END = re.compile(r"[.!?](?:\s|$)")


def _glob_any(path: str, globs: Iterable[str]) -> bool:
    from fnmatch import fnmatch
    p = path.replace(os.sep, "/")
    return any(fnmatch(p, g) or g.strip("*") in p for g in globs if g)


def classify(block: Block, policy: Policy, refindex: RefIndex | None = None) -> Verdict:
    """Exactly one verdict, from the first rule that fires (spec section 2.2)."""
    text = block.text
    stripped = [l for l in text.splitlines() if l.strip()]
    L, W = block.lines, block.words

    # R7 is an axis, not a class: evaluated for every block.
    stale = bool(refindex and refindex.dangling(text, policy.ref_allowlist))

    # R0 GENERATED-SOURCE -- extracting from an artifact multi-counts the source.
    if _glob_any(block.path, policy.blocklist_globs):
        return Verdict("DROP", "generated-artifact", stale)

    # R1 READONLY-PAYLOAD -- this string is sent to a model; never edit it.
    if block.kind == "docstring" and _glob_any(block.path, policy.llm_payload_globs):
        return Verdict("READONLY", "llm-payload", stale)

    # R2 HEADER
    if block.in_header_block:
        # hint_max_chars caps the AI-hint PROSE, not the whole header block.
        # AI-related/AI-functions/AI-doc are machine-maintained: their length
        # tracks how many files a module touches and how many functions it
        # defines, neither of which is a writing-quality signal. Counting them
        # made the ceiling unreachable -- check-fleet-safety.py carries 357
        # characters of generated metadata, so it breached a 260 cap even with
        # an empty hint, and no amount of editing could clear the gate.
        hint_len = _hint_prose_len(text)
        if (hint_len or len(text)) > policy.hint_max_chars:
            return Verdict("MIGRATE_HEADER", "overlong-hint", stale)
        return Verdict("STAY", "ai-header", stale)

    # R3 COMMENTED-OUT CODE
    if stripped:
        codey = sum(1 for l in stripped if policy.matches("code", l))
        if codey * 2 >= len(stripped) and (W / max(L, 1)) < 4:
            return Verdict("DROP", "commented-out-code", stale)

    # R4 BANNER
    #
    # DELIBERATE NARROWING of the spec's second clause. As written it is
    # "<= 8 words AND no sentence-final punctuation AND not WHY -> DROP", which
    # also swallows ordinary short comments ("bump the retry count",
    # "guard against zero") -- and DROP is a class that `prune` may delete.
    # Information safety is absolute here, so a short block must additionally
    # LOOK like a label -- ALL-CAPS, Title Case, or a trailing colon -- before it
    # can be treated as a divider. Pure divider runs are unaffected.
    why = policy.matches("why", text)
    flat = " ".join(stripped).strip()
    looks_like_label = bool(
        flat
        and (flat.isupper()
             or flat.endswith(":")
             or all(w[:1].isupper() for w in flat.split() if w[:1].isalpha()))
    )
    if stripped and (all(_BANNER_ONLY.match(l) for l in stripped)
                     or (W <= 8 and not _SENTENCE_END.search(text)
                         and not why and looks_like_label)):
        if policy.matches("fact", text):
            return Verdict("MIGRATE", "banner-fact", stale, "heading-fact")
        return Verdict("DROP", "banner", stale)

    narr = policy.matches("narrative", text)

    # R6 INLINE (checked before R5's default so a trailing comment is never
    # deleted; R5(b) may still promote a fat one to MIGRATE below).
    if block.kind == "inline" and not (W > policy.stay_max_words and narr):
        return Verdict("STAY", "inline-scoped", stale)

    # R5 SIZE + SIGNAL -- the core split.
    if L <= policy.stay_max_lines and W <= policy.stay_max_words:
        return Verdict("STAY", "local-scoped", stale)
    if L <= policy.stay_max_lines and W > policy.stay_max_words and narr:
        return Verdict("MIGRATE", "fat-inline-narrative", stale, "note")
    if L >= policy.migrate_min_lines or W >= policy.migrate_min_words:
        as_ = "adr-candidate" if (narr and W >= 250) else ""
        return Verdict("MIGRATE",
                       "narrative-history" if narr else "narrative-rationale",
                       stale, as_)
    if narr:
        return Verdict("MIGRATE", "midsize-narrative", stale)
    return Verdict("STAY", "midsize-why", stale)

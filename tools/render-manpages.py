#!/usr/bin/env python3
# AI-hint: Renders the native roff manual tree from the SSOT, so the operating system manual reader answers about MiOS on the machine.
# AI-related: usr/share/mios/mios.toml, tools/sync-generated.sh
import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

MAN = "usr/share/man"
DOT = "."
TICK = chr(39)


def roff(text) -> str:
    """Make arbitrary prose safe inside a roff document."""
    out = []
    for line in str(text).split(chr(10)):
        line = line.replace(chr(92), r"\e")
        if line[:1] in (DOT, TICK):
            line = r"\&" + line
        line = re.sub(r"(?<![\\w])-(?=\w)", r"\-", line)
        out.append(line)
    return chr(10).join(out)


def th(name, section, version, title) -> str:
    return '.TH %s %s "" "MiOS %s" "%s"' % (
        roff(name.upper()), section, roff(version), roff(title)) + chr(10)


def version_of(root) -> str:
    try:
        raw = open(os.path.join(root, "VERSION"), encoding="utf-8").read()
        return "".join(raw.split()).lstrip("v") or "0.0.0"
    except OSError:
        return "0.0.0"


def prose(path, limit=14):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return []
    paras, buf = [], []
    for line in text.split(chr(10)):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("<!--"):
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        buf.append(s)
    if buf:
        paras.append(" ".join(buf))
    return paras[:limit]
DASH = chr(92) + "-"


def pages(root, ssot):
    v = version_of(root)
    verbs = ssot.get("verbs") or {}
    names = sorted(verbs)
    nl = chr(10)
    out = {}

    idx = [th("mios", "1", v, "MiOS Manual"),
           ".SH NAME" + nl + "mios " + DASH + " the MiOS verb dispatcher" + nl,
           ".SH SYNOPSIS" + nl + ".B mios" + nl + ".I verb" + nl,
           ".SH DESCRIPTION" + nl,
           "MiOS exposes its capabilities as verbs. Every verb below is declared"
           + nl + "in the single source of truth and has its own page: run"
           + nl + ".B man mios" + DASH + "verb" + nl + "for any of them." + nl,
           ".SH VERBS" + nl]
    for n in names:
        d = str((verbs[n] or {}).get("description") or "").strip()
        idx.append(".TP" + nl + ".B " + roff(n) + nl
                   + roff(d or "(no description)") + nl)
    idx.append(".SH FILES" + nl + ".TP" + nl + ".I /usr/share/mios/mios.toml" + nl
               + "The single source of truth." + nl
               + ".TP" + nl + ".I /usr/share/doc/mios/manual/" + nl
               + "The distilled prose manual." + nl)
    idx.append(".SH SEE ALSO" + nl + ".BR mios.toml (5)," + nl + ".BR mios (7)" + nl)
    out[MAN + "/man1/mios.1"] = "".join(idx)

    for n in names:
        spec = verbs[n] or {}
        d = str(spec.get("description") or "").strip() or "A MiOS verb."
        body = [th("mios-" + n, "1", v, "MiOS Verbs"),
                ".SH NAME" + nl + "mios" + DASH + roff(n) + " " + DASH + " "
                + roff(d.rstrip(DOT)) + nl,
                ".SH SYNOPSIS" + nl + ".B mios " + roff(n) + nl,
                ".SH DESCRIPTION" + nl + roff(d) + nl]
        surface = str(spec.get("surface") or "").strip()
        if surface:
            body.append(".SH SURFACE" + nl + "This verb runs on the" + nl
                        + ".B " + roff(surface) + nl + "surface." + nl)
        body.append(".SH FILES" + nl + ".TP" + nl
                    + ".I /usr/share/mios/mios.toml" + nl
                    + "Declares this verb and the description shown above." + nl)
        body.append(".SH SEE ALSO" + nl + ".BR mios (1)," + nl
                    + ".BR mios.toml (5)," + nl + ".BR mios (7)" + nl)
        out[MAN + "/man1/mios-" + n + ".1"] = "".join(body)

    cfg = [th("mios.toml", "5", v, "MiOS Configuration"),
           ".SH NAME" + nl + "mios.toml " + DASH + " the MiOS single source of truth" + nl,
           ".SH DESCRIPTION" + nl,
           "Every MiOS surface is projected from this file: units, ports, themes,"
           + nl + "container definitions, verbs and the installers. Editing a"
           + nl + "projection by hand is undone by the next build; edit the table"
           + nl + "here instead." + nl,
           ".SH SECTIONS" + nl]
    for key in sorted(ssot):
        val = ssot[key]
        if isinstance(val, dict):
            kind = "table with %d key(s)" % len(val)
        elif isinstance(val, list):
            kind = "array of %d entry(ies)" % len(val)
        else:
            kind = "scalar"
        cfg.append(".TP" + nl + ".B [" + roff(key) + "]" + nl + roff(kind) + nl)
    cfg.append(".SH FILES" + nl + ".TP" + nl + ".I /usr/share/mios/mios.toml" + nl
               + "The vendor copy that ships in the image." + nl
               + ".TP" + nl + ".I /etc/mios/mios.toml" + nl
               + "Host overrides, layered over the vendor copy." + nl)
    cfg.append(".SH SEE ALSO" + nl + ".BR mios (1)," + nl + ".BR mios (7)" + nl)
    out[MAN + "/man5/mios.toml.5"] = "".join(cfg)

    con = [th("mios", "7", v, "MiOS Concepts"),
           ".SH NAME" + nl + "mios " + DASH + " what MiOS is and how its pieces relate" + nl,
           ".SH DESCRIPTION" + nl]
    ps = prose(os.path.join(root, "usr/share/doc/mios/manual",
                            "ch01-introduction-and-core-concepts.md"))
    if not ps:
        ps = ["The distilled manual is installed under /usr/share/doc/mios/manual/."]
    for p in ps:
        con.append(".PP" + nl + roff(p) + nl)
    con.append(".SH FILES" + nl + ".TP" + nl + ".I /usr/share/doc/mios/manual/" + nl
               + "The full distilled manual." + nl)
    con.append(".SH SEE ALSO" + nl + ".BR mios (1)," + nl + ".BR mios.toml (5)" + nl)
    out[MAN + "/man7/mios.7"] = "".join(con)

    var = ssot.get("variants") or {}
    entries = var.get("entries") or {}
    if entries:
        vp = [th("mios-variants", "7", v, "MiOS Variants"),
              ".SH NAME" + nl + "mios" + DASH + "variants " + DASH
              + " the MiOS product line" + nl,
              ".SH DESCRIPTION" + nl,
              "Every variant below is one entry in the single source of truth."
              + nl + "The status is measured, not aspirational: shipping means"
              + nl + "built, published and observed; partial means the machinery"
              + nl + "runs but does not yet do the whole job; design means"
              + nl + "specified with no artifact yet." + nl,
              ".SH VARIANTS" + nl]
        for k in sorted(entries):
            e = entries[k] or {}
            vp.append(".TP" + nl + ".B " + roff(str(e.get("title", k)))
                      + " (" + roff(str(e.get("status", "?"))) + ")" + nl
                      + roff(str(e.get("summary", ""))) + nl
                      + ".br" + nl + "Runs on: " + roff(str(e.get("target", "?")))
                      + "." + nl)
        naming = var.get("naming") or {}
        if naming:
            vp.append(".SH NAMING" + nl
                      + "Titles read " + roff(str(naming.get("title_pattern", "")))
                      + " and keys read " + roff(str(naming.get("key_pattern", "")))
                      + ": the same name in two registers." + nl
                      + "A suffix names the job, not the size." + nl)
        vp.append(".SH SEE ALSO" + nl + ".BR mios (1)," + nl
                  + ".BR mios.toml (5)," + nl + ".BR mios (7)" + nl)
        out[MAN + "/man7/mios-variants.7"] = "".join(vp)
    return out


def validate_man_page(full_path: str) -> tuple[bool, str]:
    """Validate that a rendered roff man page is structurally valid and readable by man/groff if available."""
    import shutil, subprocess
    try:
        with open(full_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError as err:
        return False, f"cannot read {full_path}: {err}"

    if not content.startswith(".TH "):
        return False, f"{full_path} missing .TH header"
    if ".SH NAME" not in content or (".SH SYNOPSIS" not in content and ".SH DESCRIPTION" not in content):
        return False, f"{full_path} missing required .SH NAME / SYNOPSIS / DESCRIPTION section"

    man_bin = shutil.which("man")
    if man_bin:
        try:
            res = subprocess.run([man_bin, "-l", full_path], capture_output=True, text=True)
            if res.returncode != 0:
                return False, f"man -l {full_path} exited {res.returncode}: {res.stderr}"
            if not res.stdout.strip():
                return False, f"man -l {full_path} produced empty output"
        except Exception:
            pass

    groff_bin = shutil.which("groff")
    if groff_bin:
        try:
            res = subprocess.run([groff_bin, "-mandoc", "-Tutf8", full_path], capture_output=True, text=True)
            if res.returncode != 0:
                return False, f"groff -mandoc {full_path} exited {res.returncode}"
            if not res.stdout.strip():
                return False, f"groff -mandoc {full_path} produced empty output"
        except Exception:
            pass

    return True, "OK"


def main(argv) -> int:
    root = (os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT")
            or os.getcwd())
    check = "--check" in argv
    validate = "--validate" in argv
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        ssot = tomllib.load(fh)
    rendered = pages(root, ssot)

    drift = []
    for rel, body in sorted(rendered.items()):
        full = os.path.join(root, rel)
        try:
            current = open(full, encoding="utf-8").read()
        except OSError:
            current = None
        if current == body:
            continue
        if check:
            drift.append(rel if current is not None else rel + " (missing)")
            continue
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline=chr(10)) as fh:
            fh.write(body)

    orphans = []
    for base, _dirs, files in os.walk(os.path.join(root, MAN)):
        for fn in files:
            rel = os.path.relpath(os.path.join(base, fn), root).replace(os.sep, "/")
            if rel not in rendered:
                orphans.append(rel)

    if check and (drift or orphans):
        print("man pages out of sync with the SSOT -- run tools/render-manpages.py:")
        for d in drift[:10]:
            print("  " + d)
        for o in orphans[:5]:
            print("  " + o + " (no verb declares it)")
        return 1
    for o in orphans:
        os.remove(os.path.join(root, o))

    if validate:
        sample_pages = [os.path.join(root, MAN, "man1", "mios.1"),
                        os.path.join(root, MAN, "man7", "mios-variants.7"),
                        os.path.join(root, MAN, "man5", "mios.toml.5")]
        valid_errors = []
        for sp in sample_pages:
            if os.path.exists(sp):
                ok, msg = validate_man_page(sp)
                if not ok:
                    valid_errors.append(msg)
        if valid_errors:
            print("man page validation failed:")
            for ve in valid_errors:
                print("  " + ve)
            return 1

    print("[render-manpages] %d page(s) %s" %
          (len(rendered), "verified" if check else "rendered"), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

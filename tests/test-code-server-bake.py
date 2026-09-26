# AI-hint: Hermetic two-sided tests for the code-server workbench bake (mios-vscode-custom-css patch/verify), the dev-image wiring that runs it, and the mios-agents image and builders that bake it.
# AI-related: /usr/libexec/mios/mios-vscode-custom-css, /.devcontainer/Containerfile, /.devcontainer/setup-devcontainer.sh, /.devcontainer/post-start.sh, /usr/share/mios/agents/Containerfile, /usr/libexec/mios/mios-agents-firstboot.sh, /src/mios-rs/miosd/src/main.rs
# AI-functions: TestCodeServerBake, TestDevImageWiring, TestAgentsContainerfile, TestBuilders

import hashlib
import importlib.machinery
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOL = os.path.join(ROOT, "usr/libexec/mios/mios-vscode-custom-css")
CSS = os.path.join(ROOT, "usr/share/mios/themes/code-server-terminal.css")
CF = os.path.join(ROOT, "usr/share/mios/agents/Containerfile")
FIRSTBOOT = os.path.join(ROOT, "usr/libexec/mios/mios-agents-firstboot.sh")
MAIN_RS = os.path.join(ROOT, "src/mios-rs/miosd/src/main.rs")
TOML = os.path.join(ROOT, "usr/share/mios/mios.toml")
WB = "/usr/lib/code-server/lib/vscode/out/vs/code/browser/workbench/workbench.html"
IMG_TOOL = "/usr/libexec/mios/mios-vscode-custom-css"
IMG_CSS = "/usr/share/mios/themes/code-server-terminal.css"
ARGS = {"MIOS_CODE_SERVER_VERSION": ("image.sidecars", "code_server"),
        "CODE_SERVER_SCROLLBAR_PX": ("theme.edge", "code_server_scrollbar_px"),
        "CODE_SERVER_PERIMETER_PX": ("theme.edge", "code_server_perimeter_px")}

# Measured once each in code-server 4.139.1 lib/vscode/out/vs/code/browser/workbench/workbench.js.
JS_SCROLLBAR = 'get scrollbarWidth(){return this._configurationService.getValue("workbench.experimental.modernUI")===!0?10:14}'
JS_PERIMETER = ("var L0e=4,fGn=0,vGn=4,Wre=0;function Hre(s){return s.isModernUICompact()?fGn:L0e}"
                "function P0e(s){return s.isModernUICompact()?vGn:L0e}")
HTML = ('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8" />\n<link rel="stylesheet" href="{{WORKBENCH_WEB_BASE_URL}}'
        '/out/vs/code/browser/workbench/workbench.css">\n</head>\n<body aria-label="">\n</body>\n</html>\n')
START = "<!-- !! VSCODE-CUSTOM-CSS-START !! -->"


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _load_tool():
    loader = importlib.machinery.SourceFileLoader("mios_vscode_custom_css", TOOL)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class TestCodeServerBake(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.html = os.path.join(self.tmp, "workbench.html")
        self.js = os.path.join(self.tmp, "workbench.js")
        self.css = os.path.join(self.tmp, "code-server-terminal.css")
        with open(self.html, "w") as f:
            f.write(HTML)
        with open(self.js, "w") as f:
            f.write("var a=1;" + JS_PERIMETER + ";class X{" + JS_SCROLLBAR + "}")
        shutil.copyfile(CSS, self.css)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_tool(self, *args, env=None):
        return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True, env=env)

    def bake(self, cmd="patch", sb="0", pm="0"):
        return self.run_tool(cmd, "--target", self.html, "--css", self.css, "--scrollbar-px", sb, "--perimeter-px", pm)

    def test_patch_then_verify(self):
        r = self.bake()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        js = _read(self.js)
        self.assertIn("===!0?0:14}", js)
        self.assertIn("vGn=0,Wre=0", js)
        html = _read(self.html)
        self.assertEqual(html.count(START), 1)
        self.assertIn(_read(CSS), html)
        self.assertIn("--modern-ui-floating-card-outer-margin:0px", html)
        self.assertNotIn("file://", html)
        r = self.bake("verify")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_value_is_the_flag_not_a_literal(self):
        self.assertEqual(self.bake(sb="3", pm="2").returncode, 0)
        js = _read(self.js)
        self.assertIn("===!0?3:14}", js)
        self.assertIn("vGn=2,Wre=0", js)
        self.assertEqual(self.bake("verify", sb="3", pm="2").returncode, 0)

    def test_rebake_is_idempotent_and_replaces_block(self):
        self.assertEqual(self.bake().returncode, 0)
        before = (_sha(self.html), _sha(self.js))
        self.assertEqual(self.bake().returncode, 0)
        self.assertEqual((_sha(self.html), _sha(self.js)), before)
        with open(self.css, "a") as f:
            f.write("\n/* changed */\n")
        self.assertEqual(self.bake().returncode, 0)
        html = _read(self.html)
        self.assertEqual(html.count(START), 1)
        self.assertIn("/* changed */", html)
        self.assertEqual(self.bake("verify").returncode, 0)

    def test_verify_catches_edited_block(self):
        self.assertEqual(self.bake().returncode, 0)
        html = _read(self.html)
        planted = re.sub(r"padding-left:[^;]*;", "padding-left: 20px;", html, count=1)
        self.assertNotEqual(planted, html)
        with open(self.html, "w") as f:
            f.write(planted)
        r = self.bake("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("code-server workbench.html: injected block differs", r.stdout + r.stderr)

    def test_verify_catches_wrong_values(self):
        self.assertEqual(self.bake().returncode, 0)
        r = self.bake("verify", sb="5", pm="7")
        self.assertEqual(r.returncode, 1)
        out = r.stdout + r.stderr
        self.assertIn("code-server workbench.js: scrollbarWidth ModernUI=0 want 5", out)
        self.assertIn("code-server workbench.js: COMPACT_FLOATING_PANEL_OUTER_MARGIN=0 want 7", out)

    def test_verify_unbaked_tree_fails(self):
        r = self.bake("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("scrollbarWidth ModernUI=10 want 0", r.stdout + r.stderr)

    def _assert_anchor_failure(self, needle):
        before = (_sha(self.html), _sha(self.js))
        r = self.bake()
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 2, out)
        self.assertIn("anchor not found", out)
        self.assertIn(needle, out)
        self.assertEqual((_sha(self.html), _sha(self.js)), before, "a failed bake wrote a file")

    def test_real_anchor_must_be_found(self):
        # The fixture carries the real 4.139.1 anchor; a tool whose anchor drifted must fail, not return 0.
        r = self.bake()
        out = r.stdout + r.stderr
        if r.returncode != 0:
            self.fail(f"patch of the measured 4.139.1 anchor exited {r.returncode}: {out.strip()}")

    def test_moved_scrollbar_anchor_fails_loud(self):
        with open(self.js, "w") as f:
            f.write(JS_PERIMETER + JS_SCROLLBAR.replace("?10:14", "?10:15"))
        self._assert_anchor_failure("get scrollbarWidth")

    def test_duplicate_scrollbar_anchor_fails_loud(self):
        with open(self.js, "a") as f:
            f.write(JS_SCROLLBAR)
        self._assert_anchor_failure("get scrollbarWidth")

    def test_moved_perimeter_anchor_fails_loud(self):
        with open(self.js, "w") as f:
            f.write(JS_PERIMETER.replace("vGn=4", "vGn=6") + JS_SCROLLBAR)
        self._assert_anchor_failure("COMPACT_FLOATING_PANEL_OUTER_MARGIN")

    def test_missing_js_fails_loud(self):
        os.unlink(self.js)
        r = self.bake()
        self.assertEqual(r.returncode, 2)
        self.assertIn("anchor not found", r.stdout + r.stderr)

    def test_head_anchor_must_be_unique(self):
        for body in (HTML.replace("</head>", ""), HTML.replace("</head>", "</head></head>")):
            with open(self.html, "w") as f:
                f.write(body)
            self._assert_anchor_failure(": </head>")

    def test_empty_target_list_exits_2(self):
        mod = _load_tool()
        mod.locate_workbench_html_files = lambda: []
        argv = sys.argv
        sys.argv = ["mios-vscode-custom-css", "patch", "--scrollbar-px", "0", "--perimeter-px", "0"]
        try:
            self.assertEqual(mod.main(), 2)
        finally:
            sys.argv = argv

    def test_defaults_resolve_from_theme_edge(self):
        toml = os.path.join(self.tmp, "mios.toml")
        with open(toml, "w") as f:
            f.write("[theme.edge]\ncode_server_scrollbar_px = 4\ncode_server_perimeter_px = 1\n")
        env = dict(os.environ, MIOS_VENDOR_TOML=toml, MIOS_HOST_TOML=os.path.join(self.tmp, "none-host.toml"),
                   MIOS_USER_TOML=os.path.join(self.tmp, "none-user.toml"),
                   MIOS_VENDOR_TOML_D=os.path.join(self.tmp, "none.d"))
        r = self.run_tool("patch", "--target", self.html, "--css", self.css, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("===!0?4:14}", _read(self.js))
        self.assertIn("vGn=1,", _read(self.js))

    def test_unpatch_restores_upstream(self):
        before = (_sha(self.html), _sha(self.js))
        self.assertEqual(self.bake().returncode, 0)
        r = self.run_tool("unpatch", "--target", self.html)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((_sha(self.html), _sha(self.js)), before)

    def test_retired_fallbacks_are_gone(self):
        src = _read(TOOL)
        for gone in ("ALT_CSS_FILE", "patch_xterm_css", 'href="file://'):
            self.assertNotIn(gone, src)
        self.assertFalse(os.path.exists(os.path.join(ROOT, "usr/share/mios/theme/code-server-terminal.css")))


class TestDevImageWiring(unittest.TestCase):

    def test_containerfile_bakes_pinned_release(self):
        cf = _read(os.path.join(ROOT, ".devcontainer/Containerfile"))
        runs = [r for r in re.split(r"\n(?=[A-Z]+ )", cf) if r.startswith("RUN") and ".rpm" in r]
        self.assertEqual(len(runs), 1, "exactly one RUN installs and bakes code-server")
        run = runs[0]
        self.assertIn("set -euo pipefail", run)
        self.assertNotIn("|| true", run)
        for key in ("image.sidecars code_server", "theme.edge code_server_scrollbar_px", "theme.edge code_server_perimeter_px"):
            self.assertIn(key, run)
        self.assertRegex(run, r"code-server-\$\{v\}-\$\{arch\}\.rpm")
        self.assertRegex(run, r"\bpatch\b[\s\S]*\bverify\b")
        for f in ("usr/libexec/mios/mios-vscode-custom-css", "usr/libexec/mios/mios-toml-get",
                  "usr/lib/mios/mios_toml.py", "usr/share/mios/themes/code-server-terminal.css"):
            self.assertIn(f, cf)
        self.assertIsNone(re.search(r"code-server[-:]v?\d+\.\d+\.\d+", cf), "a version literal in the Containerfile")

    def test_setup_verify_is_fatal_and_install_is_reported(self):
        sh = _read(os.path.join(ROOT, ".devcontainer/setup-devcontainer.sh"))
        verify = [ln for ln in sh.splitlines() if '"$VSCODE_CSS_TOOL" verify' in ln]
        self.assertEqual(len(verify), 1)
        self.assertNotIn("||", verify[0])
        self.assertNotIn("install --all || true", sh)
        self.assertIn("custom-css extension install failed (exit", sh)

    def test_post_start_binds_loopback_from_ports(self):
        sh = _read(os.path.join(ROOT, ".devcontainer/post-start.sh"))
        self.assertIn("ports code_server", sh)
        self.assertIn("127.0.0.1", sh)
        self.assertIsNone(re.search(r"\b8900\b|\b8080\b", sh), "a code-server port literal in post-start.sh")


def containerfile_violations(text):
    """Every way the agents Containerfile fails to pin code-server or to bake and verify both patches."""
    errs = []
    lines = [ln.strip() for ln in text.replace("\\\n", " ").splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    froms = [i for i, ln in enumerate(lines) if ln.startswith("FROM ")]
    cs = [i for i in froms if "ghcr.io/coder/code-server" in lines[i]]
    if not cs:
        errs.append("agents/Containerfile: no FROM ghcr.io/coder/code-server")
    for i in cs:
        if lines[i] != "FROM ghcr.io/coder/code-server:${MIOS_CODE_SERVER_VERSION}":
            errs.append(f"agents/Containerfile: {lines[i]} (unpinned)")
        if "ARG MIOS_CODE_SERVER_VERSION" not in lines[:i]:
            errs.append("agents/Containerfile: ARG MIOS_CODE_SERVER_VERSION (no default) must precede the FROM")
    for ln in lines:
        if re.match(r"ARG (MIOS_CODE_SERVER_VERSION|CODE_SERVER_\w+_PX)=", ln):
            errs.append(f"agents/Containerfile: {ln} (a default bypasses the layered loader)")
    after = lines[cs[0] + 1:] if cs else lines
    for a in ("CODE_SERVER_SCROLLBAR_PX", "CODE_SERVER_PERIMETER_PX"):
        if f"ARG {a}" not in after:
            errs.append(f"agents/Containerfile: ARG {a} missing after FROM")
    for src in (IMG_TOOL, IMG_CSS):
        if not any(re.fullmatch(rf"COPY --from=mios {re.escape(src)} \S+", ln) for ln in lines):
            errs.append(f"agents/Containerfile: COPY --from=mios {src} missing")
    runs = " ".join(ln for ln in lines if ln.startswith("RUN "))
    if f"wb={WB}" not in runs or 'test -f "$wb"' not in runs:
        errs.append(f"agents/Containerfile: test -f {WB} missing")
    for flag, arg in (("--scrollbar-px", "CODE_SERVER_SCROLLBAR_PX"), ("--perimeter-px", "CODE_SERVER_PERIMETER_PX")):
        if not re.search(rf'{flag} "\$\{{{arg}:\?\}}"', runs):
            errs.append(f"agents/Containerfile: {flag} not fed by a required ${{{arg}}}")
    for verb in ("patch", "verify"):
        if not re.search(rf'python3 {re.escape(IMG_TOOL)} {verb} "\$@"', runs):
            errs.append(f"agents/Containerfile: {IMG_TOOL} {verb} not run")
    return errs


def builder_violations(name, text):
    """A builder that does not pass every build arg from its mios-toml-get read, or the mios build-context."""
    errs = []
    for arg, (section, key) in ARGS.items():
        if arg not in text:
            errs.append(f"{name}: --build-arg {arg} missing")
        if not re.search(rf'{re.escape(section)}"?\)?[ ,]+"?{re.escape(key)}\b', text):
            errs.append(f"{name}: no mios-toml-get read of [{section}].{key}")
    if "mios=/" not in text or "--build-context" not in text:
        errs.append(f"{name}: --build-context mios=/ missing")
    if IMG_CSS not in text:
        errs.append(f"{name}: rebuild trigger ignores {IMG_CSS}")
    return errs


class TestAgentsContainerfile(unittest.TestCase):

    def test_repo_containerfile_is_clean(self):
        self.assertEqual(containerfile_violations(_read(CF)), [])

    def test_latest_is_named(self):
        text = re.sub(r"(?m)^FROM ghcr\.io/coder/code-server:.*$", "FROM ghcr.io/coder/code-server:latest", _read(CF))
        self.assertIn("agents/Containerfile: FROM ghcr.io/coder/code-server:latest (unpinned)", containerfile_violations(text))

    def test_missing_verify_is_named(self):
        text = _read(CF).replace(f'{IMG_TOOL} verify "$@"', "true")
        self.assertIn(f"agents/Containerfile: {IMG_TOOL} verify not run", containerfile_violations(text))

    def test_defaulted_arg_is_named(self):
        text = _read(CF).replace("ARG CODE_SERVER_PERIMETER_PX\n", "ARG CODE_SERVER_PERIMETER_PX=4\n")
        self.assertTrue(any("CODE_SERVER_PERIMETER_PX=4" in e for e in containerfile_violations(text)))


class TestBuilders(unittest.TestCase):

    def test_both_builders_clean(self):
        self.assertEqual(builder_violations("mios-agents-firstboot.sh", _read(FIRSTBOOT)), [])
        self.assertEqual(builder_violations("miosd main.rs", _read(MAIN_RS)), [])

    def test_dropped_arg_is_named(self):
        text = _read(MAIN_RS).replace("CODE_SERVER_PERIMETER_PX=", "X=")
        self.assertIn("miosd main.rs: --build-arg CODE_SERVER_PERIMETER_PX missing", builder_violations("miosd main.rs", text))

    def _resolve(self, values):
        """Run firstboot's resolve_build_args against a stub mios-toml-get that serves `values`."""
        body = re.search(r"(?ms)^resolve_build_args\(\) \{.*?^\}", _read(FIRSTBOOT)).group(0)
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "mios-toml-get")
            with open(stub, "w") as f:
                f.write("#!/bin/sh\ncase \"$1 $2\" in\n")
                for (section, key), v in values.items():
                    f.write(f"  '{section} {key}') printf '%s\\n' '{v}' ;;\n")
                f.write("esac\n")
            os.chmod(stub, os.stat(stub).st_mode | stat.S_IXUSR)
            script = (f'set -euo pipefail\nTOML_GET={stub}\nlog() {{ echo "$*" >&2; }}\n{body}\n'
                      'resolve_build_args\nprintf "%s\\n" "${BUILD_ARGS[@]}"\n')
            return subprocess.run(["bash", "-c", script], capture_output=True, text=True)

    def test_firstboot_resolves_ssot_values(self):
        with open(TOML, "rb") as f:
            data = tomllib.load(f)
        img = data["image"]["sidecars"]["code_server"]
        edge = data["theme"]["edge"]
        vals = {("image.sidecars", "code_server"): img,
                ("theme.edge", "code_server_scrollbar_px"): edge["code_server_scrollbar_px"],
                ("theme.edge", "code_server_perimeter_px"): edge["code_server_perimeter_px"]}
        r = self._resolve(vals)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split("\n")[:-1], [
            "--build-arg", f"MIOS_CODE_SERVER_VERSION={img.rsplit(':', 1)[1]}",
            "--build-arg", f"CODE_SERVER_SCROLLBAR_PX={edge['code_server_scrollbar_px']}",
            "--build-arg", f"CODE_SERVER_PERIMETER_PX={edge['code_server_perimeter_px']}",
            "--build-context", "mios=/"])

    def test_firstboot_refuses_unpinned(self):
        for img in ("ghcr.io/coder/code-server:latest", "ghcr.io/coder/code-server", "localhost:5000/code-server"):
            r = self._resolve({("image.sidecars", "code_server"): img,
                               ("theme.edge", "code_server_scrollbar_px"): 0,
                               ("theme.edge", "code_server_perimeter_px"): 0})
            self.assertNotEqual(r.returncode, 0, img)
            self.assertIn(f"'{img}' has no pinned tag", r.stderr)


def main():
    """Unit tests, then the repo agents Containerfile as a gate: exit 1 naming each violation."""
    ok = unittest.main(exit=False, argv=[sys.argv[0]]).result.wasSuccessful()
    for e in containerfile_violations(_read(CF)):
        print(f"VIOLATION: {e}", file=sys.stderr)
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

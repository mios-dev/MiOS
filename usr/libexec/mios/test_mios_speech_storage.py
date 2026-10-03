#!/usr/bin/env python3
# AI-hint: Two-sided controls for T-1140 -- the speech engines' model storage is persistent /var declared in tmpfiles, mounted from the SSOT model_dir, and asserted before start.
# AI-related: usr/share/mios/mios.toml, usr/lib/tmpfiles.d/mios-speech.conf, usr/share/containers/systemd/mios-whisper.container, usr/share/containers/systemd/mios-piper.container
# AI-functions: speech_engines, check_engine, TestSpeechStorage
"""T-1140: mios-whisper bind-mounted /usr/share/mios/whisper/models, a path
nothing created, so podman's statfs failed and the unit looped on Restart=.

For every [services.<engine>] carrying model_dir/model, the shipped tree must
hold:

* usr/lib/tmpfiles.d declares model_dir (Law 2), owned by the engine's uid/gid,
  and model_dir lives under /var -- never mutable state under /usr;
* the rendered Quadlet mounts exactly model_dir at /models, read-only;
* its Exec= loads /models/<model>;
* its [Unit] orders after systemd-tmpfiles-setup.service and asserts
  model_dir/model exists, so a missing model fails the unit by name.

Each negative control plants one defect in a scratch copy and requires the
same check to name it.
"""
from __future__ import annotations

import glob
import os
import shutil
import tempfile
import tomllib
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
_TOML = os.path.join("usr", "share", "mios", "mios.toml")
_TMPFILES = os.path.join("usr", "lib", "tmpfiles.d")
_QUADLETS = os.path.join("usr", "share", "containers", "systemd")


def speech_engines(root: str) -> dict[str, dict]:
    with open(os.path.join(root, _TOML), "rb") as f:
        services = tomllib.load(f).get("services", {})
    return {name: spec for name, spec in services.items()
            if isinstance(spec, dict) and "model_dir" in spec}


def _tmpfiles(root: str) -> dict[str, tuple[str, str]]:
    owners: dict[str, tuple[str, str]] = {}
    for conf in sorted(glob.glob(os.path.join(root, _TMPFILES, "*.conf"))):
        with open(conf, encoding="utf-8") as f:
            for line in f:
                fields = line.split()
                if len(fields) >= 5 and fields[0] in ("d", "D", "v", "q", "Q"):
                    owners[fields[1].rstrip("/")] = (fields[3], fields[4])
    return owners


def _quadlet(root: str, engine: str) -> dict[str, dict[str, list[str]]]:
    sections: dict[str, dict[str, list[str]]] = {}
    cur: dict[str, list[str]] | None = None
    with open(os.path.join(root, _QUADLETS, f"mios-{engine}.container"), encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                cur = sections.setdefault(s[1:-1], {})
            elif cur is not None and "=" in s and not s.startswith("#"):
                k, v = s.split("=", 1)
                cur.setdefault(k, []).append(v)
    return sections


def check_engine(root: str, engine: str, spec: dict) -> list[str]:
    errors: list[str] = []
    model_dir, model = spec["model_dir"].rstrip("/"), spec["model"]
    unit = f"mios-{engine}.container"
    if not model_dir.startswith("/var/"):
        errors.append(f"[services.{engine}].model_dir {model_dir} is not /var storage")
    owner = _tmpfiles(root).get(model_dir)
    if owner is None:
        errors.append(f"tmpfiles.d declares no {model_dir}")
    elif owner[0] not in (spec.get("user"), str(spec.get("uid"))):
        errors.append(f"tmpfiles.d owns {model_dir} as {owner[0]}, not {spec.get('user')}")
    q = _quadlet(root, engine)
    vols = [v.split(":") for v in q.get("Container", {}).get("Volume", [])]
    mounts = [v for v in vols if len(v) >= 2 and v[1] == "/models"]
    if not mounts:
        errors.append(f"{unit} mounts nothing at /models")
    for v in mounts:
        if v[0].rstrip("/") != model_dir:
            errors.append(f"{unit} mounts {v[0]} at /models, not model_dir {model_dir}")
        if len(v) < 3 or "ro" not in v[2].split(","):
            errors.append(f"{unit} mounts /models read-write")
    if not any(f"/models/{model}" in e for e in q.get("Container", {}).get("Exec", [])):
        errors.append(f"{unit} Exec= does not load /models/{model}")
    unit_sec = q.get("Unit", {})
    if f"{model_dir}/{model}" not in unit_sec.get("AssertPathExists", []):
        errors.append(f"{unit} does not AssertPathExists={model_dir}/{model}")
    if "systemd-tmpfiles-setup.service" not in " ".join(unit_sec.get("After", [])).split():
        errors.append(f"{unit} is not ordered After=systemd-tmpfiles-setup.service")
    return errors


class TestSpeechStorage(unittest.TestCase):
    def setUp(self) -> None:
        self.engines = speech_engines(_ROOT)
        self.scratch = tempfile.mkdtemp(prefix="t1140_")
        for rel in (_TMPFILES, _QUADLETS):
            shutil.copytree(os.path.join(_ROOT, rel), os.path.join(self.scratch, rel))
        os.makedirs(os.path.join(self.scratch, os.path.dirname(_TOML)))
        shutil.copy2(os.path.join(_ROOT, _TOML), os.path.join(self.scratch, _TOML))

    def tearDown(self) -> None:
        shutil.rmtree(self.scratch, ignore_errors=True)

    def _plant(self, rel: str, old: str, new: str) -> None:
        path = os.path.join(self.scratch, rel)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn(old, text, f"plant anchor missing from {rel}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new))

    def test_host_store_engines(self) -> None:
        # whisper loads the model baked into its bound image, so only piper
        # carries a host model_dir.
        self.assertEqual(sorted(self.engines), ["piper"])

    def test_whisper_loads_its_in_image_model(self) -> None:
        q = _quadlet(_ROOT, "whisper")
        self.assertFalse([v for v in q.get("Container", {}).get("Volume", []) if ":/models" in v],
                         "mios-whisper must not bind a host /models")
        self.assertIn("--model /app/models/", " ".join(q.get("Container", {}).get("Exec", [])))

    def test_positive_shipped_tree(self) -> None:
        for engine, spec in self.engines.items():
            self.assertEqual(check_engine(_ROOT, engine, spec), [], engine)

    def test_negative_pre_fix_usr_mount(self) -> None:
        """The pre-fix shape: a /usr bind source nothing creates."""
        self._plant(os.path.join(_QUADLETS, "mios-piper.container"),
                    "Volume=/var/lib/mios/piper/models:", "Volume=/usr/share/mios/piper/models:")
        errs = check_engine(self.scratch, "piper", self.engines["piper"])
        self.assertIn("mios-piper.container mounts /usr/share/mios/piper/models at /models, "
                      "not model_dir /var/lib/mios/piper/models", errs)

    def test_negative_storage_undeclared(self) -> None:
        self._plant(os.path.join(_TMPFILES, "mios-speech.conf"),
                    "d /var/lib/mios/piper/models ", "# d /var/lib/mios/piper/models ")
        self.assertIn("tmpfiles.d declares no /var/lib/mios/piper/models",
                      check_engine(self.scratch, "piper", self.engines["piper"]))

    def test_negative_no_prerequisite_assert(self) -> None:
        self._plant(os.path.join(_QUADLETS, "mios-piper.container"),
                    "AssertPathExists=", "ConditionPathExists=")
        self.assertIn("mios-piper.container does not AssertPathExists="
                      "/var/lib/mios/piper/models/en_US-lessac-medium.onnx",
                      check_engine(self.scratch, "piper", self.engines["piper"]))

    def test_negative_model_drift(self) -> None:
        spec = dict(self.engines["piper"], model="en_US-other.onnx")
        errs = check_engine(_ROOT, "piper", spec)
        self.assertIn("mios-piper.container Exec= does not load /models/en_US-other.onnx", errs)
        self.assertIn("mios-piper.container does not AssertPathExists="
                      "/var/lib/mios/piper/models/en_US-other.onnx", errs)


if __name__ == "__main__":
    unittest.main()

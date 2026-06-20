# AI-hint: Standalone unit test for tools/provision-agent-mtls (#54 mTLS PKI): the agent leaf cert is signed by the CA, carries clientAuth+serverAuth EKU, and re-runs reuse the CA (peer trust survives). Skips cleanly if cryptography is absent.
# AI-related: tools/provision-agent-mtls.py
# AI-functions: _skip, _load_tool, t_chain, t_eku, t_ca_reuse, main
"""Standalone unit test for the #54 mTLS provisioning tool.

Provisions into a temp dir and verifies the PKI is correct: the agent leaf is
signed by the CA, it is valid for BOTH client + server auth, and re-running keeps
the existing CA (so exchanged peer trust is not invalidated). Needs cryptography;
SKIPS (exit 0) if it is unavailable so the drift-gate stays portable.

Run:  python test_mios_mtls.py
"""

import importlib.machinery
import importlib.util
import os
import sys
import tempfile

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _skip(msg: str) -> None:
    print(f"[SKIP] {msg}")
    print("\nskipped (0 checks)")
    sys.exit(0)


try:
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID
except ModuleNotFoundError:
    _skip("cryptography not installed")


def _load_tool():
    p = os.environ.get("MIOS_MTLS_TOOL")
    if not p:
        here = os.path.dirname(os.path.abspath(__file__))
        repo = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
        p = os.path.join(repo, "tools", "provision-agent-mtls.py")
    if not os.path.isfile(p):
        _skip(f"provision-agent-mtls.py not found at {p}")
    loader = importlib.machinery.SourceFileLoader("provmtls", p)
    spec = importlib.util.spec_from_loader("provmtls", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def _provision(tool, d):
    os.environ["MIOS_MTLS_DIR"] = d
    os.environ["MIOS_MTLS_CN"] = "test-agent"
    os.environ["MIOS_TOML"] = os.path.join(d, "no-such.toml")  # force defaults
    cfg = tool._cfg()
    ca_cert, ca_key, minted = tool.ensure_ca(cfg)
    tool.issue_agent_cert(cfg, ca_cert, ca_key)
    return cfg, minted


def main() -> int:
    tool = _load_tool()
    with tempfile.TemporaryDirectory() as d:
        cfg, minted = _provision(tool, d)
        _check("ca: minted on first run", minted is True)
        ca = x509.load_pem_x509_certificate(open(cfg["ca_cert"], "rb").read())
        agent = x509.load_pem_x509_certificate(open(cfg["cert"], "rb").read())

        # chain: agent issued by the CA + signature verifies under the CA key
        _check("chain: issuer == CA subject", agent.issuer == ca.subject)
        try:
            ca.public_key().verify(
                agent.signature, agent.tbs_certificate_bytes,
                ec.ECDSA(agent.signature_hash_algorithm))
            sig_ok = True
        except Exception:  # noqa: BLE001
            sig_ok = False
        _check("chain: agent signature verifies under CA", sig_ok)

        # CA is a CA; agent is not
        _check("ca: BasicConstraints CA=true",
               ca.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is True)
        _check("agent: BasicConstraints CA=false",
               agent.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is False)

        # EKU: client AND server auth (mutual)
        eku = agent.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        _check("agent: EKU clientAuth", ExtendedKeyUsageOID.CLIENT_AUTH in eku)
        _check("agent: EKU serverAuth", ExtendedKeyUsageOID.SERVER_AUTH in eku)
        _check("agent: CN carried", any(
            a.value == "test-agent" for a in agent.subject))

        # key file is private-mode (best-effort; POSIX only)
        if os.name == "posix":
            mode = os.stat(cfg["key"]).st_mode & 0o777
            _check("agent: key file mode 0600", mode == 0o600, oct(mode))

        # idempotent: re-run reuses the SAME CA (peer trust preserved)
        ca_serial_before = ca.serial_number
        _, minted2 = _provision(tool, d)
        ca2 = x509.load_pem_x509_certificate(open(cfg["ca_cert"], "rb").read())
        _check("ca: reused on re-run (not minted)", minted2 is False)
        _check("ca: serial stable across re-runs",
               ca2.serial_number == ca_serial_before)

    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

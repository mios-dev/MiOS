#!/usr/bin/env python3
# AI-hint: Provision the MiOS agent mTLS PKI (#54 zero-trust federation): self-signed CA + agent cert/key.
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_provision_agent_mtls_py.md
from __future__ import annotations

import datetime
import os
import socket
import sys


def _load_toml(path: str) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore
        except ModuleNotFoundError:
            return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except OSError:
        return {}


def _cfg() -> dict:
    root = os.environ.get("MIOS_ROOT") or os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))
    toml = os.environ.get("MIOS_TOML") or os.path.join(root, "usr/share/mios/mios.toml")
    sect = ((_load_toml(toml).get("security") or {}).get("mtls")) or {}
    d = os.environ.get("MIOS_MTLS_DIR") or str(sect.get("dir") or "/etc/mios/mtls")
    cn = (os.environ.get("MIOS_MTLS_CN") or str(sect.get("common_name") or "")
          or socket.gethostname() or "mios-agent")
    return {
        "dir": d,
        "ca_cert": str(sect.get("ca_file") or os.path.join(d, "ca.crt")),
        "ca_key": os.path.join(d, "ca.key"),
        "cert": str(sect.get("cert_file") or os.path.join(d, "agent.crt")),
        "key": str(sect.get("key_file") or os.path.join(d, "agent.key")),
        "cn": cn,
        "days": int(sect.get("validity_days") or 825),
    }


def _write(path: str, data: bytes, mode: int) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    os.chmod(path, mode)


def ensure_ca(cfg: dict):
    """Load the CA if present (preserve peer trust across runs), else mint one."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    if os.path.exists(cfg["ca_cert"]) and os.path.exists(cfg["ca_key"]):
        ca_cert = x509.load_pem_x509_certificate(open(cfg["ca_cert"], "rb").read())
        ca_key = serialization.load_pem_private_key(open(cfg["ca_key"], "rb").read(), None)
        return ca_cert, ca_key, False
    ca_key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "MiOS Agent CA")])
    now = datetime.datetime.now(datetime.timezone.utc)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True, key_cert_sign=True, crl_sign=True,
            key_encipherment=False, content_commitment=False, data_encipherment=False,
            key_agreement=False, encipher_only=False, decipher_only=False), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    _write(cfg["ca_cert"], ca_cert.public_bytes(serialization.Encoding.PEM), 0o644)
    _write(cfg["ca_key"], ca_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()), 0o600)
    return ca_cert, ca_key, True


def issue_agent_cert(cfg: dict, ca_cert, ca_key) -> None:
    """Mint an agent leaf cert (clientAuth + serverAuth) signed by the CA."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cfg["cn"])])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=cfg["days"]))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(cfg["cn"])]), critical=False)
        .add_extension(x509.ExtendedKeyUsage(
            [ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    _write(cfg["cert"], cert.public_bytes(serialization.Encoding.PEM), 0o644)
    _write(cfg["key"], key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()), 0o600)


def main() -> int:
    try:
        import cryptography  # noqa: F401
    except ModuleNotFoundError:
        sys.stderr.write("[mtls] python3 'cryptography' is required -- "
                         "install it where the agent runs, then re-run.\n")
        return 2
    cfg = _cfg()
    ca_cert, ca_key, minted = ensure_ca(cfg)
    issue_agent_cert(cfg, ca_cert, ca_key)
    print(f"[mtls] CA {'minted' if minted else 'reused'}: {cfg['ca_cert']}")
    print(f"[mtls] agent cert (CN={cfg['cn']}, {cfg['days']}d): {cfg['cert']}")
    print("[mtls] share ca.crt with peers; configure the reverse proxy to require "
          "client certs (see usr/share/mios/security/README.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

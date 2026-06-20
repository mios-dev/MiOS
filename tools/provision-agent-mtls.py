#!/usr/bin/env python3
# AI-hint: Provision the MiOS agent mTLS PKI (#54 zero-trust federation): self-signed CA + agent cert/key.
# AI-related: usr/share/mios/security, usr/share/mios/mios.toml, mios_a2a_principal, tools/generate-egress-firewall.py
# AI-functions: _cfg, ensure_ca, issue_agent_cert, main
#   Operator-gated tool (like the fine-tune subsystem): generates a self-signed
#   local CA (the standard self-hosted default; override the paths in
#   [security.mtls] to use an org PKI) and an agent leaf cert/key valid for BOTH
#   client + server auth, so A2A peers can mutually authenticate. Writes PEMs to
#   [security.mtls].dir (default /etc/mios/mtls), NOT committed (secrets, per-host,
#   time-stamped). mTLS itself is terminated at the reverse proxy (MiOS's TLS
#   pattern) using these certs -- this tool only mints the PKI.
"""Provision the MiOS agent mTLS keypair + CA (#54).

Zero-trust federation needs peers to mutually authenticate. The ed25519 *message*
principal (#60) signs delegations; mTLS authenticates the *transport*. This mints
the PKI for that: a self-signed local CA + an agent leaf certificate (clientAuth +
serverAuth) signed by it. Peers trust each other by exchanging CA certs.

Trust model: self-signed local CA per node is the standard self-hosted default
(point [security.mtls] at an existing org CA to override). The enforcing half --
making the A2A endpoint REQUIRE client certs -- is reverse-proxy deployment
(MiOS terminates TLS at the proxy), documented in security/README.md; this tool
only provisions the credentials.

Idempotent: an existing CA is reused (so peer trust survives re-runs); the agent
leaf is re-issued. Requires `cryptography`. Run where the certs should live.
"""
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

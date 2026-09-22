# Local secret boundary

This directory is intentionally tracked only through this README. Its
contents are ignored and must remain local.

It represents the local boundary for encrypted operator input consumed by
`mios-bootstrap.git`; it is not a fourth MiOS repository and must not become a
nested Git checkout committed into `mios.git`.

## Expected encrypted repository shape

```text
operator-secret-input/
├── README.md
├── .sops.yaml
├── recipients/
│   └── operators.txt
├── encrypted/
│   ├── common.env.sops
│   ├── linux.env.sops
│   ├── windows.env.sops
│   └── hosts/
└── rotation/
    └── README.md
```

Only encrypted payloads, public recipient identifiers, and non-sensitive
rotation metadata belong in that repository. Age identity files, KMS
credentials, plaintext `.env` files, decrypted archives, and logs remain
outside Git.

Do not commit credentials, tokens, private keys, password hashes, or exported
environment files here. Use `[REDACTED]` or
`<REPLACEMENT_CREDENTIAL>` in research and examples. Runtime secrets belong
in the repository-approved secret manager or protected
`/etc/mios/secrets.env` with the required permissions.

An empty `.secrets/` directory is not an authentication mechanism. Local
loopback is not a sufficient multi-user security boundary.

## AGY from Blink Shell and GitHub Codespaces

Use separate trust paths for transport and application authentication:

- Blink Shell may authenticate the SSH connection with an iOS Keychain/Secure
  Enclave-backed key. Prefer a dedicated, least-privilege key and Blink's
  integrated SSH agent; never export the private key into the Codespace.
- GitHub Codespaces may inject a narrowly scoped, revocable application
  credential as a Codespaces secret at runtime. Do not place that value in
  `devcontainer.json`, a Dockerfile `ENV`, an image layer, `/workspaces`, a
  shell startup file, logs, command arguments, or this directory.
- An interactive OAuth login should be completed in the trusted Codespace
  terminal over the Blink connection. Do not assume SSH agent forwarding can
  transport an arbitrary bearer token, and do not store OAuth cookies or
  credential caches in the repository.

Codespaces secrets are still readable by trusted processes in the Codespace.
Treat the repository, devcontainer lifecycle scripts, extensions, and
dependencies as trusted code before granting access. Rotate or revoke the
credential after testing, and diagnose authentication by checking names and
metadata only, never by printing values.

The MiOS contract is therefore: repository metadata may name a stable
`secret_ref`, Blink supplies SSH transport authentication, and the runtime
secret source supplies the AGY application credential. Plaintext values remain
outside Git and outside generated artifacts.

The supported AGY API-key setup is deliberately non-secret:

1. Configure `modelProvider = "gemini"` in the user's AGY settings.
2. Inject `GEMINI_API_KEY` only at runtime through the Codespaces secret
   mechanism or an equivalent protected runtime source.
3. Run `.devcontainer/configure-agy-runtime.sh`; it preserves other AGY
   settings, writes mode `0600`, and reports only whether the variable is
   present.
4. Launch AGY after the runtime variable is available. The API key is not
   an OpenAI-provider credential and does not change the MiOS
   `MIOS_AI_ENDPOINT` contract.

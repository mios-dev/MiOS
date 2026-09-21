# Local secret boundary

This directory is intentionally tracked only through this README. Its
contents are ignored and must remain local.

It represents the local boundary for a separate private repository such as
`mios-dev/mios-secrets`; it is not that repository itself and must not become
a nested Git checkout committed into `mios.git`.

## Expected encrypted repository shape

```text
mios-secrets/
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

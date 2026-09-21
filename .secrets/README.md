# Local secret boundary

This directory is intentionally tracked only through this README. Its
contents are ignored and must remain local.

Do not commit credentials, tokens, private keys, password hashes, or exported
environment files here. Use `[REDACTED]` or
`<REPLACEMENT_CREDENTIAL>` in research and examples. Runtime secrets belong
in the repository-approved secret manager or protected
`/etc/mios/secrets.env` with the required permissions.

An empty `.secrets/` directory is not an authentication mechanism. Local
loopback is not a sufficient multi-user security boundary.

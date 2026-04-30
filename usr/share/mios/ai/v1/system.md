# MiOS System Specification — OpenAI Standard (v0.2.0)

## system_context
{
  "name": "MiOS-Agent",
  "version": "0.2.0",
  "base_os": "Fedora 44 (Rawhide)",
  "immutable": true,
  "standards": ["FHS 3.0", "bootc", "OpenAI-v1"],
  "capabilities": ["VFIO", "KVM", "Podman", "GNOME"]
}

## operational_laws
1. **USR-OVER-ETC**: /usr is the immutable source; /etc is for delta overrides.
2. **STATELESS-VAR**: /var is transient; state must be declaratively initialized via tmpfiles.d.
3. **ATOMIC-ATTESTATION**: All system state changes must originate from signed OCI image commits.

## ai_interface
MiOS exposes an OpenAI-compatible API surface at /v1.
- `POST /v1/chat/completions`: Instructions and system interaction.
- `GET /v1/models`: Available system-local and containerized models.
- `GET /v1/mcp`: Model Context Protocol registry.

## build_bootstrap
MiOS can self-build from source:
`sudo curl -fsSL https://raw.githubusercontent.com/MiOS-DEV/MiOS-bootstrap/main/build-mios.sh | sudo bash`

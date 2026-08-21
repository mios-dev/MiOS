<!-- AI-hint: Chapter 48: Local AI Web Consoles. Covers Open WebUI Quadlet parameters and local mapping. Details interface layout settings and custom models aliases. Explains console access security using token authentication. -->

# Chapter 48: Local AI Web Consoles

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Local AI Web Consoles** under MiOS.

### <a name="48_open_webui_deployment"></a>48.Open WebUI Deployment: Open WebUI Deployment

> Path Reference: `/usr/share/doc/mios/manual.md#48_open_webui_deployment`

#### Overview

Deploys Open WebUI as the primary browser chat interface.

## Details
- **Port**: Serves requests on port 3030.
- **Service**: Managed via `mios-owui` Quadlet.
- **Connection**: Connects internally to `/v1/chat/completions` on the local endpoint.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="48_interface_customization"></a>48.Interface Customization: Interface Customization

> Path Reference: `/usr/share/doc/mios/manual.md#48_interface_customization`

#### Overview

Customizes panels and options in the web interface.

## Settings
- **Customizations**: Configures defaults inside Open WebUI.
- **Tuning**: Integrates with local search tool paths.
- **Features**: Restricts outbound options.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="48_token_based_access_control"></a>48.Token-based Access Control: Token-based Access Control

> Path Reference: `/usr/share/doc/mios/manual.md#48_token_based_access_control`

#### Overview

Secures web access using credentials tokens.

## Details
- **Authentication**: secured via token strings.
- **Logs**: User connection actions are tracked.
- **Security**: Restricts local web console access.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

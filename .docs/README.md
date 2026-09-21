# Documentation staging

This is the root-level documentation control plane.

- Drafts and editorial plans live here.
- Durable project research is published under `docs/research/`.
- Image-shipped documentation is published under `usr/share/doc/mios/`.
- Architecture decisions are authored under `usr/share/doc/mios/adr/`, with
  `ADR.md` as the generated root index.

Do not use `.docs/` to bypass the FHS ownership model or create a second copy
of the `mios.toml` SSOT.

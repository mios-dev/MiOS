<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Powershell script to pull the MiOS OCI image from GHCR and use bootc-image-builder (BIB) via Podman to generate multi-format deployment artifacts (qcow2, raw, vhdx, wsl, iso) for various hypervisors and hardware.
AI-related: mios-dev, mios-cloud-build, mios-cloud-export
AI-functions: Write-Step, Write-Ok, Write-Warn, Write-Bad, ConvertTo-WslPath, Resolve-OutputBase, Invoke-Podman, Invoke-PodmanCapture, Invoke-BibTarget, Invoke-WslExport, Invoke-VhdxConvert
Requires -Version 7.0

<!-- mios-src:12db086a4734 from mios-cloud-build.ps1:1-4 -->


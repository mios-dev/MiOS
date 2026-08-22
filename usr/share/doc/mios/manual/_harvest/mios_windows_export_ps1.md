<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: A Windows-native OCI image exporter that extracts rootfs layers directly from GHCR to create .tar.zst files for WSL or converts existing disk images to .vhdx via qemu-img.exe without requiring Podman or WSL.
AI-related: mios-cloud-build, mios-dev, mios-windows-export, mios-hyperv-create
AI-functions: Write-Step, Write-Ok, Write-Warn, Write-Bad, Test-CommandExists, Install-WingetTool, Get-GhcrToken, Resolve-ImageRef, Get-ImageManifest, Save-ImageLayers, Merge-LayersToTar, Compress-WithZstd
Requires -Version 7.0

<!-- mios-src:ce7451ca6234 from mios-windows-export.ps1:1-4 -->


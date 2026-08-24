# AI-hint: Generate k3s/k8s manifests from live MiOS Podman containers (pods-as-SSOT)
# AI-related: usr/share/mios/k3s, usr/share/containers/systemd, usr/share/mios/mios.toml

[CmdletBinding()]
param (
    [string]$Root = $env:MIOS_ROOT,
    [string]$OutDir = $env:MIOS_K3S_OUT,
    [string]$NameFilter = '^mios-'
)

if (-not $Root) {
    $Root = Split-Path -Parent $PSScriptRoot
}
if (-not $OutDir) {
    $OutDir = Join-Path $Root 'usr\share\mios\k3s\generated'
}

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

Write-Host "🔍 [generate-k3s] Output directory: $OutDir"

# Generate k3s manifest for mios-node if container exists or template
$nodeYaml = Join-Path $OutDir "mios-node.yaml"
$nodeManifestContent = @"
# AI-hint: GENERATED k3s/k8s manifest for the MiOS mios-node pod (pods-as-SSOT).
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: mios-node
  name: mios-node
spec:
  containers:
  - name: mios-node
    image: ghcr.io/mios-dev/mios-node:latest
    env:
    - name: MIOS_NODE_ID
      value: "101"
    - name: MIOS_PORT
      value: "8650"
    ports:
    - containerPort: 8650
      protocol: UDP
    - containerPort: 8650
      protocol: TCP
    volumeMounts:
    - mountPath: /var/lib/mios
      name: mios-state-vol
  volumes:
  - name: mios-state-vol
    hostPath:
      path: /var/lib/mios
"@

Set-Content -Path $nodeYaml -Value $nodeManifestContent -Encoding UTF8
Write-Host "✅ [generate-k3s]   Wrote $nodeYaml"

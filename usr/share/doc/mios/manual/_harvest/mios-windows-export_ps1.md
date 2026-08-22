<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Resolve image ref into (registry, repo, ref). Only ghcr.io...

Resolve image ref into (registry, repo, ref). Only ghcr.io is supported
directly; other registries fall through to a clear error so the operator
knows to use mios-cloud-build.ps1 + a podman pull instead.

<!-- mios-src:ff25edc44f14 from mios-windows-export.ps1:137-139 -->

### The scaffold needs admin (Hyper-V cmdlets gate on...

The scaffold needs admin (Hyper-V cmdlets gate on RunAsAdmin), so we
generate it for the operator to review + launch elevated themselves
rather than auto-elevating from here. Operators get to see the New-VM
parameters before committing.

<!-- mios-src:de9e7196d03d from mios-windows-export.ps1:348-351 -->

### Anonymous bearer for the public-read pull. Even private...

Anonymous bearer for the public-read pull. Even private repos that the
operator has access to via gh auth would work if you swap this for a
PAT-derived token -- left out of scope for the public-image use case.

<!-- mios-src:fd5d006cadcb from mios-windows-export.ps1:383-385 -->

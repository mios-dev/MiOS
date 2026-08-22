<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Suppresses the cloud-init final stage error in WSL2 environments by masking the cloud-final.service when the system is not running in a standard cloud/hypervisor environment.
AI-related: cloud-final.service
Skip cloud-init's final stage in WSL.

cloud-final.service runs `nc /run/cloud-init/share/final.sock` to
signal completion to a hypervisor / cloud platform. WSL2 isn't a
cloud platform; the socket is never created and the nc call fails
with `nc: /run/cloud-init/share/final.sock: No such file or directory`
at every boot, surfacing as the trailing error in the operator's
`wsl -d MiOS` console output. Matches the existing skip pattern for
cloud-init-local / cloud-init-network / cloud-config in the same
directory neighbors.

<!-- mios-src:9d95610db5c7 from usr/lib/systemd/system/cloud-final.service.d/10-mios-wsl2.conf:1-12 -->


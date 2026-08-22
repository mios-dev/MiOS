<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines system user accounts and group memberships for Podman Machine compatibility, specifically pinning the 'core' user to UID 1001 to ensure valid logind session creation and resource access.
Podman Machine Compatibility
Login-shell user -- pin UID to >= UID_MIN so logind creates /run/user/<uid>/.
'g core 1001' must come BEFORE 'u core' so sysusers can resolve the GID;
see 10-mios.conf header for the canonical pattern + failure-mode rationale.

<!-- mios-src:4cf7b27163d3 from usr/lib/sysusers.d/20-podman-machine.conf:1-5 -->


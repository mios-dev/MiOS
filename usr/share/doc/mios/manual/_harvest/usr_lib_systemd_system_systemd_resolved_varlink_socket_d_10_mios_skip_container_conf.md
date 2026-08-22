<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Prevents systemd-resolved varlink socket activation churn in containerized environments by applying ConditionVirtualization=!container to avoid TriggerLimitBurst failures when the service is gated off.
AI-related: mios-skip-container, systemd-resolved-varlink.socket, resolved.service
/usr/lib/systemd/system/systemd-resolved-varlink.socket.d/10-mios-skip-container.conf

Skip the resolved varlink socket inside containers where resolved is
gated off. Same failure pattern as 10-mios-skip-container.conf for the
logind varlink socket: resolved.service has
ConditionVirtualization=!container, so its varlink socket activates
repeatedly to a service that gets skipped, hits TriggerLimitBurst, and
leaves a permanently-failed socket in the unit list. Adding the same
Condition* directives to the socket prevents the activation churn.

<!-- mios-src:722b5d9e9b4d from usr/lib/systemd/system/systemd-resolved-varlink.socket.d/10-mios-skip-container.conf:1-11 -->


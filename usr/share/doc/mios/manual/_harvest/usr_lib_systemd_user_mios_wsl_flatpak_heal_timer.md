<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Triggers the mios-wsl-flatpak-heal.service every 5 minutes to keep the flatpak-portal active and prevent it from entering an idle timeout state in WSL environments.
AI-related: /usr/libexec/mios/mios-wsl-flatpak-heal, mios-wsl-flatpak-heal, mios-wsl-flatpak-heal.service, graphical-session.target, timers.target
/usr/lib/systemd/user/mios-wsl-flatpak-heal.timer

Cadence: every 5 minutes. Tight enough that the heal fires
before flatpak-portal's typical idle timeout (~10 min) lets it
go dormant; loose enough that the heal itself doesn't churn
the portal stack.

Activated on graphical-session.target so headless WSL distros
(CI runners, etc.) don't try to keep portals warm they never
use.

<!-- mios-src:16542c5380ff from usr/lib/systemd/user/mios-wsl-flatpak-heal.timer:1-12 -->


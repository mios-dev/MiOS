<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Layout differs by upstream release. Newer tags nest the...

Layout differs by upstream release. Newer tags nest the sources under
policy/<distro>/; older ones -- which is what the vendored tarball is --
keep k3s.te FLAT at the archive root with no policy/ directory at all. The
old `find policy ...` had no fallback for that and, with `set -euo pipefail`,
a missing policy/ aborted the whole phase two seconds in with a bare exit 1 --
which is what the bake logged as "[WARN] 37-k3s-selinux".

<!-- mios-src:dcb7ebbac1a4 from automation/37-k3s-selinux.sh:49-54 -->

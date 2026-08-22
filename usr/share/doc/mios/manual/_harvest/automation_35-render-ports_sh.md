<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Ports are ALLOCATED from [ports.categories] (base +...

Ports are ALLOCATED from [ports.categories] (base + index*stride), not read
off the flat table -- and the allocation must honour the layered override
chain (vendor/OEM default < /etc operator < user). The shared resolver is the
only thing that does both, so prefer it; the awk fallback below can only see
the flat vendor projection and exists purely so a stripped build host without
python still produces SOMETHING rather than an empty install.env.

<!-- mios-src:d8ec2062e5d6 from automation/35-render-ports.sh:23-28 -->

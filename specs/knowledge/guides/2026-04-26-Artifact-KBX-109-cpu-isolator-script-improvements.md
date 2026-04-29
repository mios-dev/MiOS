<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-fss/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "knowledge"
  ],
  "relations": {
    "depends_on": [
      ".env.mios"
    ],
    "impacts": []
  }
}
```
> **Proprietor:** MiOS Project
> **Infrastructure:** Self-Building Infrastructure (Personal Property)
> **License:** Licensed as personal property to MiOS Project
> **Source Reference:** MiOS-Core-v0.1.4
---

# CPU Isolation Script Improvements
## Fixing systemd Affinity Application

### Problem Identified

The original script had a critical limitation: it would configure systemd CPUAffinity in `/etc/systemd/system.conf` but **would not apply the changes immediately**. This meant:

1. âœ— Commented `#CPUAffinity=` line wasn't being uncommented
2. âœ— systemd daemon wasn't being reloaded
3. âœ— Existing processes weren't moved to host cores
4. âœ— All host processes would pile up on a single core (typically core 31)

### Improvements Made

#### 1. Enhanced `configure_systemd_affinity()` Function

**Before:**
- Only appended `CPUAffinity=` if it didn't exist
- Didn't handle commented lines
- No immediate daemon reload
- No process migration

**After:**
```bash
# Handles three scenarios:
1. Uncommented line (CPUAffinity=...) â†’ Update value
2. Commented line (#CPUAffinity=) â†’ Uncomment and set value
3. Missing line â†’ Insert after [Manager] section

# Immediate actions:
- systemctl daemon-reexec (reload systemd)
- Move all processes to host cores
- Show success/failure counts
- Provide immediate feedback
```

#### 2. Improved `cpu-isolate` Helper Script

**New Features:**
- **Progress indicators** - Shows process count during migration
- **Success/failure counts** - Reports how many processes moved
- **Enhanced status command** - Shows comprehensive isolation state
- **Better error handling** - Gracefully handles kernel threads
- **Visual feedback** - Progress bar for large process counts

**Usage:**
```bash
# Enable isolation (move processes to host cores)
sudo cpu-isolate on

# Disable isolation (allow all cores)
sudo cpu-isolate off

# Check current status
cpu-isolate status
```

#### 3. Better User Feedback

The script now provides clear feedback at each step:
- âœ“ "Moved X processes to host cores (Y failed - expected for kernel threads)"
- âœ“ "systemd daemon reloaded"
- âœ“ "CPU affinity is now active - check with 'htop' to verify"

### What Happens Now

When you select **"Both (Maximum isolation)"** in the script:

1. **Kernel parameters** are added to bootloader (requires reboot)
2. **systemd affinity** is configured AND applied immediately:
   - `/etc/systemd/system.conf` is updated
   - `systemctl daemon-reexec` is run
   - All processes are moved to host cores
   - You see immediate results in `htop`

### Verification Steps

After running the improved script:

```bash
# 1. Check systemd affinity is set
grep CPUAffinity /etc/systemd/system.conf
# Should show: CPUAffinity=0 1 8 9 16 17 24 25 (uncommented)

# 2. Verify processes are using host cores
htop
# Press 't' for tree view
# Cores 0,1,8,9,16,17,24,25 should show activity
# Cores 2-7,10-15,18-23,26-31 should be mostly idle

# 3. Check affinity of a specific process
taskset -cp 1
# Should show: pid 1's current affinity list: 0,1,8,9,16,17,24,25

# 4. Use the helper script
cpu-isolate status
```

### Before vs After Comparison

| Aspect | Before (Old Script) | After (Improved Script) |
|--------|---------------------|-------------------------|
| systemd config | Appends line only | Handles commented/uncommented |
| Daemon reload | âŒ Not done | âœ“ Immediate reload |
| Process migration | âŒ Not done | âœ“ Moves all processes |
| User feedback | Generic message | Detailed counts & status |
| Immediate effect | âŒ Requires reboot | âœ“ Active immediately |
| Host core usage | All on core 31 | Spread across all host cores |

### Technical Details

#### How systemd CPUAffinity Works

When `CPUAffinity=` is set in `/etc/systemd/system.conf`:
1. systemd (PID 1) sets its own affinity to those cores
2. All child processes inherit this affinity by default
3. Kernel threads and processes that explicitly set affinity are unaffected

This is why we need to:
1. Set the affinity in the config file
2. Reload systemd (`daemon-reexec`)
3. Move existing processes manually (they don't inherit retroactively)

#### Why Some Processes "Fail"

You'll see messages like:
```
Moved 1847 processes to host cores (143 failed - expected for kernel threads)
```

The "failed" processes are typically:
- **Kernel threads** - Can't have their affinity changed from userspace
- **Already-terminated processes** - PIDs that ended between enumeration and migration
- **Protected processes** - System-critical processes with locked affinity

This is **normal and expected** - don't worry about these failures!

### Migration Path for Existing Systems

If you've already run the old script and have the "core 31 problem":

```bash
# Quick fix without re-running the script:
sudo nano /etc/systemd/system.conf
# Uncomment and set: CPUAffinity=0 1 8 9 16 17 24 25

sudo systemctl daemon-reexec

for pid in (ps -eo pid --no-headers)
    sudo taskset -cp 0,1,8,9,16,17,24,25 $pid 2>/dev/null
end

# Verify with htop
```

Or simply re-run the improved script - it will detect the existing configuration and update it correctly.

### Future Enhancements

Possible future improvements:
- [ ] Auto-detect if running in fish/zsh and adjust syntax
- [ ] Persist process affinity across reboots (via systemd unit overrides)
- [ ] GUI tool for real-time affinity visualization
- [ ] Integration with virt-manager for automatic VM core pinning
- [ ] Per-CCD performance monitoring integration

---

**Version**: 2026-01-15  
**Script Version**: Updated from universal-cpu-isolator.sh  
**Tested On**: MiOS with AMD Ryzen 9 9950X3D

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-fss/mios](https://github.com/mios-fss/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-fss/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-fss/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->

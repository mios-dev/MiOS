<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Wi-Fi 6E/7, 2.5GbE & VirtIO...

!/usr/bin/env python3
AI-hint: Wi-Fi 6E/7, 2.5GbE & VirtIO driver slipstream into WinPE boot.wim & install.wim
AI-related: tests/test-driver-slipstream.py, usr/share/mios/mios.toml, usr/libexec/mios/win/unattend_gen.py
AI-functions: DriverSlipstreamEngine, DriverPackage, DismCommandPlan, slipstream_drivers

<!-- mios-src:9fed304dc3ff from usr/libexec/mios/win/driver_slipstream.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Windows PowerShell...

!/usr/bin/env python3
AI-hint: Windows PowerShell RemoteSigned policy, Developer Mode registry & profile configurator
AI-related: tests/test-ps-policy-config.py, usr/share/mios/mios.toml, usr/libexec/mios/win/unattend_gen.py
AI-functions: PowerShellPolicyEngine, PolicyConfig, generate_reg_file, generate_ps1_script

<!-- mios-src:f461ad797a0c from usr/libexec/mios/win/ps_policy_config.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Windows 11 autounattend.xml...

!/usr/bin/env python3
AI-hint: Windows 11 autounattend.xml generator with debloat, developer mode & bypasses
AI-related: tests/test-unattend-gen.py, usr/share/mios/mios.toml, usr/libexec/mios/win/ps_policy_config.py
AI-functions: UnattendGenerator, UnattendPreset, generate_unattend_xml

<!-- mios-src:b9745aa15c1d from usr/libexec/mios/win/unattend_gen.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Automated validation of...

!/usr/bin/env python3
AI-hint: Automated validation of Windows unattend XML schema against official Microsoft XSD rules.
AI-related: tests/test-unattend-validate.py, usr/libexec/mios/win/unattend_gen.py, autounattend.xml
AI-functions: UnattendValidator, ValidationError, ValidationResult, ValidationSeverity, validate_unattend_xml, main

<!-- mios-src:e9e81ecfbb98 from usr/libexec/mios/win/unattend_validate.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Windows Terminal...

!/usr/bin/env python3
AI-hint: Windows Terminal settings.json profile injector with MiOS tabs & color palette
AI-related: tests/test-wt-profile-inject.py, usr/share/mios/mios.toml, usr/libexec/mios/win/unattend_gen.py
AI-functions: WindowsTerminalProfileInjector, ProfileConfig, ColorScheme, inject_wt_profiles

<!-- mios-src:67197f7ee483 from usr/libexec/mios/win/wt_profile_inject.py:1-4 -->

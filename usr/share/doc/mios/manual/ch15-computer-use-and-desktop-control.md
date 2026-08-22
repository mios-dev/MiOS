<!-- AI-hint: Chapter 15: Computer Use and Desktop Control. Details coordinate grounding on Wayland screens via vision models. Explains input emulation via the mios-pc-control command suite. Documents screen tree traversal for structural UI reasoning. -->

# Chapter 15: Computer Use and Desktop Control

> Part IV: Detailed Inference & Execution Layers of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Computer Use and Desktop Control** under MiOS.

### <a name="15_ui_tars_vision_grounding"></a>15.UI-TARS Vision Grounding: UI-TARS Vision Grounding

> Path Reference: `/usr/share/doc/mios/manual.md#15_ui_tars_vision_grounding`

#### Overview

Desktop automation uses UI-TARS models to translate visual displays into action coordinates.

## Operations
- **Screen Capture**: Grabs active Wayland framebuffer frames.
- **Grounding**: Processes frames to return clickable target coordinates.
- **Scaling**: Coordinates are scaled to match the physical resolution.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="15_wayland_input_automation"></a>15.Wayland Input Automation: Wayland Input Automation

> Path Reference: `/usr/share/doc/mios/manual.md#15_wayland_input_automation`

#### Overview

Inputs are emulated on Wayland through secure input modules.

## Flow
- **Utility**: Uses the `mios-pc-control` command suite.
- **Input Emulation**: Emulates mouse movement, click actions, and key events.
- **Containment**: Actions are confined to approved display boundaries.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="15_at_spi_accessibility_tuning"></a>15.AT-SPI Accessibility Tuning: AT-SPI Accessibility Tuning

> Path Reference: `/usr/share/doc/mios/manual.md#15_at_spi_accessibility_tuning`

#### Overview

AT-SPI screen trees allow agents to navigate UI hierarchies programmatically.

## Methods
- **Traversal**: Traverses active GUI trees to identify component properties.
- **Fallback**: Serves as a semantic fallback when visual coordinate grounding is blocked.
- **Speed**: Improves automation speed by returning direct text content without visual delays.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

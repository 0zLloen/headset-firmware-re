# Shared Platforms (`platforms/`)

A folder under `platforms/<oem-or-chip-vendor>-<family>/` holds bootloader specifications, USB/HID ISP protocols, and read-back/flashing tools that are shared across two or more headset models (for example, headsets built on the same Skyworks/Avnera, Realtek, Actions, C-Media, Airoha, BES, or Nordic wireless audio platform).

Until a second device in `devices/` is shown to share the same MCU/SoC and bootloader protocol, keep device-specific protocol notes and scripts inside `devices/<vendor>-<model>/`. See [`CONTRIBUTING.md`](../CONTRIBUTING.md#where-things-go) for the rules on moving material into `platforms/`.

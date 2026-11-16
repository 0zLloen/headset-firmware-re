# HyperX Cloud III Wireless — Firmware Notes

Status: Both the wired USB-C headset (`03f0:06b7`, `bcdDevice` `0x3109`, 150-byte HID-only descriptor) and the 2.4 GHz USB wireless receiver (`03f0:05b7`, `bcdDevice` `0x4109`, USB Audio Class 1.0 + 187-byte HID descriptor) are identified and verified on a retail unit (2026-11-16). Nothing has been written to the receiver or headset.

Findings use the labels defined in [`CONTRIBUTING.md`](../../CONTRIBUTING.md#evidence-rules). [`device.yaml`](device.yaml) holds the structured summary.

| File | What it covers |
| :--- | :--- |
| [`usb-and-hid.md`](usb-and-hid.md) | Verified USB device/configuration descriptors for both `03f0:05b7` (receiver) and `03f0:06b7` (wired headset), USB Audio Class 1.0 terminal tree and streaming formats, comparison of the 187-byte and 150-byte HID report descriptors (`0xFF13:0x0001`, Consumer `0x0C:0x01`, Telephony `0x0B:0x05`), and the inferred Report ID `0x66` telemetry protocol |
| [`hardware-and-fcc.md`](hardware-and-fcc.md) | FCC grant specifications for the headset (`B94-CL007`) and 2.4 GHz USB-C receiver (`B94-CL007WA`), physical controls (including the 3-second mute hold for sidetone), and open hardware questions |
| [`re-scripts/`](re-scripts/README.md) | Passive sysfs inspector and offline HID report descriptor decoder (`inspect_usb_hid.py`) with offline unit tests (`test_inspect.py`) covering both `03f0:05b7` (187 B) and `03f0:06b7` (150 B) |
| [`udev/`](udev/70-hyperx-cloud-iii-wireless.rules) | Non-root `hidraw` access (`TAG+="uaccess"`) for both `03f0:05b7` (receiver) and `03f0:06b7` (wired headset) |

## Open questions

Each with what would settle it:

- **Exact wireless audio SoC / MCU markings on the headset (`B94-CL007`) and receiver (`B94-CL007WA`)**: Both `03f0:06b7` and `03f0:05b7` expose the exact same Interrupt IN endpoint (`0x84`, `EP 4 IN`, 64 B, 4 ms), the same 16-zero `iSerial` placeholder, and byte-for-byte identical `0xFF13:0x0001` (73 B) and `0x000B:0x0005` (77 B) HID descriptor blocks (**Verified**, 2026-11-16), strongly indicating the same SoC family and USB/HID SDK on both boards (**Inferred**). Settle: inspect the FCC internal photos exhibits on `fccid.io` (`B94-CL007` and `B94-CL007WA`) or record the package markings from a non-destructive earcup/dongle inspection (Step 2).
- **Firmware container and update protocol in HyperX NGENUITY**: Because the headset over USB-C (`03f0:06b7`) is a single-interface HID device exposing the exact same `0xFF13:0x0001` vendor collection (Report IDs `0x06`, `0x07`, `0x0A`, `0x0B`, `0x66`) as the dongle (`03f0:05b7`), NGENUITY updates both devices over USB HID (or triggers a bootloader re-enumeration via `0xFF13:0x0001`). Settle: unpack the NGENUITY `.msixbundle`/`.appx` offline (Step 3), locate the bundled firmware binaries (`v3.1.0.9` for `03f0:06b7` and `v4.1.0.9` for `03f0:05b7`) and update DLLs, and record their filenames, versions, SHA-256 hashes, load addresses, and command opcodes.
- **Purpose of unmapped vendor HID reports `0x06` (61 B Out), `0x07` (61 B In), `0x0A` (61 B Out), and `0x0B` (2 B In) on `0xFF13:0x0001`**: Present on both `03f0:05b7` and `03f0:06b7`. Settle: passive `usbmon`/`USBPcap` capture of NGENUITY startup, sidetone toggle, EQ change, and version check (Step 4), cross-checked against decompiled NGENUITY libraries (Step 3).
- **Verification of Report ID `0x66` commands (`0x89` battery, `0x8A` charging state, sidetone, auto-shutoff timer) on hardware**: Documented in third-party open-source tools (`HyperHeadset`, `HaloBattery`, `NightfurY-Peripherals`), so currently labelled **Inferred** here. Settle: capture NGENUITY polling `03f0:05b7` and `03f0:06b7` over `usbmon` (Step 4) or run a read-only `0x66 0x89` / `0x66 0x8A` query once confirmed against a passive capture.

## Sources

- Retail unit: `03f0:05b7` receiver (`bcdDevice` `0x4109`) and `03f0:06b7` wired USB-C headset (`bcdDevice` `0x3109`), Linux `lsusb -v`, `/sys/bus/usb/devices/1-1`, `/sys/bus/usb/devices/1-3`, `/proc/asound/card1`, `/sys/class/hidraw/hidraw1/device/report_descriptor`, and `/sys/class/hidraw/hidraw7/device/report_descriptor`, 2026-11-16.
- FCC ID `B94-CL007` (headset, model `CL007`): <https://fccid.io/B94-CL007>
- FCC ID `B94-CL007WA` (2.4 GHz USB wireless dongle, model `CL007WA`): <https://fccid.io/B94-CL007WA>
- Third-party open-source protocol documentation: [LennardKittner/HyperHeadset](https://github.com/LennardKittner/HyperHeadset), [HeyOkay/HaloBattery](https://github.com/HeyOkay/HaloBattery), [Sapd/HeadsetControl](https://github.com/Sapd/HeadsetControl).

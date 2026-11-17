# HyperX Cloud III Wireless — Firmware Notes

Status: Both the wired USB-C headset (`03f0:06b7` / `03f0:0e9d`, `bcdDevice` `0x3109`, **Airoha AB1565** `AB1565_Headset` `v3.1.0.9`, 150-byte HID-only descriptor) and the 2.4 GHz USB wireless receiver (`03f0:05b7` / `03f0:0c9d`, `bcdDevice` `0x4109`, **Airoha AB1565** `AB1565_ULL2_DONGLE` `v4.1.0.9`, USB Audio Class 1.0 + 187-byte HID descriptor), along with all 13 read-only `0xFF13:0x0001` (`Report ID 0x66`) status queries (`0x81`..`0x8F` in both headset-on and headset-off states), the official FOTA firmware images (`03F005B7.bin`, `03F006B7.bin`, `03F00C9D.bin`, `03F00E9D.bin`), and the **Airoha RACE over USB HID** (`Report IDs 0x06 / 0x07 / 0x0A / 0x0B`) update protocol, are **Verified** (2026-11-16/17). Nothing has been written to flash on the receiver or headset.

Findings use the labels defined in [`CONTRIBUTING.md`](../../CONTRIBUTING.md#evidence-rules). [`device.yaml`](device.yaml) holds the structured summary.

| File | What it covers |
| :--- | :--- |
| [`usb-and-hid.md`](usb-and-hid.md) | Verified USB device/configuration descriptors for both `03f0:05b7` (receiver) and `03f0:06b7` (wired headset), USB Audio Class 1.0 terminal tree and streaming formats, comparison of the 187-byte and 150-byte HID report descriptors, and the **Verified** Report ID `0x66` (`0x81`..`0x8F`) status protocol (headset-on, charging, unplugged, and headset-off states) |
| [`firmware-updater.md`](firmware-updater.md) | **Verified** Airoha AB1565 FOTA package headers (`03F005B7.bin` / `03F00C9D.bin` `v4.1.0.9` and `03F006B7.bin` / `03F00E9D.bin` `v3.1.0.9`), SHA-256 digests, SPI NOR flash partition tables (`TLV 0x0012` / `0x0014`), and the Airoha RACE over USB HID (`Report IDs 0x06 / 0x07 / 0x0A / 0x0B`) updater protocol |
| [`hardware-and-fcc.md`](hardware-and-fcc.md) | Verified **Airoha AB1565** SoC (`AB1565_ULL2_DONGLE` and `AB1565_Headset`), FCC grant specifications for the headset (`B94-CL007`) and 2.4 GHz USB-C receiver (`B94-CL007WA`), physical controls, and flash capacities |
| [`re-scripts/`](re-scripts/README.md) | Passive sysfs inspector (`inspect_usb_hid.py`), read-only `0x66` status probe (`query_status.py`), passive event listener (`listen_events.py`), Airoha FOTA header parser (`inspect_fota_package.py`), and offline unit tests (`test_inspect.py`) |
| [`udev/`](udev/70-hyperx-cloud-iii-wireless.rules) | Non-root `hidraw` access (`TAG+="uaccess"`) for both `03f0:05b7` (receiver) and `03f0:06b7` (wired headset) |

## Open questions

Each with what would settle it:

- **AES key used for `TLV 0x00F0 = 0x01` FOTA payload stream (`0x1000..end`)**: While the 4 KB FOTA header (`0x0000..0x0FFF`), overall SHA-256 (`0x0000..0x001F`), and per-partition uncompressed sizes, target flash addresses (`TLV 0x0012`), and SHA-256 hashes (`TLV 0x0014`) are **Verified** in plaintext, the compressed LZMA stream starting at `0x1000` is encrypted (`TLV 0x00F0 = 0x01`) for on-chip decryption by the AB1565 FOTA mover. Settle: read out the external SPI NOR flash (`0x08000000`) directly via a clip or `RaceReadNV` / flash read command if needed.
- **Physical PCB test points (UART0 / 1-Wire RACE / SWD)**: Settle: inspect PCB test pads during a physical teardown.

## Sources

- Retail unit: `03f0:05b7` receiver (`bcdDevice` `0x4109`) and `03f0:06b7` wired USB-C headset (`bcdDevice` `0x3109`), Linux `lsusb -v`, `/sys/bus/usb/devices/1-1`, `/sys/bus/usb/devices/1-3`, `/proc/asound/card1`, `/sys/class/hidraw/hidraw1/device/report_descriptor`, `/sys/class/hidraw/hidraw7/device/report_descriptor`, `re-scripts/query_status.py`, and `re-scripts/listen_events.py`, 2026-11-16/17.
- Official HyperX NGENUITY installer: `HyperX_NGENUITY_Installer_2.38.0.0.exe` (`435,177,264` B, `Setup_2.38.0.0_x64.msix`: `Assets/Firmware/03F005B7.bin`, `03F006B7.bin`, `03F00C9D.bin`, `03F00E9D.bin`, `Assets/Native/AirohaHidCoreLib.dll`, `Assets/Native/NGenuity2Helper.exe`), 2026-11-17.
- FCC ID `B94-CL007` (headset, model `CL007`): <https://fccid.io/B94-CL007>
- FCC ID `B94-CL007WA` (2.4 GHz USB wireless dongle, model `CL007WA`): <https://fccid.io/B94-CL007WA>
- Third-party open-source protocol documentation: [LennardKittner/HyperHeadset](https://github.com/LennardKittner/HyperHeadset), [esdedev/nogenuity](https://github.com/esdedev/nogenuity), [HeyOkay/HaloBattery](https://github.com/HeyOkay/HaloBattery), [Sapd/HeadsetControl](https://github.com/Sapd/HeadsetControl).

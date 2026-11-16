# Reverse-Engineering Scripts (`hyperx-cloud-iii-wireless`)

Passive, non-destructive inspection scripts and offline unit tests for the HyperX Cloud III Wireless 2.4 GHz USB receiver (`03f0:05b7`) and wired USB-C headset (`03f0:06b7`).

| Script | Touches a device? | What it does |
| :--- | :--- | :--- |
| `inspect_usb_hid.py --offline` | No | Decodes both verified HID report descriptors (`03f0:05b7` receiver 187 B, SHA-256 `ddd28140...6729bf`, and `03f0:06b7` wired headset 150 B, SHA-256 `d8869a8f...a46e1c`) and prints their collection and report layouts. |
| `inspect_usb_hid.py --sysfs` | Kernel sysfs cache only (no USB packets sent) | Reads `/sys/bus/usb/devices`, `/sys/class/hidraw/*/device/report_descriptor`, and `/proc/asound` on Linux for `03f0:05b7` and `03f0:06b7`, redacting serial numbers, and verifies live report descriptors against the recorded hashes. Never opens `/dev/hidraw*`. |
| `test_inspect.py` | No | Offline `unittest` suite verifying the HID report descriptor parser and byte-level equivalence of the shared `0xFF13:0x0001` (73 B) and `0x000B:0x0005` (77 B) blocks across `03f0:05b7` and `03f0:06b7` (run in CI). |

## Usage

```bash
python3 test_inspect.py
python3 inspect_usb_hid.py --offline
python3 inspect_usb_hid.py --sysfs
```

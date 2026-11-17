# Reverse-Engineering Scripts (`hyperx-cloud-iii-wireless`)

Passive and read-only inspection scripts and offline unit tests for the HyperX Cloud III Wireless 2.4 GHz USB receiver (`03f0:05b7`) and wired USB-C headset (`03f0:06b7`).

| Script | Touches a device? | What it does |
| :--- | :--- | :--- |
| `inspect_usb_hid.py --offline` | No | Decodes both verified HID report descriptors (`03f0:05b7` receiver 187 B, SHA-256 `ddd28140...6729bf`, and `03f0:06b7` wired headset 150 B, SHA-256 `d8869a8f...a46e1c`) and prints their collection and report layouts. |
| `inspect_usb_hid.py --sysfs` | Kernel sysfs cache only (no USB packets sent) | Reads `/sys/bus/usb/devices`, `/sys/class/hidraw/*/device/report_descriptor`, and `/proc/asound` on Linux for `03f0:05b7` and `03f0:06b7`, redacting serial numbers, and verifies live report descriptors against the recorded hashes. Never opens `/dev/hidraw*`. |
| `query_status.py` | Read-only (`0x66 0x81..0x8F` queries on `/dev/hidraw*`) | Sends the read-only Report ID `0x66` status queries (`0x81`..`0x8F`) to `03f0:05b7` and `03f0:06b7` and decodes the replies. Refuses any opcode `< 0x80` (blocking all write commands and `0x1E` `RESET_SIRK`) and redacts the 16-byte SIRK pairing key in `0x83` replies. Requires `../udev/70-hyperx-cloud-iii-wireless.rules`. |
| `listen_events.py` | Passive read-only (`os.O_RDONLY` on `/dev/hidraw*`, sends 0 packets) | Passively listens for incoming HID input reports across all collections (`0x66` unsolicited notifications `0x07..0x0D`, `0x0C` Consumer Control volume/media events, `0x05` Telephony Headset events, and `0x07`/`0x0B` Airoha RACE over USB HID input). |
| `inspect_fota_package.py` | No | Offline parser and SHA-256 verifier for Airoha AB1565 FOTA `.bin` firmware images (`03F005B7.bin`, `03F006B7.bin`, `03F00C9D.bin`, `03F00E9D.bin`). |
| `test_inspect.py` | No | Offline `unittest` suite verifying the HID report descriptor parser, byte-level equivalence of the shared `0xFF13:0x0001` (73 B) and `0x000B:0x0005` (77 B) blocks, `query_status.py` safety guards and SIRK redaction, `listen_events.py` report decoders, and `inspect_fota_package.py` TLV/hash verification (run in CI). |

## Usage

```bash
python3 test_inspect.py
python3 inspect_usb_hid.py --offline
python3 inspect_usb_hid.py --sysfs

# Optional read-only hardware status query & passive event listener (after installing ../udev/70-hyperx-cloud-iii-wireless.rules):
python3 query_status.py
python3 listen_events.py --duration 10.0

# Offline Airoha FOTA firmware binary header inspection:
python3 inspect_fota_package.py /path/to/03F005B7.bin /path/to/03F006B7.bin
```

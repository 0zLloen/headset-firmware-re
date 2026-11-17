# `headset-firmware-re` — Gaming & Wireless Headset Firmware Reverse Engineering Archive

Open documentation, USB Audio and HID protocol specifications, bootloader protocols, flash memory layouts, and safe non-destructive inspection utilities for commercial gaming and wireless headsets.

---

## Repository Structure

```text
headset-firmware-re/
├── CONTRIBUTING.md                            # Safety ladder and evidence rules for reverse-engineering a headset
├── schema/device.schema.json                  # JSON Schema for every devices/*/device.yaml (checked in CI)
├── .github/                                   # Issue forms (new device, finding/correction), PR checklist, CI
├── platforms/
│   └── README.md                              # Shared OEM / wireless audio SoC / bootloader families
└── devices/
    ├── _template/                             # Copy to devices/<vendor>-<model>/: README.md skeleton + device.yaml
    └── hyperx-cloud-iii-wireless/             # HyperX Cloud III Wireless (HP Inc., FCC IDs: B94-CL007 / B94-CL007WA)
        ├── README.md                          # Status, file list, and open questions
        ├── device.yaml                        # Structured summary: USB IDs (03f0:06b7 & 03f0:05b7), Airoha AB1565 SoC, HID
        ├── usb-and-hid.md                     # Verified USB Audio Class 1.0 topology, 187 B & 150 B HID descriptors,
        │                                      #   and the 0xFF13 / Report ID 0x66 command set
        ├── firmware-updater.md                # Verified Airoha AB1565 FOTA package headers (03F005B7.bin / 03F006B7.bin),
        │                                      #   flash partition tables, and RACE over USB HID (0x06/0x07) update flow
        ├── hardware-and-fcc.md                # Verified Airoha AB1565 SoCs, FCC grant specs, controls, flash layout
        ├── re-scripts/
        │   ├── README.md                      # Passive sysfs / read-only HID & FOTA inspection scripts
        │   ├── inspect_usb_hid.py             # Offline HID report descriptor decoder + passive Linux sysfs reader
        │   ├── query_status.py                # Read-only Report ID 0x66 (0x81..0x8F) status probe (refuses < 0x80 writes)
        │   ├── listen_events.py               # Passive O_RDONLY listener for 0x66, 0x0C, 0x05, and 0x07/0x0B reports
        │   ├── inspect_fota_package.py        # Offline Airoha AB1565 FOTA .bin header & SHA-256 verifier
        │   └── test_inspect.py                # Offline unit tests for descriptors, safety guards, and FOTA headers (CI)
        └── udev/
            └── 70-hyperx-cloud-iii-wireless.rules
```

---

## Contributing

Reverse-engineered a headset, or want to? [`CONTRIBUTING.md`](CONTRIBUTING.md) walks through it as a safety ladder, from reading USB Audio and HID descriptors to backing up and writing flash, and explains how to submit what you find:

- copy [`devices/_template/`](devices/_template/) to `devices/<vendor>-<model>/` and fill in `device.yaml` (validated against [`schema/device.schema.json`](schema/device.schema.json)) and `README.md`, then open a pull request;
- or, without a pull request, open a [New device report](https://github.com/0zLloen/headset-firmware-re/issues/new?template=new-device.yml) or a [Finding or correction](https://github.com/0zLloen/headset-firmware-re/issues/new?template=finding.yml) issue.

---

## Repository Policies

1. **No Proprietary Firmware Binaries Committed**:
   - Do **not** commit vendor `.exe`, `.dll`, `.msix`, `.appx`, `.bin`, or `.hex` firmware dumps.
   - Document official package URLs, version numbers, and SHA-256 checksums so researchers can verify and extract their own local copies.
   - Never publish an image that contains vendor code, such as a patched stock image, anywhere: not in the repository, a release, an issue or a discussion. Describe how to build it from the user's own copy of the official image instead.
2. **Evidence Classification**:
   - Every claim is labelled as defined in [`CONTRIBUTING.md`](CONTRIBUTING.md#evidence-rules):
     - **Verified**: observed directly on a real unit (USB enumeration, audio/HID descriptors, a read-back, a measurement), or read literally from an official file, grant, or photo (a hash, a record address, a string, a constant, a chip marking).
     - **Inferred**: your interpretation of disassembly, decompilation, USB captures, third-party tool source, or photos: what a pin does, what a command means, how a bootloader behaves.
     - **Unknown**: not established yet; say what would settle it.
3. **Bootloader, Pairing & Calibration Preservation**:
   - Tools in this repository never execute mass-erase or chip-erase operations, and must preserve the resident bootloader, per-unit 2.4 GHz/Bluetooth pairing keys (such as the 16-byte SIRK on `03f0:05b7`, where command `0x66 0x1E` is blocked), and factory acoustic/microphone calibration regions.

---

## Quick Start (HyperX Cloud III Wireless `03f0:05b7` & `03f0:06b7`)

```bash
cd devices/hyperx-cloud-iii-wireless/re-scripts
python3 test_inspect.py                     # offline checks against the verified 187 B & 150 B HID descriptors
python3 inspect_usb_hid.py --offline        # decode both verified HID report descriptors offline
python3 inspect_usb_hid.py --sysfs          # passive read-only inspection of connected 03f0:05b7 & 03f0:06b7 via Linux sysfs
```

`inspect_usb_hid.py` is strictly passive: `--sysfs` only reads kernel-cached descriptors from `/sys/bus/usb/devices`, `/sys/class/hidraw`, and `/proc/asound` (redacting serial numbers) and never opens `/dev/hidraw*` or sends packets to the receiver or headset. To run the read-only `0x66` status queries (`0x81`..`0x8F`) via `query_status.py`, install `devices/hyperx-cloud-iii-wireless/udev/70-hyperx-cloud-iii-wireless.rules` first.

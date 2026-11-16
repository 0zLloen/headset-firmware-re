# <Vendor> <Model> — Firmware Notes

<!--
Copy devices/_template/ to devices/<vendor>-<model>/ (lower case, hyphens), fill in device.yaml
first, then this file. Delete these HTML comments and any section you have nothing for yet,
but keep "Open questions" and "Sources".

Every claim gets a label (CONTRIBUTING.md, "Evidence rules"):
  Verified - observed on a real unit, or read literally from an official file, grant, or photo
  Inferred - your interpretation of disassembly, decompilation, captures, third-party tools, or photos
  Unknown  - not established; say what would settle it
Cite firmware addresses as `<file name> @ 0x0000xxxx` (load address, not file offset).
Never paste serial numbers, Bluetooth/RF addresses or pairing keys.
Worked example: devices/hyperx-cloud-iii-wireless/
-->

Status: <one line: how far the research got, e.g. "USB receiver identified and audio/HID descriptors recorded; nothing written to the device">

Findings use the labels defined in the repository [`CONTRIBUTING.md`](../../CONTRIBUTING.md#evidence-rules).

## 1. Identification

| Item | Value | Evidence | How |
| :--- | :--- | :--- | :--- |
| Receiver application | `vvvv:pppp`, bcdDevice `0x0000`, product `"..."` | **Verified** | `lsusb -v`, YYYY-MM-DD |
| Wired application | | | |
| Bootloader | | | |
| FCC ID(s) | | | label / FCC grant |
| Firmware version reported by the device or vendor app | | | |

## 2. USB Audio and HID interfaces

<!-- One block per interface: number, class/subclass, audio formats/terminals or HID report
     descriptor length and hex, report IDs and what each carries. -->

| Interface | Class / usage | Descriptor / audio format | Report IDs / endpoints | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| 0 | | | | |

## 3. Hardware and pinout

<!-- PCB name/revision, chip markings -> part numbers, crystal, battery, debug pads.
     Pin maps from firmware disassembly are Inferred until probed. -->

| Function | Pin / part | Evidence | Source |
| :--- | :--- | :--- | :--- |
| Headset MCU / Wireless Audio SoC | | | |
| Receiver MCU / Wireless Audio SoC | | | |
| External Codec / Amp (if any) | | | |
| Controls (power, mute/sidetone, volume wheel) | | | |
| Debug pads (SWD/JTAG/UART/ISP) | | | |

## 4. Flash and RAM layout

<!-- Start, end (inclusive), purpose, and whether tools must preserve it. Mark the regions that
     exist only on the device (bootloader, pairing keys, acoustic calibration): they are not in any
     vendor package, so a bad erase loses them for good. -->

| Component | Range | Size | Purpose | Preserve | Evidence | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| headset | `0x00000000`–`0x00000FFF` | | bootloader | yes | | |

## 5. Bootloader and update protocol

<!-- How the device enters the bootloader, its USB identity, the command set (packet layouts
     with byte offsets), any wire obfuscation, whether it can read flash back, and what is
     still Unknown. -->

## 6. Firmware versions and hashes

<!-- Never commit the files. Record where you downloaded them and how they nest. -->

| Component | File | Version | Size (bytes) | SHA-256 | Origin / container |
| :--- | :--- | :--- | :--- | :--- | :--- |
| | | | | | |

Image format: <Intel HEX / raw bin / vendor container>; base address `0x...`; encrypted / signed / compressed: <yes/no + evidence>.

## 7. Recovery

<!-- Every way back to stock you know of, and whether it was actually tried on this device. -->

| Method | Tried? | Evidence | Notes |
| :--- | :--- | :--- | :--- |
| Official updater re-flash | | | |

## 8. Open questions

- <What is Unknown, and what would settle it>

## 9. Sources

- Vendor download page(s), with access date
- FCC ID / teardown photos (link, do not re-host)
- Tools and versions used

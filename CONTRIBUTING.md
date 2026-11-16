# Contributing: reverse-engineer your headset and publish what you find

This guide is for people who want to find out how their gaming or wireless headset's firmware works (which wireless audio SoC, MCU, or codec it uses, how USB Audio and HID control channels are structured, how firmware updates work, where the bootloader and pairing/calibration data live, and whether it can run open tools or custom firmware) and add that knowledge here in a form others can build on. You do not need prior firmware experience. You do need patience, a notebook, and the discipline to stop before steps that can brick your headset or unpair its wireless receiver.

The worked example is [`devices/hyperx-cloud-iii-wireless/`](devices/hyperx-cloud-iii-wireless/): start with its [`README.md`](devices/hyperx-cloud-iii-wireless/README.md) (status and open questions) and [`device.yaml`](devices/hyperx-cloud-iii-wireless/device.yaml), then read the Markdown files it lists.

**Contents:** [Ground rules](#ground-rules) · [Evidence rules](#evidence-rules) · [The safety ladder](#the-safety-ladder) · [Submitting](#submitting) · [Review checklist](#review-checklist)

---

## Ground rules

1. **Climb the ladder in order.** Each step below is more invasive than the one before. Most of the useful facts come from the first five steps, in which you never write anything to the headset or receiver yourself (changing settings like sidetone or EQ in the vendor app during step 4 is fine; letting it update firmware is a write, see step 4).
2. **Back up before you write.** Nothing you send writes firmware until there is a verified backup and a known way back (step 7).
3. **Never mass-erase.** No `nrfjprog --recover`, `--eraseall`, OpenOCD mass-erase, STM32 RDP regression, SPI flash chip-erase, or any "unlock" that erases the chip. It destroys the bootloader, the per-unit 2.4 GHz/Bluetooth pairing keys, and factory acoustic/ANC/microphone calibration data, which exist nowhere else.
4. **Never send bytes you do not understand.** Vendor HID commands that look harmless can erase flash, enter a one-way ISP mode, or overwrite the receiver's pairing ID. Only send a command you have seen the vendor software send and that you have good reason to believe is read-only.
5. **Label every claim** as Verified, Inferred or Unknown, and say how you know it.
6. **No vendor binaries, no dumps, no personal data in the repository.** URLs and SHA-256 hashes instead of files; serial numbers, Bluetooth MACs, and 2.4 GHz pairing keys redacted.
7. **Keep a lab notebook.** Date, command, output, file hash. Your notebook is your evidence; the `source` fields in `device.yaml` are copied from it.

---

## Evidence rules

Every factual statement in a device folder or platform document carries one label:

| Label | Meaning | What the `source` must say |
| :--- | :--- | :--- |
| **Verified** | Observed directly on a real unit (USB enumeration, audio/HID descriptors, a read-back, a measurement), or read literally from an official file or photo (a hash, a record address, a string, a constant, a chip marking, an FCC grant). | What you ran or read, and when: command + date, file name + address, photo/grant URL + exhibit. |
| **Inferred** | Your interpretation of disassembly, decompilation, USB captures, third-party tool source, or photos: what a pin does, what a command means, how a bootloader behaves. | What you inferred it from. |
| **Unknown** | Not established yet. | What would settle it. |

Rules of thumb:

- Label the claim, not the document. In Markdown a row can carry two labels (Verified for the marking, Inferred for the part it implies); `device.yaml` has one label per item, so use the weaker one and name the stronger part in `source`.
- A value read from vendor software is Verified as a constant. What it implies about the device ("the bootloader enumerates as `03f0:xxxx`") is Inferred until it is seen on the device.
- When unsure, use the weaker label. Upgrading a label needs new evidence, and the edit says what it was.
- "Documented" is not "tested". Anything not yet exercised on hardware says so explicitly.
- If two sources disagree, record both with their sources and mark the point Unknown until one is confirmed.
- Cite firmware locations as `<file name> @ <load address>`, e.g. `firmware.bin @ 0x000184EC`. Use load addresses, not file offsets, and name the exact file version.

---

## The safety ladder

| Step | Touches the headset/receiver? | Can brick it? | Typical labels |
| :--- | :--- | :--- | :--- |
| [1. Identify](#1-identify-the-device) | Standard descriptor reads only | No | Verified |
| [2. Open-source intel](#2-open-source-intel) | No | No | Verified (markings, grants), Inferred (parts, protocols) |
| [3. Vendor updater analysis](#3-vendor-updater-analysis) | No | No | Verified (hashes, constants), Inferred (behaviour) |
| [4. Passive USB capture](#4-passive-usb-capture) | Only the vendor app talks to it | Only as much as the vendor app | Verified (bytes), Inferred (meaning) |
| [5. Static disassembly](#5-static-disassembly) | No | No | Inferred, Verified for literal constants |
| [6. Read-back and backup](#6-read-back-and-backup) | Yes, read-only commands | Unlikely, but the device is now in a special mode | Verified |
| [7. Writing flash and SWD](#7-writing-flash-and-swd) | Yes, writes | **Yes** | Verified only for what you actually did |

Start `devices/<vendor>-<model>/device.yaml` from [`devices/_template/`](devices/_template/) at step 1 and fill it in as you go. A pull request after step 1 or 2 is welcome; you do not need to finish the ladder.

### 1. Identify the device

Connect the wireless receiver (or base station), and also plug the headset in directly by USB cable if it supports USB data or firmware updates over the cable. Record each identity. These commands only read what the kernel already fetched when the device was plugged in, plus standard USB descriptors.

```bash
lsusb                                    # find it: "Bus 001 Device 002: ID 03f0:05b7 HP, Inc HyperX Cloud III Wireless"
sudo lsusb -v -d 03f0:05b7 > lsusb-03f0-05b7.txt   # all descriptors (USB Audio Class + HID); HID report descriptors
                                         # show "** UNAVAILABLE **" while usbhid owns them: use sysfs below
lsusb -t                                 # interfaces, drivers (snd-usb-audio, usbhid), speed (12M = full-speed)
cat /proc/asound/cards                   # ALSA sound card index for the headset/receiver
cat /proc/asound/card1/stream0 /proc/asound/card1/usbmixer

id=0003:000003F0:000005B7                # HID_ID = bus:VID:PID, upper case, zero-padded; bus 0003 = USB
for h in /sys/class/hidraw/hidraw*; do   # one hidraw node per HID interface
  grep -qi "HID_ID=$id" "$h/device/uevent" || continue
  echo "== $h interface $(basename "$(readlink -f "$h/device/..")" | sed 's/.*\.//')"
  echo "report descriptor: $(wc -c < "$h/device/report_descriptor") bytes"
  xxd -p "$h/device/report_descriptor" | tr -d '\n'; echo
  hid-decode "$h/device/report_descriptor"   # pipx install hid-tools
done
```

Windows: Device Manager → the device → Properties → Details → *Hardware Ids* shows `USB\VID_03F0&PID_05B7&REV_4109&MI_03` (`REV` is `bcdDevice`, `MI` the interface); [USB Device Tree Viewer](https://www.uwe-sieber.de/usbtreeview_e.html) shows every descriptor including USB Audio Class and HID report descriptors. macOS: `system_profiler SPUSBDataType` (`SPUSBHostDataType` on recent versions) and `ioreg -p IOUSB -l -w0`.

**Record:** VID:PID and role of every identity (`application`, `receiver-application`, `base-station-application`; bootloaders come later), `bcdDevice`, the `iManufacturer` and `iProduct` strings exactly, USB speed, USB Audio Class version (`bcdADC`), AudioControl terminal/feature-unit topology, AudioStreaming sample rates and bit depths (playback and capture), each HID interface with its report descriptor length and hex, the firmware version shown by the vendor app, and the FCC ID(s) from the earcup/headband and dongle labels. Look for a vendor-defined usage page (`0xFF00`–`0xFFFF`) with Output, Input, or Feature reports: that is usually the telemetry, EQ/sidetone control, and firmware update channel.

**Do not record** `iSerial`, `HID_UNIQ`, or Bluetooth addresses (`bluetoothctl info` prints one). Replace them with `<redacted>` when you paste output.

**Label:** Verified, with the command and date.

### 2. Open-source intel

Before opening anything, find what others already published.

- **FCC ID** (headset label under ear cushion or on inner headband, receiver label on the USB plug/housing, manual, or box): wireless headsets normally have **two** FCC IDs—one for the headset (`B94-CL007`) and one for the wireless dongle (`B94-CL007WA`). Search [fccid.io](https://fccid.io/) or the [FCC database](https://apps.fcc.gov/oet/cf/eas/reports/GenericSearch.cfm). The *internal photos* exhibit usually shows both PCB sides; the test report names the frequency band, channel spacing, and modulation. Other regulators (ISED Canada, NCC Taiwan, KC Korea, MIC Japan) sometimes have unredacted internal photos when FCC exhibits are under short-term confidentiality.
- **Teardowns:** repair guides, battery replacement videos, enthusiast forums.
- **Chip markings → parts.** Zoom into the photos and copy the package text exactly. Decode it with the manufacturer's datasheet ("ordering information" / "marking" sections). Common wireless headset SoC/audio families include Skyworks/Avnera (`AV62xx`/`AV63xx`), Realtek (`RTL8763`/`RTL8773`), Actions (`ATS2831`/`ATS2853`), C-Media (`CM700x`), Airoha (`AB156x`), Bestechnic (`BES2300`/`BES2500`), Nordic (`nRF52840`/`nRF5340`), and Telink (`TLSR8xxx`/`TLSR9xxx`).
- **Existing projects:** search for the VID:PID and model name in [HeadsetControl](https://github.com/Sapd/HeadsetControl), [HyperHeadset](https://github.com/LennardKittner/HyperHeadset), [HaloBattery](https://github.com/HeyOkay/HaloBattery), [OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB), Linux kernel `sound/usb/quirks.c`, and GitHub issues/PRs.

**Record:** the FCC ID(s) and exhibit URLs, PCB silkscreen (name, revision, date), every marking you can read with the photo it came from, the parts you derive, and links to related open-source tools.

**Label:** markings read from a photo and numbers read from an FCC grant are Verified (cite the exhibit); the part a custom marking implies or a protocol reverse-engineered in a third-party repository (until you test or capture it yourself) is Inferred.

### 3. Vendor updater analysis

The official updater or companion suite (e.g. HyperX NGENUITY, Logitech G HUB, SteelSeries GG, Razer Synapse, Corsair iCUE) contains the firmware images and the code that talks to the bootloader.

1. **Download it yourself** from the vendor's official site or store package. Record the page URL, the file URL, the date, the version and the size, and hash every file you get or extract (`sha256sum *`). Keep your copies outside the repository.
2. **Extract, don't run.** Work in a throwaway VM or an offline directory. Installers and store packages unpack without executing anything:
   - MSIX / Appx bundles (Microsoft Store packages such as HyperX NGENUITY): unzip the `.msixbundle` / `.appxbundle` and the inner `.msix` / `.appx` with `7z x` or `unzip`.
   - Inno Setup: `innoextract Setup.exe`; NSIS, self-extracting archives, many MSIs: `7z x`; MSI: `msiextract`.
   - Electron apps: `npx @electron/asar extract resources/app.asar app/`.
   - .NET executables and DLLs: decompile with [ILSpy](https://github.com/icsharpcode/ILSpy) / `ilspycmd` or dnSpyEx. Look for VID/PID constants, report IDs, archive passwords, XOR keys, command bytes, and the update state machine.
   - Native code: Ghidra (step 5).
3. **Identify the image format.** Intel HEX, Motorola S-record, raw `.bin`, DFU, UF2, or a vendor container with a header (often containing separate payloads for the USB dongle and the headset DSP/MCU).

**Record:** the full nesting, each file's name, version, size and SHA-256, the image format, address range and entry point, whether it is encrypted, signed or checksummed, and which parts of flash the update writes.

**Never commit** the downloaded or extracted files, or full decompiled vendor source.

**Label:** hashes, sizes, record addresses and literal constants are Verified; what the updater code does is Inferred.

### 4. Passive USB capture

Watch the vendor software talk to the receiver and headset. You send nothing yourself.

**Linux (`usbmon` + Wireshark):**

```bash
sudo modprobe usbmon
lsusb -d 03f0:05b7                       # "Bus 001 Device 002" -> interface usbmon1, address 2
sudo dumpcap -i usbmon1 -w battery-poll.pcapng   # Ctrl-C when done
```

Display filters: `usb.device_address == 2 && usb.transfer_type != 0x00` (exclude isochronous audio transfers `0x00` so the capture is not flooded with PCM audio frames; use `usb.transfer_type == 0x02` for control transfers `SET_REPORT`/`GET_REPORT` and `usb.transfer_type == 0x01` for interrupt HID reports).

**Privacy:** `usbmon` and `USBPcap` capture *every* device on that bus, including your keyboard and USB microphone audio. Do not type passwords or speak sensitive information while capturing, filter out isochronous audio endpoints before exporting text excerpts, and **never commit raw `.pcap`/`.pcapng` captures**. Commit redacted text excerpts only.

**Receivers.** A 2.4 GHz wireless audio dongle handles some USB HID commands locally (USB audio mixer, dongle firmware version, link status, pairing mode) and relays others over the air to the headset (battery level, mic mute, sidetone, sleep timer, EQ presets, headset OTA/cable firmware update). Document which commands work with the headset powered off (receiver-local) versus powered on and linked (relayed).

**Label:** bytes on the wire are Verified (cite the capture name and date); what a field means is Inferred until cross-checked against code (step 3 or 5).

### 5. Static disassembly

Load the firmware into [Ghidra](https://ghidra-sre.org/) or another disassembler.

1. **Identify the architecture.** ARM Cortex-M (`ARM:LE:32:Cortex`), RISC-V, 8051, or a proprietary audio DSP core (e.g. Kalimba, Xtensa HiFi, Avnera).
2. **Vector table and memory map.** Locate the initial stack pointer, reset handler, peripheral register bases, and external SPI/QSPI flash mapping if execute-in-place (XIP) is used.
3. **Strings and constants.** Search for USB descriptor strings (UTF-16LE), SDK assert paths, HID report IDs (`0x66`, `0x06`, `0x0A`), and command opcodes observed in step 4.
4. **Flash map.** Identify where the bootloader, application partition, DSP coefficients, acoustic calibration, and 2.4 GHz/Bluetooth pairing pages reside.

**Label:** Inferred, except literal constants, strings and addresses read from the image (Verified).

### 6. Read-back and backup

Before anything is ever written, make a backup of everything that is **not** in the vendor package: the bootloader, settings, 2.4 GHz/Bluetooth pairing keys, and per-unit acoustic/ANC calibration pages.

- Read twice and compare: `sha256sum backup-1.bin backup-2.bin`. Keep backups outside the repository.
- **Never commit dumps,** even of your own unit: they contain serial numbers, pairing keys, and calibration data.

**Label:** Verified (the data came off the device).

### 7. Writing flash and SWD

This is the step that can brick a headset or receiver. Do not start it until all of these hold:

1. **A full backup** from step 6, read twice with matching hashes.
2. **A known recovery path** that does not depend on what you are about to write.
3. **A documented flash layout** in `device.yaml` with `preserve: true` on the bootloader, pairing, and calibration regions.
4. **A tool that verifies by read-back** before handing control to the new image.

---

## Submitting

### Where things go

```text
devices/<vendor>-<model>/      one product: its USB identities, audio/HID descriptors, hardware,
  device.yaml                  flash layout, updater analysis, recovery notes (copy devices/_template/)
  README.md                    or topic files listed under docs: in device.yaml
platforms/<family>/            shared by several products: an OEM/SoC/bootloader family's protocol
  tools/                       spec and the tools that speak it, with an offline test
schema/device.schema.json      the device.yaml schema (CI validates every device folder against it)
```

- **Device folder name:** `<vendor>-<model>`, lower case ASCII, words joined by hyphens, as marketed (`hyperx-cloud-iii-wireless`). Add a suffix such as `-rev2` only for a hardware revision that differs, and note how to tell them apart.
- **Platform folder name:** `<oem-or-chip-vendor>-<family>`. Start in your device folder; move protocol specs and tools to `platforms/` once a second device is shown to share them, and set `platform:` in each `device.yaml`.
- **Tools** follow the repository rules: Python standard library where possible, read-only unless the subcommand says otherwise, never mass-erase, refuse images that overlap preserved regions, verify by read-back before handing control to the new image, and ship an offline test that runs in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

### Pull request

```bash
gh repo fork 0zLloen/headset-firmware-re --clone   # or fork on github.com and clone
cd headset-firmware-re
git switch -c device/<vendor>-<model>
cp -r devices/_template devices/<vendor>-<model>
# fill in device.yaml first, then README.md
pipx run check-jsonschema --schemafile schema/device.schema.json devices/<vendor>-<model>/device.yaml
git add devices/<vendor>-<model>
git commit -m "devices: add <vendor> <model>"
git push -u origin device/<vendor>-<model>
gh pr create --web
```

### Never commit

- Vendor firmware, updaters or anything extracted from them. Link the official download and record the SHA-256 instead. CI fails if any tracked file matches `.gitignore`.
- Flash dumps or backups, even of your own unit.
- Raw USB captures (`.pcap`, `.pcapng`): commit redacted text excerpts.
- Full decompiled vendor source or long disassembly listings. Short excerpts with addresses are fine.
- Firmware encryption or signing keys found in vendor software.
- Images that contain vendor code, such as a patched stock image.

### Privacy

Before you push, search your changes for:

- USB serial numbers (`iSerial`, `HID_UNIQ`), Bluetooth MAC addresses, 2.4 GHz RF addresses, and pairing keys.
- Serial stickers in your own photos, and EXIF metadata (`exiftool -all= photo.jpg`).
- Your user name, host name or home path in pasted terminal output.

### Licensing

This repository is under the [MIT License](LICENSE). By contributing, you agree that your text, tables, code and your own photos are published under it.

---

## Review checklist

Reviewers check, and authors tick in the pull request:

- [ ] Folder name follows `devices/<vendor>-<model>/` (or `platforms/<oem>-<family>/` for shared material).
- [ ] `device.yaml` validates against `schema/device.schema.json` and agrees with the Markdown.
- [ ] Every claim is labelled Verified, Inferred or Unknown, with how it was verified (command + date, file + address, photo/grant URL) or what would settle it.
- [ ] Firmware addresses name the exact image file and version.
- [ ] Vendor files are referenced by official URL, version and SHA-256; no binaries, dumps or raw captures are added.
- [ ] Serial numbers, Bluetooth/RF addresses, pairing keys, photo metadata and personal paths are removed.
- [ ] Anything not exercised on hardware is marked untested.
- [ ] Write procedures preserve the bootloader and unit-specific pages, never mass-erase, require a backup first, and name the recovery path (and whether it was tested).
- [ ] New tools have an offline test that runs in CI.
- [ ] The contribution is the author's own work and can be published under the MIT License.

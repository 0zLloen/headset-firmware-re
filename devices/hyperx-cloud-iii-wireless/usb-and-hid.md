# HyperX Cloud III Wireless — USB Audio & HID Protocol Notes

Findings use the evidence labels defined in [`CONTRIBUTING.md`](../../CONTRIBUTING.md#evidence-rules).

---

## 1. USB Device & Configuration Summary (`03f0:05b7` Receiver vs. `03f0:06b7` Wired Headset)

All fields in the table below are **Verified** on a retail unit via `lsusb -v`, `/sys/bus/usb/devices/1-1/*` (receiver), and `/sys/bus/usb/devices/1-3/*` (headset over USB-C cable) on `2026-11-16` unless marked otherwise:

| Field | 2.4 GHz USB Receiver (`03f0:05b7`) | Wired USB-C Headset (`03f0:06b7`) | Evidence | Notes / Source |
| :--- | :--- | :--- | :--- | :--- |
| `idVendor` : `idProduct` | `03f0:05b7` | `03f0:06b7` | **Verified** | `lsusb`, 2026-11-16 (alternate receiver PID `03f0:0c9d` is **Inferred** from `HaloBattery`/`nogenuity`) |
| `bcdUSB` / Speed | `2.00` / `12 Mb/s` (Full-Speed) | `2.00` / `12 Mb/s` (Full-Speed) | **Verified** | `bMaxPacketSize0 = 64` on both, `lsusb -v`, 2026-11-16 |
| `bcdDevice` | `41.09` (`0x4109`) | `31.09` (`0x3109`) | **Verified** | `/sys/bus/usb/devices/1-1/bcdDevice` (`4109`) and `1-3/bcdDevice` (`3109`), 2026-11-16 |
| Firmware version | `v4.1.0.9` | `v3.1.0.9` | **Inferred** | Derived from `bcdDevice` `41.09` (dongle) and `31.09` (headset), matching HyperX NGENUITY's paired `4.1.0.9` / `3.1.0.9` release numbers |
| `iManufacturer` (index 1) | `"HP, Inc"` | `"HP, Inc"` | **Verified** | `lsusb -v`, 2026-11-16 |
| `iProduct` (index 2) | `"HyperX Cloud III Wireless"` | `"HyperX Cloud III Wireless"` | **Verified** | `lsusb -v`, 2026-11-16 |
| `iSerial` (index 3) | 16 ASCII zeros (`<redacted>`) | 16 ASCII zeros (`<redacted>`) | **Verified** | Both devices report a fixed 16-zero placeholder string rather than a unique serial, 2026-11-16 |
| Power attributes | `bmAttributes = 0x80` (Bus Powered), `MaxPower = 20mA` | `bmAttributes = 0xc0` (Self Powered), `MaxPower = 20mA` | **Verified** | `lsusb -v`, 2026-11-16 |
| `bNumInterfaces` / `wTotalLength` | `4` interfaces (`0..3`), `wTotalLength = 0x0115` (277 B) | `1` interface (`0`), `wTotalLength = 0x0022` (34 B) | **Verified** | Receiver is USB Audio Class 1.0 + HID; wired headset is **HID-only** (no USB Audio over the USB-C cable), `lsusb -v`, 2026-11-16 |
| HID Interrupt IN Endpoint | Interface `3`: `0x84` (`EP 4 IN`, 64 B, `bInterval = 4` ms) | Interface `0`: `0x84` (`EP 4 IN`, 64 B, `bInterval = 4` ms) | **Verified** | Identical endpoint number (`0x84`), packet size (`64 B`), and interval (`4 ms`) on both boards, `lsusb -v`, 2026-11-16 |
| HID Report Descriptor Length | `187` bytes (`[0, 0, 0, 187]`) | `150` bytes (`[150]`) | **Verified** | `/sys/class/hidraw/hidraw1/device/report_descriptor` and `hidraw7/device/report_descriptor`, 2026-11-16 |

---

## 2. USB Interface Map & Audio Class 1.0 Topology (`03f0:05b7` Receiver)

The `03f0:05b7` receiver is a composite USB Audio Class 1.0 (`bcdADC = 1.00`) and USB HID (`bcdHID = 1.10`) device with 4 interfaces, whereas the `03f0:06b7` wired USB-C headset exposes only a single HID interface (`Interface 0`) (**Verified** via `lsusb -v`, `lsusb -t`, and `/proc/asound/card1/*`, 2026-11-16):

| Device | Interface | Altset | Class / SubClass | Driver (Linux) | Endpoints | Role / Format | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `03f0:05b7` | `0` | `0` | `0x01` Audio / `0x01` Control (`bcdADC 1.00`) | `snd-usb-audio` | `0` (EP0 control) | AudioControl (`wTotalLength = 0x004e` = 78 B), manages streaming interfaces `1` and `2`; `iInterface = "HyperX Cloud III Wireless"` | **Verified** |
| `03f0:05b7` | `1` | `0` | `0x01` Audio / `0x02` Streaming | `snd-usb-audio` | `0` | Playback idle (zero bandwidth) | **Verified** |
| `03f0:05b7` | `1` | `1` | `0x01` Audio / `0x02` Streaming | `snd-usb-audio` | `0x01` (`EP 1 OUT`, Isochronous Adaptive, `wMaxPacketSize = 384 B`, `bInterval = 1`) | Playback: PCM (`0x0001`), 2 ch (`FL FR`), **16-bit** (`bSubframeSize = 2`), discrete rates **48,000 Hz** and **96,000 Hz** (`bTerminalLink = 1`) | **Verified** |
| `03f0:05b7` | `1` | `2` | `0x01` Audio / `0x02` Streaming | `snd-usb-audio` | `0x01` (`EP 1 OUT`, Isochronous Adaptive, `wMaxPacketSize = 576 B`, `bInterval = 1`) | Playback: PCM (`0x0001`), 2 ch (`FL FR`), **24-bit** (`bSubframeSize = 3`, `S24_3LE`), discrete rates **48,000 Hz** and **96,000 Hz** (`bTerminalLink = 1`) | **Verified** |
| `03f0:05b7` | `2` | `0` | `0x01` Audio / `0x02` Streaming | `snd-usb-audio` | `0` | Capture idle (zero bandwidth) | **Verified** |
| `03f0:05b7` | `2` | `1` | `0x01` Audio / `0x02` Streaming | `snd-usb-audio` | `0x81` (`EP 1 IN`, Isochronous Adaptive, `wMaxPacketSize = 64 B`, `bInterval = 1`) | Capture (Mic): PCM (`0x0001`), 1 ch (`MONO`), **16-bit** (`bSubframeSize = 2`), discrete rates **16,000 Hz** and **32,000 Hz** (`bTerminalLink = 7`) | **Verified** |
| `03f0:05b7` | `3` | `0` | `0x03` HID / `0x00` / `0x00` | `usbhid` (`hid-generic`) | `0x84` (`EP 4 IN`, Interrupt, `wMaxPacketSize = 64 B`, `bInterval = 4` = 4 ms) | 187-byte HID Report Descriptor (`0xFF13:0x0001` vendor, `0x0C:0x01` consumer, `0x0B:0x05` telephony); `iInterface = "HyperX Cloud III Wireless"` | **Verified** |
| `03f0:06b7` | `0` | `0` | `0x03` HID / `0x00` / `0x00` | `usbhid` (`hid-generic`) | `0x84` (`EP 4 IN`, Interrupt, `wMaxPacketSize = 64 B`, `bInterval = 4` = 4 ms) | 150-byte HID Report Descriptor (`0xFF13:0x0001` vendor, `0x0B:0x05` telephony; omits the 37-byte `0x0C:0x01` consumer collection); `iInterface = "HyperX Cloud III Wireless"` | **Verified** |

### 2.1 AudioControl Terminal & Unit Graph (`03f0:05b7` Interface 0)

**Verified** from `lsusb -v -d 03f0:05b7` and `/proc/asound/card1/usbmixer` (2026-11-16):

- **Playback path**:
  - **Input Terminal `1`** (`INPUT_TERMINAL`): `wTerminalType = 0x0101` (USB Streaming), `bNrChannels = 2`, `wChannelConfig = 0x0003` (Left Front, Right Front).
  - **Feature Unit `2`** (`FEATURE_UNIT`, `bSourceID = 1`, `bControlSize = 1`):
    - Master channel (`bmaControls(0) = 0x01`): Mute Control (`PCM Playback Switch`, `INV_BOOLEAN`).
    - Channel 1 & 2 (`bmaControls(1) = 0x02`, `bmaControls(2) = 0x02`): Volume Control (`PCM Playback Volume`, 2 channels, `S16`, raw range `-18944` to `-1`, corresponding to `-74.00 dB` to `0.00 dB`).
  - **Output Terminal `3`** (`OUTPUT_TERMINAL`, `bSourceID = 2`): `wTerminalType = 0x0302` (Headphones).
- **Capture (Microphone) path**:
  - **Input Terminal `5`** (`INPUT_TERMINAL`): `wTerminalType = 0x0201` (Microphone), `bAssocTerminal = 11`, `bNrChannels = 1`, `wChannelConfig = 0x0000`.
  - **Feature Unit `6`** (`FEATURE_UNIT`, `bSourceID = 5`, `bControlSize = 1`):
    - Master channel (`bmaControls(0) = 0x01`): Mute Control (`Mic Capture Switch`, `INV_BOOLEAN`).
    - Channel 1 (`bmaControls(1) = 0x02`): Volume Control (`Mic Capture Volume`, 1 channel, `S16`, raw range `-18944` to `-1`, corresponding to `-74.00 dB` to `0.00 dB`).
  - **Selector Unit `4`** (`SELECTOR_UNIT`, `bNrInPins = 1`, `baSourceID(0) = 6`).
  - **Output Terminal `7`** (`OUTPUT_TERMINAL`, `bSourceID = 4`): `wTerminalType = 0x0101` (USB Streaming).

---

## 3. HID Report Descriptors (`03f0:05b7` 187 B vs. `03f0:06b7` 150 B)

### 3.1 Receiver Descriptor (`03f0:05b7` Interface 3 — 187 Bytes)

**Verified** from `/sys/class/hidraw/hidraw1/device/report_descriptor` on `2026-11-16` (187 bytes, SHA-256 `ddd28140e5b7628282ef2a2f66d955f8e40f371b48d3f5a19e5599593e6729bf`):

```text
0613ff0901a101150026ff00850609007508953d9102850709007508953d8102
850a09007508953d9122850b0900750895028102856609007508953d91228566
09007508953d8102c0050c0901a101850c1500250109e909ea09e209cd09b509
b6750195068102090095028102c0050b0905a101150025017501850509209501
8122092f95018106092409210997092a09509505810609070509090175019501
81020508850509170909091809200921092a9506912295029101c0
```

### 3.2 Wired Headset Descriptor (`03f0:06b7` Interface 0 — 150 Bytes)

**Verified** from `/sys/class/hidraw/hidraw7/device/report_descriptor` on `2026-11-16` (150 bytes, SHA-256 `d8869a8f6ff66fca2cfa0e9e8ad13f68adb76032b8898677c118991ab7a46e1c`):

```text
0613ff0901a101150026ff00850609007508953d9102850709007508953d8102
850a09007508953d9122850b0900750895028102856609007508953d91228566
09007508953d8102c0050b0905a1011500250175018505092095018122092f95
018106092409210997092a095095058106090705090901750195018102050885
0509170909091809200921092a9506912295029101c0
```

### 3.3 Top-Level Collections and Reports

Comparing the two descriptors (**Verified** with [`re-scripts/inspect_usb_hid.py`](re-scripts/inspect_usb_hid.py), 2026-11-16):
- The 73-byte **Vendor Collection (`0xFF13:0x0001`)** and the 77-byte **Telephony Headset Collection (`0x000B:0x0005`)** are **byte-for-byte identical** between `03f0:05b7` and `03f0:06b7` (`73 + 77 = 150` bytes).
- Only `03f0:05b7` includes the 37-byte **Consumer Control Collection (`0x000C:0x0001`)** at offsets `73..109` (`150 + 37 = 187` bytes).
- Neither descriptor declares any `Feature` (`0xB1`) items.

| Collection | `03f0:05b7` Offsets | `03f0:06b7` Offsets | Usage Page / Usage | Report ID | Direction | Payload Size | Wire Size (with ID) | Item Flags / Fields | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Vendor** | `0..72` (73 B) | `0..72` (73 B) | `0xFF13` / `0x0001` | `0x06` (`6`) | Output (`0x91 0x02`) | 61 B (`0x3D` × 8-bit) | 62 B | `Data,Var,Abs`, Usage `0x00` | **Verified** |
| **Vendor** | `0..72` | `0..72` | `0xFF13` / `0x0001` | `0x07` (`7`) | Input (`0x81 0x02`) | 61 B (`0x3D` × 8-bit) | 62 B | `Data,Var,Abs`, Usage `0x00` | **Verified** |
| **Vendor** | `0..72` | `0..72` | `0xFF13` / `0x0001` | `0x0A` (`10`) | Output (`0x91 0x22`) | 61 B (`0x3D` × 8-bit) | 62 B | `Data,Var,Abs,NoPref`, Usage `0x00` | **Verified** |
| **Vendor** | `0..72` | `0..72` | `0xFF13` / `0x0001` | `0x0B` (`11`) | Input (`0x81 0x02`) | 2 B (`0x02` × 8-bit) | 3 B | `Data,Var,Abs`, Usage `0x00` | **Verified** |
| **Vendor** | `0..72` | `0..72` | `0xFF13` / `0x0001` | `0x66` (`102`) | Output (`0x91 0x22`) | 61 B (`0x3D` × 8-bit) | 62 B | `Data,Var,Abs,NoPref`, Usage `0x00` | **Verified** |
| **Vendor** | `0..72` | `0..72` | `0xFF13` / `0x0001` | `0x66` (`102`) | Input (`0x81 0x02`) | 61 B (`0x3D` × 8-bit) | 62 B | `Data,Var,Abs`, Usage `0x00` | **Verified** |
| **Consumer** | `73..109` (37 B) | *Not present* | `0x000C` / `0x0001` | `0x0C` (`12`) | Input (`0x81 0x02`) | 1 B (6 bits + 2 bits) | 2 B | Bits `0..5`: Volume Up (`0xE9`), Volume Down (`0xEA`), Mute (`0xE2`), Play/Pause (`0xCD`), Next Track (`0xB5`), Prev Track (`0xB6`); Bits `6..7`: `0x00` padding | **Verified** |
| **Telephony** | `110..186` (77 B) | `73..149` (77 B) | `0x000B` / `0x0005` | `0x05` (`5`) | Input (`0x81 ...`) | 1 B (1 + 1 + 5 + 1 bits) | 2 B | Bit 0: Hook Switch (`0x20`, `Abs,NoPref`); Bit 1: Phone Mute (`0x2F`, `Rel`); Bits `2..6`: Redial (`0x24`), Flash (`0x21`), Line Busy Tone (`0x97`), Line (`0x2A`), Speed Dial (`0x50`) (`Rel`); Bit 7: Programmable Button (`0x07` / Button 1 `0x09:0x01`, `Abs`) | **Verified** |
| **Telephony** | `110..186` | `73..149` | `0x000B` / `0x0005` (LEDs `0x0008`) | `0x05` (`5`) | Output (`0x91 ...`) | 1 B (6 bits + 2 bits) | 2 B | Bits `0..5` (Usage Page `0x08` LEDs): Off-Hook (`0x17`), Mute (`0x09`), Ring (`0x18`), Hold (`0x20`), Microphone (`0x21`), On-Line (`0x2A`) (`Data,Var,Abs,NoPref`); Bits `6..7`: Constant padding (`0x91 0x01`) | **Verified** |

Because neither device declares an Interrupt OUT endpoint, host `write()` calls to `/dev/hidrawN` (or `HidD_SetOutputReport` on Windows) travel over the default control pipe (`EP0`) as `SET_REPORT (Output)` transfers.

---

## 4. Vendor Collection `0xFF13:0x0001` — Report ID `0x66` Protocol

The commands below are **Inferred** from open-source implementations ([`LennardKittner/HyperHeadset`](https://github.com/LennardKittner/HyperHeadset), [`HeyOkay/HaloBattery`](https://github.com/HeyOkay/HaloBattery), and [`mihajlo-kuzmanoski/NightfurY-Peripherals`](https://github.com/mihajlo-kuzmanoski/NightfurY-Peripherals)). They have **not** been transmitted to this hardware unit yet.

### 4.1 Frame Layout

- **Request (Host → Receiver/Headset)**: 62-byte Output report with Report ID `0x66` (`buf[0] = 0x66`, `buf[1] = <cmd>`, `buf[2..61] = 0x00` or command parameters). This matches the verified descriptor item for Report ID `0x66` (`1` report-ID byte + `61` data bytes = `62` bytes).
- **Response / Event (Receiver/Headset → Host)**: 62-byte Input report on Interrupt IN endpoint `0x84` with Report ID `0x66` (`buf[0] = 0x66`, `buf[1] = <cmd_or_event>`, `buf[2..61] = payload`).

### 4.2 Known Status Commands & Events (`Inferred`, untested on this unit)

| `buf[0]` | `buf[1]` | Direction | Meaning & Payload Layout | Evidence | Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0x66` | `0x89` | Out (Query) / In (Reply) | **Battery level query/reply**: `buf[4]` holds battery percentage (`0`–`100`) when `buf[2]` or `buf[3]` is non-zero (when the headset is powered off or unlinked, `buf[2]` and `buf[3]` are `0` or `buf[4] > 100`). | **Inferred** | `HeyOkay/HaloBattery` (`docs/protocols.md`), `LennardKittner/HyperHeadset`, `NightfurY-Peripherals` |
| `0x66` | `0x0D` | In (Event) | **Unsolicited battery level event**: same layout as `0x89` reply (`buf[4]` = battery percentage). | **Inferred** | `HeyOkay/HaloBattery` (`docs/protocols.md`) |
| `0x66` | `0x8A` | Out (Query) / In (Reply) | **Charging status query/reply**: `buf[2]` = `0x00` (not charging), `0x01` (charging), `0x02` (fully charged). | **Inferred** | `HeyOkay/HaloBattery` (`docs/protocols.md`) |
| `0x66` | `0x0C` | In (Event) | **Unsolicited charging status event**: `buf[2]` = `0x00` (not charging), `0x01` (charging), `0x02` (fully charged). | **Inferred** | `HeyOkay/HaloBattery` (`docs/protocols.md`) |

### 4.3 Unmapped Report IDs on `0xFF13:0x0001` (`Unknown`)

On both `03f0:05b7` and `03f0:06b7`, the vendor collection `0xFF13:0x0001` also declares:
- Report ID `0x06` (61 B Output, `Data,Var,Abs`) and Report ID `0x07` (61 B Input, `Data,Var,Abs`)
- Report ID `0x0A` (61 B Output, `Data,Var,Abs,NoPref`) and Report ID `0x0B` (2 B Input, `Data,Var,Abs`)

Because `03f0:06b7` (wired headset) is a single-interface HID device used by NGENUITY during wired firmware updates and exposes these exact same report IDs, Report IDs `0x06`/`0x07`/`0x0A`/`0x0B` (or a subcommand of `0x66`) very likely carry the firmware update / ISP frames (**Inferred**). Per [`CONTRIBUTING.md`](../../CONTRIBUTING.md#ground-rules) ground rule 4, never send arbitrary packets to Report IDs `0x06`, `0x0A`, or unknown `0x66` subcommands without first observing them in a passive capture of HyperX NGENUITY or decompiling the updater.

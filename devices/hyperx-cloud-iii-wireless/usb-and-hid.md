# HyperX Cloud III Wireless — USB Audio & HID Protocol Notes

Findings use the evidence labels defined in [`CONTRIBUTING.md`](../../CONTRIBUTING.md#evidence-rules).

---

## 1. USB Device & Configuration Summary (`03f0:05b7` Receiver vs. `03f0:06b7` Wired Headset)

All fields in the table below are **Verified** on a retail unit via `lsusb -v`, `/sys/bus/usb/devices/1-1/*` (receiver), `/sys/bus/usb/devices/1-3/*` (headset over USB-C cable), and `re-scripts/query_status.py` on `2026-11-16/17` unless marked otherwise:

| Field | 2.4 GHz USB Receiver (`03f0:05b7`) | Wired USB-C Headset (`03f0:06b7`) | Evidence | Notes / Source |
| :--- | :--- | :--- | :--- | :--- |
| `idVendor` : `idProduct` | `03f0:05b7` | `03f0:06b7` | **Verified** | `lsusb`, 2026-11-16 (alternate PIDs `03f0:0c9d` receiver and `03f0:0e9d` headset are **Inferred** from `HyperHeadset`/`nogenuity`) |
| `bcdUSB` / Speed | `2.00` / `12 Mb/s` (Full-Speed) | `2.00` / `12 Mb/s` (Full-Speed) | **Verified** | `bMaxPacketSize0 = 64` on both, `lsusb -v`, 2026-11-16 |
| `bcdDevice` | `41.09` (`0x4109`) | `31.09` (`0x3109`) | **Verified** | `/sys/bus/usb/devices/1-1/bcdDevice` (`4109`) and `1-3/bcdDevice` (`3109`), 2026-11-16 |
| Firmware version | `v4.1.0.9` (receiver) / reports paired headset `v3.1.0.9` (`0x3109`) on `0x66 0x81` | `v3.1.0.9` (`0x3109` in both USB `bcdDevice` and `0x66 0x81`) | **Verified** | `bcdDevice` `0x4109` / `0x3109` + `0x66 0x81` identity response (`09 31` at `resp[6..8]`), 2026-11-17 |
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

Because neither device declares an Interrupt OUT endpoint, host `write()` calls to `/dev/hidrawN` travel over the default control pipe (`EP0`) as `SET_REPORT (Output)` transfers.

---

## 4. Vendor Collection `0xFF13:0x0001` — The `66` Command Set (`Report ID 0x66`)

All 13 read-only query commands (`0x81`..`0x8F`) below were **Verified** on a retail `03f0:05b7` receiver (`/dev/hidraw1`) and `03f0:06b7` wired USB-C headset (`/dev/hidraw7`) via [`re-scripts/query_status.py`](re-scripts/query_status.py) on `2026-11-17`. Unsolicited event IDs (`0x07`, `0x09`..`0x0D`) and write/set opcodes (`0x01`..`0x05`, `0x0F`, `0x1E`) are **Inferred** from [`LennardKittner/HyperHeadset`](https://github.com/LennardKittner/HyperHeadset) (`src/devices/cloud_iii_wireless.rs` and `src/devices/cloud_ii_core_wireless.rs`) and [`esdedev/nogenuity`](https://github.com/esdedev/nogenuity) (`docs/PROTOCOL.md` and `src/devices/wireless.rs`).

### 4.1 Frame Layout

- **Request (Host → Receiver/Headset)**: 62-byte Output report with Report ID `0x66` (`buf[0] = 0x66`, `buf[1] = <cmd>`, `buf[2] = <value_or_0x00>`, `buf[3..61] = 0x00`). Read-only queries have bit 7 set (`0x80`..`0x8F`).
- **Response / Unsolicited Event (Receiver/Headset → Host)**: 62-byte Input report on Interrupt IN endpoint `0x84` with Report ID `0x66` (`buf[0] = 0x66`, `buf[1] = <cmd_echo_or_event_id>`, `buf[2..61] = payload`), arriving in `2.8`–`7.9 ms` (**Verified**, 2026-11-17).

### 4.2 Complete `0x66` Command & Event Table

| Feature / Property | Read Cmd (`buf[1]`) | Unsolicited Event (`buf[1]`) | Set Cmd (`buf[1]`) | Verified Response on `03f0:05b7` & `03f0:06b7` (`buf[2..]`) | Evidence (Read / Set) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Device identity & headset firmware version** | `0x81` (`129`) | — | — | • Headset ON (`03f0:05b7` receiver): `buf[2..4]` = `b7 08` (`0x08B7`, internal `"Cloud 3 Wireless Atlas headset"` PID in `NGenuity2Helper.exe`), `buf[4..6]` = `f0 03` (`0x03F0`), `buf[6..8]` = `09 31` (`0x3109` = **`v3.1.0.9`**), `buf[8]` = `0x20` (`32`), `buf[9..41]` = `"HP, IncHyperX Cloud III Wireless"`<br>• Wired USB-C (`03f0:06b7`): identical except `buf[2..4]` = `b7 06` (`0x06B7`)<br>• Headset OFF (`03f0:05b7` receiver): `66 81 00 00...` (`vid_pid=0000:0000`, `headset_fw=0x0000`, `len=0`) | **Verified** (2026-11-17) |
| **Wireless link state** | `0x82` (`130`) | `0x0B` (`11`) | — | `66 82 01 00...` (`buf[2] = 0x01` when headset is on and linked; `0x00` when headset is powered off; unsolicited `66 0b 00 00...` on power-off) | **Verified** (Read & Event, 2026-11-17) |
| **SIRK / Pairing key** | `0x83` (`131`) | — | **`0x1E` (`30`)** | **Transport-asymmetric**:<br>• On `03f0:05b7` (receiver, headset on or off): `buf[2..18]` is all `0x00` (`0/16` non-zero bytes).<br>• On `03f0:06b7` (wired headset): `buf[2..12]` is `0x00`, and **`buf[12..18]` holds a 6-byte non-zero key/RF address** (redacted).<br>• Set `0x1E`: **DANGEROUS** — resets/overwrites SIRK (`CMDHSCloud3WirelessResetSirk`); never send! | **Verified** (Read & NGENUITY class, 2026-11-17) |
| **Sidetone (mic monitoring) on/off** | `0x84` (`132`) | `0x09` (`9`) | `0x01` (`1`) | `66 84 00 00...` (`buf[2] = 0x00` off, `0x01` on; `CMDHSCloud3WirelessGetSidetone` / `SetSidetone`) | **Verified** (Read) / **Inferred** (Set/Event) |
| **Automatic shutdown timer** | `0x85` (`133`) | `0x02` (`2`) | `0x02` (`2`) | `66 85 0a 00...` (`buf[2] = 0x0A` = `10` minutes when headset is on; `0x00` when headset is off; emits unsolicited `66 02 00 00...` on power-off; `CMDHSCloud3WirelessGetPowerAutoOff` / `SetPowerAutoOff`) | **Verified** (Read & Event, 2026-11-17) / **Inferred** (Set) |
| **Microphone mute** | `0x86` (`134`) | `0x0A` (`10`) | `0x03` (`3`) | • Read `0x86`: `66 86 00 00...` (`buf[2] = 0x00` unmuted, `0x01` muted)<br>• Unsolicited `0x0A` on physical mute button press: `66 0a 01 01 00...` (muted) and `66 0a 00 01 00...` (unmuted), where `buf[3] = 0x01` indicates physical button / boom present (`CMDHSCloud3WirelessGetMicMuteState` / `SetMicMuteState`) | **Verified** (Read & Event, 2026-11-17) / **Inferred** (Set) |
| **Playback mute (silent mode)** | `0x87` (`135`) | `0x08` (`8`) | `0x04` (`4`) | • Read `0x87`: `66 87 00 00...` (`buf[2] = 0x00` unmuted)<br>• Unsolicited `0x08` on headset power-off: `66 08 01 00...` (`buf[2] = 0x01` playback muted while disconnected; `CMDHSCloud3WirelessGetPlaybackMuteState` / `SetPlaybackMuteState`) | **Verified** (Read & Event, 2026-11-17) / **Inferred** (Set) |
| **Sidetone volume level** | `0x88` (`136`) | — | `0x05` (`5`) | `66 88 00 00...` (`buf[2] = 0x00` = `+0` default; signed int8 `-5..+5`, `0xFB..0x05`; `CMDHSCloud3WirelessGetSidetoneVolume` / `SetSidetoneVolume`) | **Verified** (Read) / **Inferred** (Set) |
| **Battery level & cell voltage** | `0x89` (`137`) | `0x0D` (`13`) | — | • `66 89 10 37 55...` (`85%`, `4151 mV` / `0x1037` charging)<br>• `66 89 10 3d 56...` (`86%`, `4157 mV` / `0x103D` charging)<br>• `66 89 10 45 64...` (`100%`, `4165 mV` / `0x1045` unplugged)<br>• `66 89 00 00 00...` (`0%`, `0 mV` when headset is off; emits unsolicited `66 0d 00 00...` on power-off) | **Verified** (Read & Event, 2026-11-17) |
| **Charging status** | `0x8A` (`138`) | `0x0C` (`12`) | — | • `66 8a 01 00...` (`buf[2] = 0x01` Charging while USB-C is connected)<br>• `66 8a 00 00...` (`buf[2] = 0x00` NotCharging when unplugged or headset off; `2` full, `3+` error) | **Verified** (Read) / **Inferred** (Event) |
| **Mic boom connected** | `0x8C` (`140`) | `0x07` (`7`) | — | `66 8c 01 00...` (`buf[2] = 0x01` connected when headset is on; `0x00` when headset is off; emits unsolicited `66 07 00 00...` on power-off; `CMDHSCloud2CoreWirelessGetMicBoomPlugState`) | **Verified** (Read & Event, 2026-11-17) |
| **Noise gate** | `0x8D` (`141`) | `0x0F` (`15`) | `0x0F` (`15`) | `66 8d 01 00...` (`buf[2] = 0x01` active when headset is on; `0x00` when headset is off; emits unsolicited `66 0f 00 00...` on power-off; `CMDHSCloud2CoreWirelessGetNoiseGateState` / `SetNoiseGateState`) | **Verified** (Read & Event, 2026-11-17) / **Inferred** (Set) |
| **Product color** | `0x8F` (`143`) | — | — | `66 8f 02 00...` (`buf[2] = 0x02` = Black/Red; `0` = Black/Black, `1` = White/White; **returns `0x02` on `03f0:05b7` even when the headset is powered off**; `CMDHSCloud3WirelessGetColor`) | **Verified** (Read, On & Off, 2026-11-17) |

### 4.3 Verified Live Event Stream (`listen_events.py` on `/dev/hidraw1`)

Passively monitoring `/dev/hidraw1` (`03f0:05b7`) with [`re-scripts/listen_events.py`](re-scripts/listen_events.py) (**Verified**, 2026-11-17) confirms the following live wire behavior:
1. **Consumer Control Volume Wheel (`Report ID 0x0C`, 2 bytes)**:
   - Each upward detent emits two pairs of press/release reports spaced exactly `4.0 ms` apart (`bInterval = 4` ms): `0c 01` (`Volume Increment 0xE9`) → `+4 ms` → `0c 00` (`Release`) → `+4 ms` → `0c 01` → `+4 ms` → `0c 00`.
   - Each downward detent emits two pairs of `0c 02` (`Volume Decrement 0xEA`) → `+4 ms` → `0c 00` (`Release`).
2. **Physical Mic Mute Button (`Report ID 0x66`, Event `0x0A`, 62 bytes)**:
   - Pressing the left-earcup mute button emits `66 0a 01 01 00...` (`mic_muted = True`, `byte[3] = 0x01`); pressing it again emits `66 0a 00 01 00...` (`mic_muted = False`, `byte[3] = 0x01`).
3. **Headset Power-Off 6-Packet Disconnect Burst (`Report ID 0x66`, 62 bytes × 6)**:
   - When the headset powers off, the `03f0:05b7` receiver emits a deterministic 6-report burst spaced `4.0 ms` apart (`20 ms` total):
     1. `+0 ms`: `66 0b 00 00...` (`0x0B` `EVENT_WIRELESS_STATUS` → `wireless_connected = False`)
     2. `+4 ms`: `66 02 00 00...` (`0x02` `EVENT_AUTO_SHUTDOWN` → `auto_shutdown = 0 min`)
     3. `+8 ms`: `66 0d 00 00...` (`0x0D` `EVENT_BATTERY` → `battery = 0%`)
     4. `+12 ms`: `66 08 01 00...` (`0x08` `EVENT_SILENT_MODE / PLAYBACK_MUTE` → `silent_mode = True`)
     5. `+16 ms`: `66 07 00 00...` (`0x07` `EVENT_MIC_CONNECTED` → `mic_connected = False`)
     6. `+20 ms`: `66 0f 00 00...` (`0x0F` `EVENT_NOISE_GATE` → `noise_gate_on = False`)

### 4.4 Headset-Off Receiver Shadow-Table Behavior (`03f0:05b7`)

When the wireless headset is powered off and unplugged from USB-C, querying `/dev/hidraw1` (`03f0:05b7`) with [`re-scripts/query_status.py`](re-scripts/query_status.py) does **not** time out (**Verified**, 2026-11-17):
- The receiver answers all 13 `0x66 0x81..0x8F` queries in `3.9`–`5.3 ms` from a local RAM table.
- Queries `0x81` through `0x8D` (`GET_DEVICE_IDENTITY`, `GET_WIRELESS_STATUS`, `GET_SIRK`, `GET_SIDETONE_ON`, `GET_AUTO_SHUTDOWN`, `GET_MIC_MUTE`, `GET_SILENT_MODE`, `GET_SIDETONE_VOLUME`, `GET_BATTERY`, `GET_CHARGING`, `GET_MIC_CONNECTED`, `GET_NOISE_GATE`) all return zeroed payloads (`0x00`).
- Query **`0x8F` (`GET_PRODUCT_COLOR`) still returns `66 8f 02 00...` (`0x02` = Black/Red)**, proving that the product color code is stored persistently in the receiver's own NVDM flash (or initialized locally at receiver boot) rather than fetched live from the headset.
- Passively monitoring `/dev/hidraw1` with [`re-scripts/listen_events.py`](re-scripts/listen_events.py) confirms that the receiver emits **zero background noise packets** while idle (`0` unsolicited reports over `4.0 s`); input reports on `EP 4 IN` (`0x84`) are strictly event-driven.

### 4.5 Purpose of Report IDs `0x06`, `0x07`, `0x0A`, and `0x0B` on `0xFF13:0x0001` (Airoha RACE over USB HID)

Inspection of `NGenuity2Helper.exe` (`Cloud3WirelessUpdater.cs`) and `AirohaHidCoreLib.dll` from `HyperX_NGENUITY_Installer_2.38.0.0.exe` (**Verified**, 2026-11-17; see [`firmware-updater.md`](firmware-updater.md)) settles the role of the four additional vendor report declarations in the 73-byte `0xFF13:0x0001` collection:
- **Report ID `0x06` (61 B Output, 62 B wire) & Report ID `0x07` (61 B Input, 62 B wire)**: Local **Airoha RACE (Remote Access Command Engine) over USB HID** command/response channel used by `AirohaHidCoreLib.dll` (`[UsbHidPhy]`) to query FOTA state, erase/program SPI flash partitions, verify SHA-256 digests, and commit firmware updates on `03f0:05b7`/`03f0:0c9d` and `03f0:06b7`/`03f0:0e9d`.
- **Report ID `0x0A` (61 B Output, 62 B wire) & Report ID `0x0B` (2 B Input, 3 B wire)**: Secondary Airoha RACE dongle-relay / notification channel (`check dongle relay HID recipient`).

# HyperX Cloud III Wireless — Hardware & Regulatory Notes

Findings use the evidence labels defined in [`CONTRIBUTING.md`](../../CONTRIBUTING.md#evidence-rules).

---

## 1. Regulatory Filings (FCC Grants)

The HyperX Cloud III Wireless system is split across two FCC equipment authorizations granted to **HP Inc.** (Grantee Code `B94`) on `2023-04-07`:

| Component | Marketing / Model Code | FCC ID | Frequency Band | Equipment Class | Conducted Output Power | Evidence | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Wireless Headset | `CL007` | `B94-CL007` | `2402`–`2480 MHz` | DTS / DSS (2.4 GHz proprietary transceiver) | `0.014 W` (`~11.46 dBm`), head SAR `< 0.10 W/kg` (0 mm) | **Verified** | FCC grant `B94-CL007` (<https://fccid.io/B94-CL007>) |
| 2.4 GHz USB-C Receiver | `CL007WA` | `B94-CL007WA` | `2402`–`2480 MHz` | DTS (Digital Transmission System) | `0.014`–`0.015 W` (`~11.46`–`11.76 dBm`), body SAR `0.20 W/kg` (5 mm) | **Verified** | FCC grant `B94-CL007WA` (<https://fccid.io/B94-CL007WA>) |

---

## 2. Physical Controls & On-Device Shortcuts

| Control | Location | Function | Evidence | Source |
| :--- | :--- | :--- | :--- | :--- |
| Power button | Left earcup | Press and hold to power on/off; short press announcements/status | **Verified** | HyperX Cloud III Wireless user manual |
| Mic Mute / Sidetone button | Left earcup | Short press toggles microphone mute (and Mute LED); **press and hold for 3 seconds** toggles microphone monitoring (sidetone) locally in firmware without host software | **Verified** | HyperX Cloud III Wireless user manual |
| Volume wheel | Right earcup | Endless rotary encoder; emits Consumer Control (`0x0C:0x01`, Report ID `0x0C`) Volume Increment (`0c 01` → `0c 00` every 4 ms) / Decrement (`0c 02` → `0c 00` every 4 ms) reports to the host | **Verified** | Live capture via `re-scripts/listen_events.py` on `/dev/hidraw1`, 2026-11-17 |
| USB-C port | Left earcup | Battery charging and wired firmware update connection | **Verified** | HyperX Cloud III Wireless user manual |

---

## 3. Internal Architecture & Verified SoC / Flash Specifications

| Item | Component | Status / Details | Evidence | Source / What settles it |
| :--- | :--- | :--- | :--- | :--- |
| Main wireless audio SoC / MCU | Headset (`CL007`, `03f0:06b7` / `03f0:0e9d` / `03f0:08b7`) | **Airoha (MediaTek) AB1565** Ultra-Low-Latency 2.0 (`ULL2`) Dual-Mode Wireless Audio SoC (`AB1565_Headset` on `headset_ref_design`; integrates ARM Cortex-M4F application MCU, Cadence Tensilica HiFi Mini Audio DSP, 2.4 GHz BT 5.3 / ULL 2.0 radio, USB 2.0 FS controller, audio codec, and Li-Po charger) | **Verified** | `TLV 0x0020` (`"AB1565_Headset"`) & `TLV 0x0021` (`"headset_ref_design"`) in `03F006B7.bin` (`v3.1.0.9`), 2026-11-17 (see [`firmware-updater.md`](firmware-updater.md)) |
| USB receiver SoC / MCU | Receiver (`CL007WA`, `03f0:05b7` / `03f0:0c9d`) | **Airoha (MediaTek) AB1565** Ultra-Low-Latency 2.0 (`ULL2`) Dongle SoC (`AB1565_ULL2_DONGLE` on `dongle_ref_design`; same AB1565 silicon family running the ULL 2.0 USB Audio Class 1.0 + HID dongle stack) | **Verified** | `TLV 0x0020` (`"AB1565_ULL2_DONGLE"`) & `TLV 0x0021` (`"dongle_ref_design"`) in `03F005B7.bin` (`v4.1.0.9`), 2026-11-17 (see [`firmware-updater.md`](firmware-updater.md)) |
| Flash memory & layout | Headset & Receiver | • **Receiver (`03F005B7.bin`)**: 3 FOTA partitions written to `0x00013000..0x000AC000` (`612 KB`), `0x000E2000..0x00216000` (`1,232 KB`), and `0x0023E000..0x0024C000` (`56 KB`) → requires **>= 4 MB (`32 Mbit`) SPI NOR flash**<br>• **Headset (`03F006B7.bin`)**: 4 FOTA partitions written up to `0x0040B000..0x004A1000` (`600 KB` ROFS voice prompts) → requires **>= 8 MB (`64 Mbit`) SPI NOR flash** | **Verified** (partition offsets/sizes) / **Inferred** (4 MB & 8 MB flash capacities) | `TLV 0x0012` & `TLV 0x0014` in `03F005B7.bin` and `03F006B7.bin`, 2026-11-17 (see [`firmware-updater.md`](firmware-updater.md)) |
| Debug / ISP pads | Headset & Receiver | **Unknown** (Airoha AB1565 provides UART0/1WIRE debug/RACE and SWD pads on PCB) | **Unknown** | Physical PCB inspection |

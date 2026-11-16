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
| Volume wheel | Right earcup | Endless rotary encoder; emits Consumer Control (`0x0C:0x01`, Report ID `0x0C`) Volume Increment (`0xE9`) / Decrement (`0xEA`) reports to the host | **Inferred** | Manual + verified Report ID `0x0C` descriptor usages `0xE9`/`0xEA` |
| USB-C port | Left earcup | Battery charging and wired firmware update connection | **Verified** | HyperX Cloud III Wireless user manual |

---

## 3. Internal Architecture & Open Hardware Items

| Item | Component | Status / Details | Evidence | What settles it |
| :--- | :--- | :--- | :--- | :--- |
| Main wireless audio SoC / MCU | Headset (`CL007`) | **Unknown** (main audio processing PCB + secondary button/wheel control board + plug-in Li-Po battery reported in community teardowns) | **Unknown** | Read package markings from the `B94-CL007` FCC internal photos exhibit or a non-destructive earcup teardown |
| USB receiver SoC / MCU | Receiver (`CL007WA`, `03f0:05b7`) | **Unknown** (integrates Full-Speed USB 2.0 device controller, USB Audio Class 1.0 streaming engine, HID endpoint `0x84`, and 2.4 GHz GFSK/DTS radio) | **Unknown** | Read package markings from the `B94-CL007WA` FCC internal photos exhibit or a dongle teardown |
| Flash memory & layout | Headset & Receiver | **Unknown** (internal MCU flash vs. external SPI NOR flash, bootloader offset, pairing key sector, and acoustic calibration sector) | **Unknown** | Unpack the NGENUITY firmware update payload (Step 3) and inspect PCB flash IC markings |
| Debug / ISP pads | Headset & Receiver | **Unknown** | **Unknown** | Inspect PCB test points in internal photos and perform passive unpowered continuity checks |

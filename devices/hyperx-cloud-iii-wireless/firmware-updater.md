# HyperX Cloud III Wireless — Firmware Images & Airoha FOTA Updater Protocol

Findings use the evidence labels defined in [`CONTRIBUTING.md`](../../CONTRIBUTING.md#evidence-rules).

---

## 1. Official Vendor Installer & Firmware Images

All binaries below were extracted read-only from the official HyperX NGENUITY installer (`HyperX_NGENUITY_Installer_2.38.0.0.exe`, `435,177,264` bytes, `Last-Modified: Mon, 22 Jun 2026 06:46:08 GMT`, URL: `https://files.hyperx.com/software-installers/Ngenuity_Installer/HyperX_NGENUITY_Installer_2.38.0.0.exe`), which embeds an uncompressed `.msixbundle` at file offset `0x008FA238` (`9,413,176`) and `Setup_2.38.0.0_x64.msix` at file offset `0x00A79A67` (`10,984,039`) (**Verified**, 2026-11-17):

| Archive Path in `Setup_2.38.0.0_x64.msix` | Uncompressed Size | SHA-256 | Target USB `VID:PID` | Target SoC (`0x0020`) & Board (`0x0021`) | Firmware Version (`0x0013`) | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Assets/Firmware/03F005B7.bin` | `1,210,352` B (`0x1277F0`) | `21f092b1d8d54675ff38964801a189a2146dcc034f7a711a3ac98662b75ec1d0` | `03f0:05b7` (2.4 GHz USB Receiver, Rev B) | `AB1565_ULL2_DONGLE` / `dongle_ref_design` | `v4.1.0.9` (matches live `bcdDevice = 0x4109`) | **Verified** |
| `Assets/Firmware/03F00C9D.bin` | `1,210,352` B (`0x1277F0`) | `21f092b1d8d54675ff38964801a189a2146dcc034f7a711a3ac98662b75ec1d0` | `03f0:0c9d` (2.4 GHz USB Receiver, Rev A) | `AB1565_ULL2_DONGLE` / `dongle_ref_design` | `v4.1.0.9` (**byte-for-byte identical** to `03F005B7.bin`) | **Verified** |
| `Assets/Firmware/03F006B7.bin` | `1,824,336` B (`0x1BD650`) | `17ee8f1369f47ddded1bf916ac89d35ac30d2612828203d65fee11d9b6cd3324` | `03f0:06b7` (Wired USB-C Headset, Rev B) | `AB1565_Headset` / `headset_ref_design` | `v3.1.0.9` (matches live `bcdDevice = 0x3109` & `0x66 0x81`) | **Verified** |
| `Assets/Firmware/03F00E9D.bin` | `1,824,336` B (`0x1BD650`) | `17ee8f1369f47ddded1bf916ac89d35ac30d2612828203d65fee11d9b6cd3324` | `03f0:0e9d` (Wired USB-C Headset, Rev A) | `AB1565_Headset` / `headset_ref_design` | `v3.1.0.9` (**byte-for-byte identical** to `03F006B7.bin`) | **Verified** |
| `Assets/Native/AirohaHidCoreLib.dll` | `787,760` B | `6a32a8de5439aad64cc25eefc81084510fe7f9b1ef1d89d8cc4ad32409475419` | Host x64 updater library | Airoha USB HID RACE & FOTA engine | — | **Verified** |
| `Assets/Native/NGenuity2Helper.exe` | `2,883,376` B | `2d6bc3c58a37afc0b0fb537dd3b8eb9cd7d493b5c850de36b56bd580fad711b8` | Host .NET updater (`Cloud3WirelessUpdater.cs`) | Orchestrates `03F005B7.bin` / `03F006B7.bin` DFU | — | **Verified** |

### Key Identity Proof: Rev A (`0c9d`/`0e9d`) vs. Rev B (`05b7`/`06b7`) and `03f0:08b7`

1. **Identical Firmware Images Across PID Revisions**: `03F005B7.bin` and `03F00C9D.bin` have the exact same SHA-256 (`21f092b1d8d5...`), and `03F006B7.bin` and `03F00E9D.bin` have the exact same SHA-256 (`17ee8f1369f4...`). Both hardware PID pairs run the exact same Airoha AB1565 firmware builds (`v4.1.0.9` on the dongle, `v3.1.0.9` on the headset), with the USB PID stored in an unupdated NVDM (Non-Volatile Data Management) flash partition (**Verified**, 2026-11-17).
2. **Meaning of `03f0:08b7` in `0x66 0x81`**: In `NGenuity2Helper.exe` (`Cloud3WirelessUpdater.cs`), `VID_03F0&PID_08B7` (`HID#VID_03F0&PID_08B7&MI_03&Col03`) is labeled **`"Cloud 3 Wireless Atlas headset"`** — the internal wireless child PID reported by the `03f0:05b7` receiver in `0x66 0x81` (`resp[2..4] = b7 08`) when the headset is wirelessly linked (**Verified**, 2026-11-17).

---

## 2. Airoha AB1565 FOTA Package Format (`0x0000..0x1000`)

Both `03F005B7.bin` (`1,210,352` B) and `03F006B7.bin` (`1,824,336` B) use the standard **Airoha FOTA (Firmware Over-The-Air / USB HID) v2 Package Container** with a 4,096-byte (`0x1000`) header followed by an AES-encrypted LZMA payload stream (`0x1000..end`). You can parse and verify any image offline with [`re-scripts/inspect_fota_package.py`](re-scripts/inspect_fota_package.py) (**Verified**, 2026-11-17).

### 2.1 Header Layout (`0x0000..0x0FFF`)

| Offset | Size | Field | Description | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| `0x0000` | `32` B | `package_sha256` | Raw 32-byte SHA-256 digest computed over `data[0x0100..file_end]`.<br>• `03F005B7.bin`: `b0bc3fd620e921beb0cc30e2081c4e0e28b888c42bdb16f212ee26f2b9c30e68`<br>• `03F006B7.bin`: `f0b2ac3ff64be12078e4204f7c99d1d81a379c3558c64cd75754999a49155b7b` | **Verified** |
| `0x0020` | `224` B | `reserved_ff` | `0xFF` padding up to `0x0100`. | **Verified** |
| `0x0100` | Variable | `tlv_stream` | Sequence of little-endian TLV records (`uint16 tag`, `uint16 length`, `uint8 value[length]`), terminated by `tag = 0xFFFF` and padded with `0xFF` to `0x1000`. | **Verified** |
| `0x1000` | `fota_length` | `fota_payload` | Compressed/encrypted partition stream (`1,206,256` B in `03F005B7.bin`; `1,820,240` B in `03F006B7.bin`). | **Verified** |

### 2.2 Header TLV Records (`0x0100..0x0220`)

| TLV Tag (LE) | Length | Name | Structure & Verified Values | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| `0x0011` | `10` B (`0x000A`) | `BASIC_INFO` | `uint8 compression_type` = `0x02` (LZMA)<br>`uint8 integrity_check_type` = `0x01` (SHA-256)<br>`uint32 LE fota_offset` = `0x00001000` (`4,096`)<br>`uint32 LE fota_length` = `0x001267F0` (`1,206,256` B on dongle) or `0x001BC650` (`1,820,240` B on headset) | **Verified** |
| `0x0013` | `28` B (`0x001C`) | `VERSION_INFO` | Null-terminated ASCII version string, padded with `0xFF` to 28 bytes:<br>• `03F005B7.bin`: `"v4.1.0.9"`<br>• `03F006B7.bin`: `"v3.1.0.9"` | **Verified** |
| `0x0012` | `4 + 12×N` B | `MOVER_INFO` (Partition Table) | `uint32 LE partition_count` (`3` on dongle, `4` on headset), followed by `N` 12-byte records:<br>• `uint32 LE uncompressed_offset` (offset in decompressed staging stream, starting at `0x00001000`)<br>• `uint32 LE uncompressed_length` (decompressed partition size in bytes)<br>• `uint32 LE flash_target_offset` (destination offset in SPI NOR flash relative to flash base `0x08000000`) | **Verified** |
| `0x0014` | `4 + 32×N` B | `INTEGRITY_INFO` | `uint32 LE partition_count` (`3` or `4`), followed by `N` 32-byte SHA-256 digests of the decompressed partitions. | **Verified** |
| `0x0020` | `14`–`18` B | `DEVICE_TYPE` | Target Airoha SoC / project identifier:<br>• `03F005B7.bin`: `"AB1565_ULL2_DONGLE"`<br>• `03F006B7.bin`: `"AB1565_Headset"` | **Verified** |
| `0x0021` | `17`–`18` B | `BOARD_NAME` | Reference design identifier:<br>• `03F005B7.bin`: `"dongle_ref_design"`<br>• `03F006B7.bin`: `"headset_ref_design"` | **Verified** |
| `0x00F0` | `1` B (`0x0001`) | `ENCRYPTION_FLAG` | `0x01` (FOTA payload stream at `0x1000` is encrypted before flash staging). | **Verified** |

### 2.3 SPI NOR Flash Partition Tables (`TLV 0x0012` & `TLV 0x0014`)

#### Receiver (`03F005B7.bin` / `03F00C9D.bin` — `AB1565_ULL2_DONGLE` `v4.1.0.9`, 3 Partitions)

Total uncompressed payload across all 3 updated partitions: **`1,945,600` bytes (`0x1DB000`)**, compressed into `1,206,256` bytes (`0x1267F0`) (**Verified**, 2026-11-17):

| Partition | Uncompressed Stream Offset | Uncompressed Size | Target SPI Flash Offset (`+0x08000000`) | Inferred Partition Role (Airoha AB1565 SDK Layout) | Uncompressed Partition SHA-256 (`TLV 0x0014`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0` | `0x00001000` | `0x00099000` (`626,688` B / `612 KB`) | `0x00013000..0x000AC000` | DSP0 / BT & ULL 2.0 Radio Controller Firmware (starts after 76 KB bootloader/partition table at `0x00000000..0x00013000`) | `f4784e8be416ac4eba6aa22e49fcebc61f2a08f346e0d805bbe4a8c1f18889be` |
| `1` | `0x0009A000` | `0x00134000` (`1,261,568` B / `1,232 KB`) | `0x000E2000..0x00216000` | ARM Cortex-M4F Application MCU Firmware (USB Audio Class 1.0 + HID `0xFF13` / RACE `0x06`/`0x07` stack) | `de217c4632d40ac364495f2390053c7978a5f0ddee1dc448c04326c13b1a4929` |
| `2` | `0x001CE000` | `0x0000E000` (`57,344` B / `56 KB`) | `0x0023E000..0x0024C000` | ROFS (Read-Only File System) / NVDM Default Parameter Table | `e485c00088b867d53e2158662049ee0bf712930824e70d95e25a783a76471e4b` |

> **Note on Preserved Flash Gaps**: Flash regions `0x00000000..0x00013000` (`76 KB` bootloader + partition table), `0x000AC000..0x000E2000` (`216 KB`), and `0x00216000..0x0023E000` (`160 KB`), along with upper NVDM sectors (`>= 0x0024C000`), are untouched by FOTA updates, preserving the factory USB PID (`05b7` vs `0c9d`), product color (`0x8F`), and paired headset SIRK/link key (**Inferred** from flash gaps and live `0x8F` persistence).

#### Headset (`03F006B7.bin` / `03F00E9D.bin` — `AB1565_Headset` `v3.1.0.9`, 4 Partitions)

Total uncompressed payload across all 4 updated partitions: **`2,965,504` bytes (`0x2D4000`)**, compressed into `1,820,240` bytes (`0x1BC650`) (**Verified**, 2026-11-17):

| Partition | Uncompressed Stream Offset | Uncompressed Size | Target SPI Flash Offset (`+0x08000000`) | Inferred Partition Role (Airoha AB1565 SDK Layout) | Uncompressed Partition SHA-256 (`TLV 0x0014`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0` | `0x00001000` | `0x000BF000` (`782,336` B / `764 KB`) | `0x00013000..0x000D2000` | DSP0 / BT 5.3 & ULL 2.0 Radio Controller Firmware | `1f0397f1637ec7926e82ab1f025b1ea91ae2f49ce1879bc30291b2b55b28667f` |
| `1` | `0x000C0000` | `0x0016B000` (`1,486,848` B / `1,452 KB`) | `0x00133000..0x0029E000` | ARM Cortex-M4F Application MCU + HiFi Mini DSP Firmware | `45644aa1caaa335d24acc587c8f8968260671bb7388d32b53c0e7f71cae66b2b` |
| `2` | `0x0022B000` | `0x00014000` (`81,920` B / `80 KB`) | `0x0032C000..0x00340000` | NVDM Default Parameter / Acoustic EQ & Sidetone Table | `7d1b951e28768fd86b547f65c596aa3ae8f29415a6368d4a5650522e11845a57` |
| `3` | `0x0023F000` | `0x00096000` (`614,400` B / `600 KB`) | `0x0040B000..0x004A1000` | ROFS (Voice Prompts: `"Power On"`, `"Power Off"`, `"Battery High/Medium/Low"`, `"Mic On/Muted"`, `"Connected"`) | `54e649fce77e8607db5912a7dfb2b4166665e30516e3b18b966a4be18850f35b` |

Because Partition 3 writes up to flash offset `0x004A1000` (`4.63 MB`), the headset board (`B94-CL007`) must carry at least an **8 MB (`64 Mbit`, `0x00800000`) SPI NOR flash**, whereas the receiver (`B94-CL007WA`, writing up to `0x0024C000` = `2.30 MB`) requires at least a **4 MB (`32 Mbit`, `0x00400000`) SPI NOR flash** (**Inferred** from verified partition addresses).

---

## 3. Airoha RACE over USB HID Update Protocol (`Report IDs 0x06 / 0x07 / 0x0A / 0x0B`)

Inspection of `NGenuity2Helper.exe` (`Cloud3WirelessUpdater.cs`) and `AirohaHidCoreLib.dll` (**Verified**, 2026-11-17) settles the purpose of the extra vendor reports (`0x06` Out, `0x07` In, `0x0A` Out, `0x0B` In) in the 73-byte `0xFF13:0x0001` HID descriptor:

1. **No Separate USB Bootloader PID**: Neither the `03f0:05b7` receiver nor the `03f0:06b7` wired USB-C headset re-enumerates to a separate DFU USB PID during firmware updates. Instead, `Cloud3WirelessUpdater.cs` opens the normal application HID interface directly:
   - Receiver (`03f0:05b7` or `03f0:0c9d`): `HID#VID_03F0&PID_05B7&MI_03&Col01` / `HID#VID_03F0&PID_0C9D&MI_03&Col01`
   - Wired USB-C Headset (`03f0:06b7` or `03f0:0e9d`): `HID#VID_03F0&PID_06B7` / `HID#VID_03F0&PID_0E9D`
2. **HID Transport (`HidD_SetOutputReport` / `ReadFile`)**:
   - `AirohaHidCoreLib.dll` (`[UsbHidPhy]`) sends **Airoha RACE (Remote Access Command Engine)** packets wrapped in 62-byte USB HID Output reports (`Report ID 0x06` for local device commands; `Report ID 0x0A` for dongle-relayed commands) and reads 62-byte Input reports (`Report ID 0x07` / `0x0B`).
   - Standard Airoha RACE frames begin with channel byte `0x05`, RACE type (`0x5A` command expecting response, `0x5B` response, `0x5C` command without response, `0x5D` indication), `uint16 LE length` (`>= 2`), and `uint16 LE race_cmd_id`.
3. **Updater State Machine (`Cloud3WirelessUpdater.cs` → `AirohaHidCoreLib.dll`)**:
   - `initialize(vid, pid)` → opens `[UsbHidPhy]` on the target device (`03f0:05b7` for dongle update with `03F005B7.bin`, then `03f0:06b7` for wired headset update with `03F006B7.bin`).
   - `requestDFUInfo()` → sends `RaceGetAgentClientVersion` / `RaceFotaInquiry` (`QUERY_SINGLE_FOTA_INFO`) to compare the running firmware version against `TLV 0x0013` in the `.bin` file.
   - `startDataTransfer()` → executes `ProgramDiffFotaStorageTask`:
     1. `RaceFotaStart` (`START_FOTA`) & `RaceFotaQueryState` (`QUERY_FOTA_STATE`)
     2. `RaceGetStoragePartitionSHA256` & `RaceStorageGetPartitionErasedStatus` (skips already-matching 4 KB flash sectors)
     3. `RaceDiffFlashPartitionEraseStorage` & `RaceStoragePageProgram` (streams the FOTA staging payload into the AB1565 FOTA staging partition while `FotaPingTask` sends periodic `RaceFotaPing` keepalives)
     4. `RaceCheckIntegrity` (verifies staging SHA-256 on-chip)
   - `applyNewFirmware()` → sends `RaceCommit` (`RaceMcuFwCommit`), causing the AB1565 ROM/bootloader ("FOTA mover") to reboot, decrypt and LZMA-decompress the staged FOTA stream into the target flash addresses (`TLV 0x0012`), verify the uncompressed partition SHA-256 digests (`TLV 0x0014`), and boot the new firmware.
   - `close()` → closes the HID handle.

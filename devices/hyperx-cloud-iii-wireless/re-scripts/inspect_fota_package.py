#!/usr/bin/env python3
"""Parse and verify Airoha AB1565 FOTA firmware package headers (.bin).

Supports the Airoha FOTA package format used by HyperX Cloud III Wireless
(03F005B7.bin, 03F006B7.bin, 03F00C9D.bin, 03F00E9D.bin):
  - 0x0000..0x001F (32 B): SHA-256 digest over data[0x0100..end]
  - 0x0020..0x00FF (224 B): 0xFF padding
  - 0x0100..0x0FFF: Little-endian TLV stream (uint16 tag, uint16 len, value)
    terminated by 0xFFFF:
      * 0x0011: BasicInfo (compression_type, integrity_type, fota_offset, fota_length)
      * 0x0013: Version string (null-terminated ASCII, 0xFF-padded to 28 B)
      * 0x0012: Partition / Mover Table (uint32 count + count * (src_off, uncomp_len, flash_dst))
      * 0x0014: Per-partition SHA-256 table (uint32 count + count * 32-byte SHA-256)
      * 0x0020: SoC / Target Name (e.g., "AB1565_ULL2_DONGLE", "AB1565_Headset")
      * 0x0021: Reference Design Name (e.g., "dongle_ref_design", "headset_ref_design")
      * 0x00F0: Payload encryption flag (0x01 = AES-encrypted LZMA payload at 0x1000)
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path


COMPRESSION_NAMES: dict[int, str] = {
    0x00: "None (0x00)",
    0x01: "LZMA-Plain (0x01)",
    0x02: "LZMA (0x02)",
}

INTEGRITY_NAMES: dict[int, str] = {
    0x00: "CRC32 (0x00)",
    0x01: "SHA-256 (0x01)",
    0x02: "SHA-256 + ECDSA (0x02)",
}


@dataclass(frozen=True)
class FotaPartitionEntry:
    index: int
    uncompressed_offset: int
    uncompressed_length: int
    flash_target_offset: int
    sha256_hex: str = ""


@dataclass
class FotaPackageMetadata:
    file_size: int
    file_sha256: str
    header_sha256: str
    computed_body_sha256: str
    header_sha256_valid: bool
    compression_type: int = 0
    integrity_type: int = 0
    fota_offset: int = 0
    fota_length: int = 0
    version: str = ""
    device_name: str = ""
    board_name: str = ""
    encryption_flag: int = 0
    partitions: list[FotaPartitionEntry] = field(default_factory=list)


def parse_fota_package(data: bytes) -> FotaPackageMetadata:
    """Parse an Airoha FOTA firmware binary image and verify its header SHA-256."""
    if len(data) < 0x0200:
        raise ValueError(f"Data too short for Airoha FOTA header ({len(data)} B < 512 B)")

    file_sha256 = hashlib.sha256(data).hexdigest()
    header_sha256 = data[0x0000:0x0020].hex()
    computed_body_sha256 = hashlib.sha256(data[0x0100:]).hexdigest()
    meta = FotaPackageMetadata(
        file_size=len(data),
        file_sha256=file_sha256,
        header_sha256=header_sha256,
        computed_body_sha256=computed_body_sha256,
        header_sha256_valid=(header_sha256 == computed_body_sha256),
    )

    pos = 0x0100
    tlv_end = min(len(data), 0x1000)
    raw_parts: list[tuple[int, int, int]] = []
    part_hashes: list[str] = []

    while pos + 4 <= tlv_end:
        tag, length = struct.unpack_from("<HH", data, pos)
        if tag == 0xFFFF:
            break
        if pos + 4 + length > tlv_end:
            raise ValueError(f"TLV 0x{tag:04X} at 0x{pos:04X} exceeds header boundary (len={length})")
        val = data[pos + 4 : pos + 4 + length]
        if tag == 0x0011 and len(val) >= 10:
            comp_type, integ_type, f_off, f_len = struct.unpack_from("<BBII", val, 0)
            meta.compression_type = comp_type
            meta.integrity_type = integ_type
            meta.fota_offset = f_off
            meta.fota_length = f_len
        elif tag == 0x0013:
            meta.version = val.split(b"\x00", 1)[0].decode("ascii", "replace")
        elif tag == 0x0012 and len(val) >= 4:
            cnt, = struct.unpack_from("<I", val, 0)
            for i in range(cnt):
                if 4 + (i + 1) * 12 <= len(val):
                    u_off, u_len, dst = struct.unpack_from("<III", val, 4 + i * 12)
                    raw_parts.append((u_off, u_len, dst))
        elif tag == 0x0014 and len(val) >= 4:
            cnt, = struct.unpack_from("<I", val, 0)
            for i in range(cnt):
                if 4 + (i + 1) * 32 <= len(val):
                    part_hashes.append(val[4 + i * 32 : 4 + (i + 1) * 32].hex())
        elif tag == 0x0020:
            meta.device_name = val.split(b"\x00", 1)[0].decode("ascii", "replace")
        elif tag == 0x0021:
            meta.board_name = val.split(b"\x00", 1)[0].decode("ascii", "replace")
        elif tag == 0x00F0 and len(val) >= 1:
            meta.encryption_flag = val[0]
        pos += 4 + length

    for idx, (u_off, u_len, dst) in enumerate(raw_parts):
        h = part_hashes[idx] if idx < len(part_hashes) else ""
        meta.partitions.append(
            FotaPartitionEntry(
                index=idx,
                uncompressed_offset=u_off,
                uncompressed_length=u_len,
                flash_target_offset=dst,
                sha256_hex=h,
            )
        )

    return meta


def format_fota_metadata(name: str, meta: FotaPackageMetadata) -> str:
    """Format parsed FOTA metadata into a human-readable summary."""
    comp_name = COMPRESSION_NAMES.get(meta.compression_type, f"0x{meta.compression_type:02X}")
    integ_name = INTEGRITY_NAMES.get(meta.integrity_type, f"0x{meta.integrity_type:02X}")
    lines = [
        f"=== {name} ({meta.file_size:,d} bytes) ===",
        f"  File SHA-256:       {meta.file_sha256}",
        f"  Header [0x00..0x20]:{meta.header_sha256}",
        f"  SHA256(0x0100..end):{meta.computed_body_sha256} (valid={meta.header_sha256_valid})",
        f"  Target SoC (0x0020):{meta.device_name!r}",
        f"  Board Name (0x0021):{meta.board_name!r}",
        f"  FW Version (0x0013):{meta.version!r}",
        f"  BasicInfo  (0x0011):compression={comp_name}, integrity={integ_name}, "
        f"fota_offset=0x{meta.fota_offset:08X}, fota_length=0x{meta.fota_length:08X} ({meta.fota_length:,d} B)",
        f"  Encrypted  (0x00F0):0x{meta.encryption_flag:02X} ({bool(meta.encryption_flag)})",
        f"  Partitions (0x0012):{len(meta.partitions)}",
    ]
    for p in meta.partitions:
        lines.append(
            f"    [{p.index}] uncomp_off=0x{p.uncompressed_offset:08X} "
            f"uncomp_len=0x{p.uncompressed_length:08X} ({p.uncompressed_length:9,d} B) "
            f"-> flash_dst=0x{p.flash_target_offset:08X}..0x{p.flash_target_offset + p.uncompressed_length:08X} "
            f"| sha256={p.sha256_hex}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="Airoha FOTA .bin file(s) to inspect")
    args = parser.parse_args()

    for path in args.files:
        data = path.read_bytes()
        meta = parse_fota_package(data)
        print(format_fota_metadata(str(path), meta))
    return 0


if __name__ == "__main__":
    sys.exit(main())

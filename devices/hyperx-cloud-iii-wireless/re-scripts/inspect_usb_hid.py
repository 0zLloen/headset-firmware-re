#!/usr/bin/env python3
"""Passive USB/HID descriptor inspector for the HyperX Cloud III Wireless (03f0:05b7 & 03f0:06b7).

Safety guarantees:
- `--offline` and `--descriptor-file` operate purely on bytes in memory.
- `--sysfs` only reads kernel-cached files under `/sys/bus/usb/devices`,
  `/sys/class/hidraw`, and `/proc/asound`. It never opens `/dev/hidraw*` or
  `/dev/bus/usb/*`, never sends any USB/HID transfer, and skips serial numbers
  (`serial`, `HID_UNIQ`).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import glob
import hashlib
from pathlib import Path
import sys
from typing import List, Optional


VID = "03f0"
RECEIVER_PID = "05b7"
HEADSET_PID = "06b7"
KNOWN_PIDS = (RECEIVER_PID, HEADSET_PID)

# Verified 187-byte HID report descriptor read from interface 3 of a retail
# 03f0:05b7 receiver (bcdDevice 0x4109) on 2026-11-16.
VERIFIED_RECEIVER_DESCRIPTOR_HEX = (
    "0613ff0901a101150026ff00850609007508953d9102850709007508953d8102"
    "850a09007508953d9122850b0900750895028102856609007508953d91228566"
    "09007508953d8102c0050c0901a101850c1500250109e909ea09e209cd09b509"
    "b6750195068102090095028102c0050b0905a101150025017501850509209501"
    "8122092f95018106092409210997092a09509505810609070509090175019501"
    "81020508850509170909091809200921092a9506912295029101c0"
)
VERIFIED_RECEIVER_DESCRIPTOR_SHA256 = (
    "ddd28140e5b7628282ef2a2f66d955f8e40f371b48d3f5a19e5599593e6729bf"
)

# Verified 150-byte HID report descriptor read from interface 0 of a retail
# 03f0:06b7 wired USB-C headset (bcdDevice 0x3109) on 2026-11-16.
VERIFIED_HEADSET_DESCRIPTOR_HEX = (
    "0613ff0901a101150026ff00850609007508953d9102850709007508953d8102"
    "850a09007508953d9122850b0900750895028102856609007508953d91228566"
    "09007508953d8102c0050b0905a1011500250175018505092095018122092f95"
    "018106092409210997092a095095058106090705090901750195018102050885"
    "0509170909091809200921092a9506912295029101c0"
)
VERIFIED_HEADSET_DESCRIPTOR_SHA256 = (
    "d8869a8f6ff66fca2cfa0e9e8ad13f68adb76032b8898677c118991ab7a46e1c"
)

KNOWN_DESCRIPTOR_HASHES = {
    VERIFIED_RECEIVER_DESCRIPTOR_SHA256: "03f0:05b7 receiver (187 B)",
    VERIFIED_HEADSET_DESCRIPTOR_SHA256: "03f0:06b7 wired headset (150 B)",
}


@dataclass
class ReportFieldSlice:
    report_id: int
    direction: str  # "Input" | "Output" | "Feature"
    usage_page: int
    usages: List[int]
    report_size_bits: int
    report_count: int
    flags: int

    @property
    def total_bits(self) -> int:
        return self.report_size_bits * self.report_count


@dataclass
class ReportSummary:
    collection_usage_page: int
    collection_usage: int
    report_id: int
    direction: str
    total_bits: int
    flags_list: List[int] = field(default_factory=list)

    @property
    def payload_bytes(self) -> int:
        assert self.total_bits % 8 == 0, f"Non-byte-aligned report: {self.total_bits} bits"
        return self.total_bits // 8

    @property
    def wire_bytes_with_report_id(self) -> int:
        return (1 if self.report_id > 0 else 0) + self.payload_bytes


@dataclass
class TopLevelCollection:
    usage_page: int
    usage: int
    collection_type: int
    start_offset: int
    end_offset: int = 0
    slices: List[ReportFieldSlice] = field(default_factory=list)

    def summarize_reports(self) -> List[ReportSummary]:
        by_key: dict[tuple[int, str], ReportSummary] = {}
        order: List[tuple[int, str]] = []
        for s in self.slices:
            key = (s.report_id, s.direction)
            if key not in by_key:
                by_key[key] = ReportSummary(
                    collection_usage_page=self.usage_page,
                    collection_usage=self.usage,
                    report_id=s.report_id,
                    direction=s.direction,
                    total_bits=0,
                )
                order.append(key)
            by_key[key].total_bits += s.total_bits
            by_key[key].flags_list.append(s.flags)
        return [by_key[k] for k in order]


def parse_hid_report_descriptor(data: bytes) -> List[TopLevelCollection]:
    """Parse a standard USB HID report descriptor into top-level collections."""
    collections: List[TopLevelCollection] = []
    current_top: Optional[TopLevelCollection] = None
    depth = 0
    block_start_offset = 0

    usage_page = 0
    report_id = 0
    report_size = 0
    report_count = 0
    local_usages: List[int] = []

    i = 0
    while i < len(data):
        b = data[i]
        if b == 0xFE:
            # Long item
            if i + 2 >= len(data):
                raise ValueError(f"Truncated long HID item at offset {i}")
            data_size = data[i + 1]
            i += 3 + data_size
            continue

        size_code = b & 0x03
        size = 4 if size_code == 3 else size_code
        item_type = (b >> 2) & 0x03
        tag = (b >> 4) & 0x0F

        if i + 1 + size > len(data):
            raise ValueError(f"Truncated short HID item at offset {i}")

        val = int.from_bytes(data[i + 1 : i + 1 + size], "little")

        if item_type == 1:  # Global
            if tag == 0x0:
                usage_page = val
            elif tag == 0x7:
                report_size = val
            elif tag == 0x8:
                report_id = val
            elif tag == 0x9:
                report_count = val
        elif item_type == 2:  # Local
            if tag == 0x0:
                local_usages.append(val)
        elif item_type == 0:  # Main
            if tag == 0xA:  # Collection
                if depth == 0:
                    top_usage = local_usages[0] if local_usages else 0
                    current_top = TopLevelCollection(
                        usage_page=usage_page,
                        usage=top_usage,
                        collection_type=val,
                        start_offset=block_start_offset,
                    )
                depth += 1
                local_usages.clear()
            elif tag == 0xC:  # End Collection
                depth -= 1
                if depth < 0:
                    raise ValueError(f"Unmatched End Collection at offset {i}")
                if depth == 0 and current_top is not None:
                    current_top.end_offset = i
                    collections.append(current_top)
                    current_top = None
                    block_start_offset = i + 1 + size
                local_usages.clear()
            elif tag in (0x8, 0x9, 0xB):  # Input, Output, Feature
                direction = {0x8: "Input", 0x9: "Output", 0xB: "Feature"}[tag]
                if current_top is None:
                    raise ValueError(f"{direction} item outside collection at offset {i}")
                current_top.slices.append(
                    ReportFieldSlice(
                        report_id=report_id,
                        direction=direction,
                        usage_page=usage_page,
                        usages=list(local_usages),
                        report_size_bits=report_size,
                        report_count=report_count,
                        flags=val,
                    )
                )
                local_usages.clear()

        i += 1 + size

    if depth != 0:
        raise ValueError(f"Unclosed collection at end of descriptor (depth={depth})")

    return collections


def format_descriptor_report(data: bytes) -> str:
    sha = hashlib.sha256(data).hexdigest()
    matched = KNOWN_DESCRIPTOR_HASHES.get(sha, "None")
    collections = parse_hid_report_descriptor(data)
    lines = [
        f"Descriptor length : {len(data)} bytes",
        f"Descriptor SHA-256: {sha}",
        f"Verified match    : {matched}",
        f"Top-level colls   : {len(collections)}",
        "",
    ]
    for idx, coll in enumerate(collections, 1):
        lines.append(
            f"Collection {idx}: Usage Page 0x{coll.usage_page:04X}, "
            f"Usage 0x{coll.usage:04X} (offsets {coll.start_offset}..{coll.end_offset})"
        )
        for rep in coll.summarize_reports():
            flags_str = ", ".join(f"0x{f:02X}" for f in rep.flags_list)
            lines.append(
                f"  Report ID 0x{rep.report_id:02X} ({rep.report_id:3d}) | "
                f"{rep.direction:<7} | payload {rep.payload_bytes:2d} B "
                f"({rep.total_bits:3d} bits) | wire {rep.wire_bytes_with_report_id:2d} B | "
                f"flags [{flags_str}]"
            )
        lines.append("")
    return "\n".join(lines)


def inspect_sysfs() -> int:
    """Passively inspect 03f0:05b7 and 03f0:06b7 via Linux sysfs without touching /dev/hidraw*."""
    usb_matches: List[tuple[str, Path]] = []
    for dev_dir in sorted(Path("/sys/bus/usb/devices").glob("*")):
        vid_file = dev_dir / "idVendor"
        pid_file = dev_dir / "idProduct"
        if not (vid_file.is_file() and pid_file.is_file()):
            continue
        vid = vid_file.read_text(encoding="utf-8", errors="replace").strip().lower()
        pid = pid_file.read_text(encoding="utf-8", errors="replace").strip().lower()
        if vid == VID and pid in KNOWN_PIDS:
            usb_matches.append((pid, dev_dir))

    if not usb_matches:
        print(
            f"No USB device {VID}:{{{'|'.join(KNOWN_PIDS)}}} found under /sys/bus/usb/devices.",
            file=sys.stderr,
        )
        return 1

    for pid, dev_dir in usb_matches:
        print(f"=== USB Device: {dev_dir} ({VID}:{pid}) ===")
        for attr in (
            "manufacturer",
            "product",
            "bcdDevice",
            "version",
            "speed",
            "bmAttributes",
            "bMaxPower",
            "bNumInterfaces",
        ):
            p = dev_dir / attr
            if p.is_file():
                print(f"  {attr:<16}: {p.read_text(encoding='utf-8', errors='replace').strip()}")
        print("  iSerial         : <redacted>")
        print()

    target_hid_ids = {f"0003:0000{VID.upper()}:0000{p.upper()}" for p in KNOWN_PIDS}
    for hidraw_str in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        hidraw_path = Path(hidraw_str)
        uevent_file = hidraw_path / "device" / "uevent"
        if not uevent_file.is_file():
            continue
        uevent = uevent_file.read_text(encoding="utf-8", errors="replace")
        if not any(f"HID_ID={hid_id}" in uevent.upper() for hid_id in target_hid_ids):
            continue
        desc_file = hidraw_path / "device" / "report_descriptor"
        data = desc_file.read_bytes()
        print(f"=== HID Node: {hidraw_path.name} ===")
        for line in uevent.splitlines():
            if line.startswith("HID_UNIQ="):
                print("  HID_UNIQ=<redacted>")
            else:
                print(f"  {line}")
        print()
        print(format_descriptor_report(data))

    for card_dir in sorted(Path("/proc/asound").glob("card*")):
        usbid_file = card_dir / "usbid"
        if not usbid_file.is_file():
            continue
        usbid = usbid_file.read_text(encoding="utf-8", errors="replace").strip().lower()
        if usbid in {f"{VID}:{p}" for p in KNOWN_PIDS}:
            print(f"=== ALSA Sound Card: {card_dir.name} ({usbid}) ===")
            for sub in ("stream0", "usbmixer"):
                sub_file = card_dir / sub
                if sub_file.is_file():
                    print(f"--- {sub_file} ---")
                    print(sub_file.read_text(encoding="utf-8", errors="replace").rstrip())
                    print()

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--offline",
        action="store_true",
        help="Decode the verified 03f0:05b7 (187 B) and 03f0:06b7 (150 B) HID report descriptors.",
    )
    group.add_argument(
        "--descriptor-file",
        type=Path,
        help="Decode a binary or hex HID report descriptor file offline.",
    )
    group.add_argument(
        "--sysfs",
        action="store_true",
        help="Passively read /sys/bus/usb/devices, /sys/class/hidraw, and /proc/asound for 03f0:05b7 and 03f0:06b7.",
    )
    args = parser.parse_args(argv)

    if args.offline:
        print("=== Receiver 03f0:05b7 (Interface 3) ===")
        print(format_descriptor_report(bytes.fromhex(VERIFIED_RECEIVER_DESCRIPTOR_HEX)))
        print("=== Wired Headset 03f0:06b7 (Interface 0) ===")
        print(format_descriptor_report(bytes.fromhex(VERIFIED_HEADSET_DESCRIPTOR_HEX)))
        return 0

    if args.descriptor_file:
        raw = args.descriptor_file.read_bytes()
        try:
            text = raw.decode("ascii").strip()
            data = bytes.fromhex("".join(text.split()))
        except (UnicodeDecodeError, ValueError):
            data = raw
        print(format_descriptor_report(data))
        return 0

    if args.sysfs:
        return inspect_sysfs()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

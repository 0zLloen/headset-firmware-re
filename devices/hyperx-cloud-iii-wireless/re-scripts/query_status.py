#!/usr/bin/env python3
"""Read-only Report ID 0x66 status probe for HyperX Cloud III Wireless (03f0:05b7 & 03f0:06b7).

Safety guarantees:
- Only read-only query opcodes (`cmd >= 0x80`, bit 7 set) are permitted.
  `build_query_packet()` raises `ValueError` for any opcode `< 0x80` (blocking all
  set commands `0x01..0x0F` and `0x1E` RESET_SIRK).
- For `0x83` (`GET_SIRK`), the 16-byte Set Identity Resolving Key / pairing key in
  `resp[2..18]` is redacted in all output (`<redacted>`).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import glob
import os
from pathlib import Path
import select
import sys
import time
from typing import Dict, List, Optional, Tuple


VID = "03f0"
RECEIVER_PID = "05b7"
HEADSET_PID = "06b7"

REPORT_ID_66 = 0x66
PACKET_LEN = 62  # 1-byte Report ID (0x66) + 61-byte payload

# Read-only query commands (bit 7 set, 0x80..0x8F) verified on 03f0:05b7 and 03f0:06b7.
READ_COMMANDS: List[Tuple[int, str]] = [
    (0x81, "GET_DEVICE_IDENTITY / HEADSET_FW (0x81)"),
    (0x82, "GET_WIRELESS_STATUS (0x82)"),
    (0x83, "GET_SIRK / PAIRING_KEY (0x83, redacted)"),
    (0x84, "GET_SIDETONE_ON (0x84)"),
    (0x85, "GET_AUTO_SHUTDOWN (0x85)"),
    (0x86, "GET_MIC_MUTE (0x86)"),
    (0x87, "GET_SILENT_MODE / PLAYBACK_MUTE (0x87)"),
    (0x88, "GET_SIDETONE_VOLUME (0x88)"),
    (0x89, "GET_BATTERY (0x89)"),
    (0x8A, "GET_CHARGING (0x8A)"),
    (0x8C, "GET_MIC_CONNECTED (0x8C)"),
    (0x8D, "GET_NOISE_GATE (0x8D)"),
    (0x8F, "GET_PRODUCT_COLOR (0x8F)"),
]

UNSOLICITED_EVENTS: Dict[int, str] = {
    0x07: "EVENT_MIC_CONNECTED (0x07)",
    0x09: "EVENT_SIDETONE_ON (0x09)",
    0x0A: "EVENT_MIC_MUTE (0x0A)",
    0x0B: "EVENT_WIRELESS_STATUS (0x0B)",
    0x0C: "EVENT_CHARGING (0x0C)",
    0x0D: "EVENT_BATTERY (0x0D)",
}

COLOR_NAMES: Dict[int, str] = {
    0: "Black/Black (0)",
    1: "White/White (1)",
    2: "Black/Red (2)",
}

CHARGING_NAMES: Dict[int, str] = {
    0: "NotCharging (0)",
    1: "Charging (1)",
    2: "FullyCharged (2)",
    3: "ChargeError (3)",
}


@dataclass
class Parsed66Response:
    report_id: int
    cmd_or_event: int
    summary: str
    redacted_hex: str


def build_query_packet(cmd: int) -> bytes:
    """Build a 62-byte Report ID 0x66 read-only query packet.

    Raises ValueError if `cmd < 0x80` so write/set commands can never be built.
    """
    if not (0x80 <= cmd <= 0xFF):
        raise ValueError(
            f"Refusing non-read-only command 0x{cmd:02X}: only 0x80..0xFF read queries are allowed"
        )
    buf = bytearray(PACKET_LEN)
    buf[0] = REPORT_ID_66
    buf[1] = cmd
    return bytes(buf)


def redact_response_hex(resp: bytes, max_prefix_bytes: int = 20) -> str:
    """Format the leading bytes of a 0x66 response, redacting SIRK bytes on 0x83."""
    if len(resp) >= 2 and resp[0] == REPORT_ID_66 and resp[1] == 0x83:
        head = resp[:2].hex(" ")
        tail_nonzero = any(b != 0 for b in resp[18:])
        return f"{head} <16-byte SIRK redacted>{' ...' if tail_nonzero else ' (rest 00)'}"
    prefix = resp[:max_prefix_bytes].hex(" ")
    rest_nonzero = any(b != 0 for b in resp[max_prefix_bytes:])
    return f"{prefix}{' ...' if rest_nonzero else ' (rest 00)'}"


def parse_66_response(resp: bytes) -> Parsed66Response:
    """Decode a 62-byte Report ID 0x66 response or unsolicited event."""
    if len(resp) < 5:
        raise ValueError(f"Short response ({len(resp)} bytes)")
    rid = resp[0]
    cmd = resp[1]
    b2, b3, b4 = resp[2], resp[3], resp[4]
    redacted = redact_response_hex(resp)

    if rid != REPORT_ID_66:
        return Parsed66Response(rid, cmd, f"Non-0x66 report 0x{rid:02X}", redacted)

    if cmd == 0x81:
        if len(resp) >= 9:
            pid_le = int.from_bytes(resp[2:4], "little")
            vid_le = int.from_bytes(resp[4:6], "little")
            fw_bcd = int.from_bytes(resp[6:8], "little")
            str_len = resp[8]
            text = resp[9 : 9 + str_len].decode("ascii", errors="replace")
            fw_str = f"v{(fw_bcd >> 12) & 0xF}.{(fw_bcd >> 8) & 0xF}.{(fw_bcd >> 4) & 0xF}.{fw_bcd & 0xF}"
            summary = (
                f"vid_pid={vid_le:04x}:{pid_le:04x}, headset_fw=0x{fw_bcd:04X} ({fw_str}), "
                f"len={str_len}, str={text!r}"
            )
        else:
            summary = f"device_identity (short): 0x{b2:02X}"
    elif cmd in (0x82, 0x0B):
        summary = f"wireless_connected = {b2 == 1} (raw=0x{b2:02X})"
    elif cmd == 0x83:
        sirk_slice = resp[2:18]
        nz_indices = [i for i in range(2, min(18, len(resp))) if resp[i] != 0]
        summary = (
            f"SIRK present = {len(nz_indices) > 0} "
            f"({len(nz_indices)}/16 non-zero bytes at indices {nz_indices}, key redacted)"
        )
    elif cmd in (0x84, 0x09):
        summary = f"sidetone_on = {b2 == 1} (raw=0x{b2:02X})"
    elif cmd == 0x85:
        summary = f"auto_shutdown = {b2} min ({'never' if b2 == 0 else f'{b2} min'})"
    elif cmd in (0x86, 0x0A):
        summary = f"mic_muted = {b2 == 1} (raw=0x{b2:02X})"
    elif cmd == 0x87:
        summary = f"silent_mode (playback_muted) = {b2 == 1} (raw=0x{b2:02X})"
    elif cmd == 0x88:
        signed_vol = b2 - 256 if b2 >= 128 else b2
        summary = f"sidetone_volume = {signed_vol:+d} (raw=0x{b2:02X})"
    elif cmd in (0x89, 0x0D):
        raw_mv = (b2 << 8) | b3
        valid = (b2 != 0 or b3 != 0) and b4 <= 100
        summary = (
            f"battery = {b4}% (valid={valid}, voltage={raw_mv} mV / 0x{b2:02X}{b3:02X})"
        )
    elif cmd in (0x8A, 0x0C):
        summary = f"charging = {CHARGING_NAMES.get(b2, f'Unknown({b2})')}"
    elif cmd in (0x8C, 0x07):
        summary = f"mic_connected = {b2 == 1} (raw=0x{b2:02X})"
    elif cmd == 0x8D:
        summary = f"noise_gate_on = {b2 == 1} (raw=0x{b2:02X})"
    elif cmd == 0x8F:
        summary = f"product_color = {COLOR_NAMES.get(b2, f'Unknown({b2})')}"
    else:
        summary = f"unknown cmd/event 0x{cmd:02X} (b2=0x{b2:02X}, b3=0x{b3:02X}, b4=0x{b4:02X})"

    return Parsed66Response(rid, cmd, summary, redacted)


def find_hidraw_nodes() -> List[Tuple[str, str, str]]:
    """Return list of (pid, hidraw_dev_path, product_name) for 03f0:05b7 and 03f0:06b7."""
    found: List[Tuple[str, str, str]] = []
    for sys_path_str in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        sys_path = Path(sys_path_str)
        uevent_file = sys_path / "device" / "uevent"
        if not uevent_file.is_file():
            continue
        uevent = uevent_file.read_text(encoding="utf-8", errors="replace")
        for pid in (RECEIVER_PID, HEADSET_PID):
            tag = f"HID_ID=0003:0000{VID.upper()}:0000{pid.upper()}"
            if tag in uevent.upper():
                dev_node = f"/dev/{sys_path.name}"
                name = "HyperX Cloud III Wireless"
                for line in uevent.splitlines():
                    if line.startswith("HID_NAME="):
                        name = line.split("=", 1)[1]
                found.append((pid, dev_node, name))
    return found


def drain_pending(fd: int) -> List[bytes]:
    drained: List[bytes] = []
    while True:
        r, _, _ = select.select([fd], [], [], 0.0)
        if not r:
            break
        try:
            data = os.read(fd, 256)
            if not data:
                break
            drained.append(data)
        except BlockingIOError:
            break
    return drained


def query_device(pid: str, dev_node: str, name: str, timeout_s: float = 0.25) -> int:
    role = "2.4 GHz USB Receiver" if pid == RECEIVER_PID else "Wired USB-C Headset"
    print(f"=== {dev_node} | {VID}:{pid} ({role}) | {name} ===")
    try:
        fd = os.open(dev_node, os.O_RDWR | os.O_NONBLOCK)
    except OSError as exc:
        print(f"  Cannot open {dev_node}: {exc}", file=sys.stderr)
        return 1

    try:
        stale = drain_pending(fd)
        if stale:
            print(f"  Drained {len(stale)} queued report(s) before probing.")
        for cmd, label in READ_COMMANDS:
            pkt = build_query_packet(cmd)
            t0 = time.monotonic()
            try:
                written = os.write(fd, pkt)
            except OSError as exc:
                print(f"  [0x{cmd:02X}] {label:<40} -> WRITE ERROR: {exc}")
                continue

            replies: List[Tuple[float, bytes]] = []
            deadline = t0 + timeout_s
            while True:
                rem = deadline - time.monotonic()
                if rem <= 0:
                    break
                r, _, _ = select.select([fd], [], [], rem)
                if not r:
                    break
                try:
                    resp = os.read(fd, 256)
                except BlockingIOError:
                    break
                dt_ms = (time.monotonic() - t0) * 1000.0
                replies.append((dt_ms, resp))
                if len(resp) >= 2 and resp[0] == REPORT_ID_66 and resp[1] == cmd:
                    break

            if not replies:
                print(f"  [0x{cmd:02X}] {label:<40} -> no reply ({timeout_s*1000:.0f} ms)")
            else:
                for dt_ms, resp in replies:
                    parsed = parse_66_response(resp)
                    print(
                        f"  [0x{cmd:02X}] {label:<40} -> ({dt_ms:5.1f} ms, {len(resp)} B) "
                        f"{parsed.summary}\n"
                        f"         raw: {parsed.redacted_hex}"
                    )
            time.sleep(0.02)
    finally:
        os.close(fd)
    print()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        default=0.25,
        help="Per-command read timeout in seconds (default: 0.25).",
    )
    args = parser.parse_args(argv)

    nodes = find_hidraw_nodes()
    if not nodes:
        print(f"No {VID}:{RECEIVER_PID} or {VID}:{HEADSET_PID} hidraw nodes found.", file=sys.stderr)
        return 1

    rc = 0
    for pid, dev_node, name in nodes:
        rc |= query_device(pid, dev_node, name, timeout_s=args.timeout)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Passive read-only HID input report listener for HyperX Cloud III Wireless.

Opens matching /dev/hidraw* nodes in read-only mode (os.O_RDONLY | os.O_NONBLOCK)
without sending any output or feature reports, and decodes incoming HID input
reports across all collections:
  - Report ID 0x66 (0xFF13:0x0001, 62 B): HP/HyperX vendor status notifications
    (0x07..0x0D) and query replies (0x81..0x8F, with 0x83 SIRK redacted).
  - Report ID 0x0C (0x000C:0x0001,  3 B): Consumer Control media/volume events
    (Volume Up 0xE9, Volume Down 0xEA, Mute 0xE2, Play/Pause 0xCD, etc.).
  - Report ID 0x05 (0x000B:0x0005,  2 B): Telephony Headset hook/mute events.
  - Report IDs 0x07, 0x0B (0xFF00:0x0001, 62 B): Airoha RACE over USB HID input.
"""

from __future__ import annotations

import argparse
import os
import select
import struct
import sys
import time

from query_status import (
    CHARGING_NAMES,
    RECEIVER_PID,
    UNSOLICITED_EVENTS,
    VID,
    find_hidraw_nodes,
    parse_66_response,
    redact_response_hex,
)


CONSUMER_BIT_NAMES: dict[int, str] = {
    0: "Volume Increment (0xE9)",
    1: "Volume Decrement (0xEA)",
    2: "Mute (0xE2)",
    3: "Scan Next Track (0xB5)",
    4: "Scan Previous Track (0xB6)",
    5: "Stop (0xB7)",
    6: "Play/Pause (0xCD)",
    7: "Fast Forward (0xB3)",
    8: "Rewind (0xB4)",
}

TELEPHONY_BIT_NAMES: dict[int, str] = {
    0: "Hook Switch (0x20)",
    1: "Redial (0x24)",
    2: "Flash (0x21)",
    3: "Phone Mute (0x2F)",
    4: "Drop (0x26)",
    5: "Speed Dial (0x50)",
    6: "Programmable Button (0x07)",
    7: "Line Busy Tone (0x97)",
}


def decode_unsolicited_0x66(resp: bytes) -> str:
    """Decode an unsolicited 0x66 input report (or a 0x81..0x8F query echo)."""
    if len(resp) < 3:
        return f"short 0x66 report ({len(resp)} B)"
    sub = resp[1]
    val = resp[2]
    if sub >= 0x80 and len(resp) >= 5:
        parsed = parse_66_response(resp)
        return f"QUERY_REPLY [0x{sub:02X}] {parsed.summary}"
    event_label = UNSOLICITED_EVENTS.get(sub, f"EVENT_UNKNOWN (0x{sub:02X})")
    if sub == 0x0D:
        if len(resp) >= 5 and (resp[3] != 0 or resp[4] != 0):
            voltage_mv = (resp[2] << 8) | resp[3]
            pct = resp[4]
            return f"{event_label}: battery = {pct}% (voltage={voltage_mv} mV / 0x{voltage_mv:04X})"
        return f"{event_label}: battery = {val}% (1-byte format, raw=0x{val:02X})"
    if len(resp) >= 5:
        parsed = parse_66_response(resp)
        return f"{event_label}: {parsed.summary}"
    if sub == 0x0C:
        return f"{event_label}: charging = {CHARGING_NAMES.get(val, f'Unknown({val})')}"
    return f"{event_label}: byte[2]=0x{val:02X}"


def decode_input_report(report: bytes) -> str:
    """Decode any HID input report from 03f0:05b7 or 03f0:06b7."""
    if not report:
        return "empty report"
    rid = report[0]
    if rid == 0x66:
        return f"[0x66 Vendor 0xFF13] {decode_unsolicited_0x66(report)}"
    if rid == 0x0C:
        if len(report) >= 3:
            bits = report[1] | (report[2] << 8)
        elif len(report) == 2:
            bits = report[1]
        else:
            bits = 0
        if bits == 0:
            active = ["Release (0x0000)"]
        else:
            active = [
                CONSUMER_BIT_NAMES.get(bit, f"Bit{bit} (0x{1 << bit:04X})")
                for bit in range(16)
                if bits & (1 << bit)
            ]
        return f"[0x0C Consumer] bits=0x{bits:04X} -> {', '.join(active)}"
    if rid == 0x05:
        bits = report[1] if len(report) >= 2 else 0
        if bits == 0:
            active = ["Release (0x00)"]
        else:
            active = [
                TELEPHONY_BIT_NAMES.get(bit, f"Bit{bit}")
                for bit in range(8)
                if bits & (1 << bit)
            ]
        return f"[0x05 Telephony] bits=0x{bits:02X} -> {', '.join(active)}"
    if rid in (0x07, 0x0B):
        col = "Col01 Local" if rid == 0x07 else "Col02 Relay"
        if len(report) >= 7:
            race_ch, race_type, race_len, race_id = struct.unpack_from("<BBHH", report, 1)
            return (
                f"[0x{rid:02X} Airoha RACE {col}] ch=0x{race_ch:02X} "
                f"type=0x{race_type:02X} len={race_len} race_id=0x{race_id:04X}"
            )
        return f"[0x{rid:02X} Airoha RACE {col}] ({len(report)} B)"
    return f"[0x{rid:02X} Unknown Report ID] ({len(report)} B)"


def listen_hidraw_events(
    nodes: list[tuple[str, str, str]],
    duration_s: float = 10.0,
) -> int:
    """Passively listen on one or more hidraw devices for duration_s seconds."""
    fds: dict[int, tuple[str, str, str]] = {}
    try:
        for pid, dev_node, name in nodes:
            fd = os.open(dev_node, os.O_RDONLY | os.O_NONBLOCK)
            fds[fd] = (pid, dev_node, name)
            role = "2.4 GHz USB Receiver" if pid == RECEIVER_PID else "Wired USB-C Headset"
            print(f"Listening passively (O_RDONLY) on {dev_node} | {VID}:{pid} ({role}) | {name}")
        print(f"Waiting up to {duration_s:.1f}s for unsolicited input reports (press Ctrl+C to stop early)...")
        sys.stdout.flush()

        start = time.monotonic()
        event_count = 0
        while True:
            elapsed = time.monotonic() - start
            remaining = duration_s - elapsed
            if remaining <= 0:
                break
            rlist, _, _ = select.select(list(fds.keys()), [], [], min(0.25, remaining))
            for fd in rlist:
                try:
                    data = os.read(fd, 256)
                except BlockingIOError:
                    continue
                if not data:
                    continue
                event_count += 1
                ts = time.monotonic() - start
                pid, dev_node, _ = fds[fd]
                decoded = decode_input_report(data)
                raw_str = redact_response_hex(data)
                print(f"[{ts:7.3f}s] {dev_node} ({VID}:{pid}) {decoded}")
                print(f"           raw ({len(data):2d} B): {raw_str}")
                sys.stdout.flush()
        print(f"Done ({event_count} input report(s) captured in {time.monotonic() - start:.1f}s).")
        return event_count
    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 0
    finally:
        for fd in list(fds.keys()):
            try:
                os.close(fd)
            except OSError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hidraw",
        help="Explicit /dev/hidrawX path to monitor (auto-discovers 03f0:05b7 and 03f0:06b7 if omitted)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Seconds to listen before exiting (default: 10.0)",
    )
    args = parser.parse_args()

    if args.hidraw:
        nodes = [(RECEIVER_PID, args.hidraw, "Manual hidraw target")]
    else:
        nodes = find_hidraw_nodes()
        if not nodes:
            print("No HyperX Cloud III Wireless hidraw devices found.", file=sys.stderr)
            return 1

    try:
        listen_hidraw_events(nodes, duration_s=args.duration)
    except PermissionError as exc:
        print(f"Permission error opening hidraw device: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

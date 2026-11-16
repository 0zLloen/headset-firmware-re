#!/usr/bin/env python3
"""Offline unit tests for inspect_usb_hid.py against the verified 03f0:05b7 and 03f0:06b7 descriptors."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inspect_usb_hid as mod  # noqa: E402


class TestHyperXCloudIIIHidDescriptors(unittest.TestCase):
    def setUp(self) -> None:
        self.rx_raw = bytes.fromhex(mod.VERIFIED_RECEIVER_DESCRIPTOR_HEX)
        self.hs_raw = bytes.fromhex(mod.VERIFIED_HEADSET_DESCRIPTOR_HEX)

    def test_receiver_length_and_sha256(self) -> None:
        self.assertEqual(len(self.rx_raw), 187)
        self.assertEqual(
            hashlib.sha256(self.rx_raw).hexdigest(),
            mod.VERIFIED_RECEIVER_DESCRIPTOR_SHA256,
        )

    def test_headset_length_and_sha256(self) -> None:
        self.assertEqual(len(self.hs_raw), 150)
        self.assertEqual(
            hashlib.sha256(self.hs_raw).hexdigest(),
            mod.VERIFIED_HEADSET_DESCRIPTOR_SHA256,
        )

    def test_shared_vendor_and_telephony_blocks_are_identical(self) -> None:
        # Both descriptors share the exact same 73-byte Vendor (0xFF13:0x0001)
        # block and 77-byte Telephony (0x000B:0x0005) block; the receiver simply
        # inserts the 37-byte Consumer Control (0x000C:0x0001) block at 73..109.
        self.assertEqual(self.rx_raw[:73], self.hs_raw[:73])
        self.assertEqual(self.rx_raw[110:], self.hs_raw[73:])
        self.assertEqual(self.rx_raw[:73] + self.rx_raw[110:], self.hs_raw)

    def test_receiver_top_level_collections(self) -> None:
        colls = mod.parse_hid_report_descriptor(self.rx_raw)
        self.assertEqual(len(colls), 3)

        c0 = colls[0]
        self.assertEqual((c0.usage_page, c0.usage), (0xFF13, 0x0001))
        self.assertEqual((c0.start_offset, c0.end_offset), (0, 72))
        r0 = [
            (r.report_id, r.direction, r.payload_bytes, r.wire_bytes_with_report_id)
            for r in c0.summarize_reports()
        ]
        self.assertEqual(
            r0,
            [
                (0x06, "Output", 61, 62),
                (0x07, "Input", 61, 62),
                (0x0A, "Output", 61, 62),
                (0x0B, "Input", 2, 3),
                (0x66, "Output", 61, 62),
                (0x66, "Input", 61, 62),
            ],
        )

        c1 = colls[1]
        self.assertEqual((c1.usage_page, c1.usage), (0x000C, 0x0001))
        self.assertEqual((c1.start_offset, c1.end_offset), (73, 109))
        r1 = [
            (r.report_id, r.direction, r.payload_bytes, r.wire_bytes_with_report_id)
            for r in c1.summarize_reports()
        ]
        self.assertEqual(r1, [(0x0C, "Input", 1, 2)])

        c2 = colls[2]
        self.assertEqual((c2.usage_page, c2.usage), (0x000B, 0x0005))
        self.assertEqual((c2.start_offset, c2.end_offset), (110, 186))
        r2 = [
            (r.report_id, r.direction, r.payload_bytes, r.wire_bytes_with_report_id)
            for r in c2.summarize_reports()
        ]
        self.assertEqual(
            r2,
            [
                (0x05, "Input", 1, 2),
                (0x05, "Output", 1, 2),
            ],
        )

    def test_headset_top_level_collections(self) -> None:
        colls = mod.parse_hid_report_descriptor(self.hs_raw)
        self.assertEqual(len(colls), 2)
        self.assertEqual((colls[0].usage_page, colls[0].usage), (0xFF13, 0x0001))
        self.assertEqual((colls[0].start_offset, colls[0].end_offset), (0, 72))
        self.assertEqual((colls[1].usage_page, colls[1].usage), (0x000B, 0x0005))
        self.assertEqual((colls[1].start_offset, colls[1].end_offset), (73, 149))

    def test_no_feature_reports_declared(self) -> None:
        for raw in (self.rx_raw, self.hs_raw):
            for coll in mod.parse_hid_report_descriptor(raw):
                for s in coll.slices:
                    self.assertNotEqual(s.direction, "Feature")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline unit tests for inspect_usb_hid.py against the verified 03f0:05b7 and 03f0:06b7 descriptors."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inspect_fota_package as fmod  # noqa: E402
import inspect_usb_hid as mod  # noqa: E402
import listen_events as lmod  # noqa: E402
import query_status as qmod  # noqa: E402


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


class TestQueryStatusSafetyAndParsing(unittest.TestCase):
    def test_build_query_packet_refuses_writes(self) -> None:
        for write_cmd in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x0F, 0x1E, 0x7F):
            with self.assertRaises(ValueError):
                qmod.build_query_packet(write_cmd)

    def test_build_query_packet_format(self) -> None:
        pkt = qmod.build_query_packet(0x89)
        self.assertEqual(len(pkt), 62)
        self.assertEqual(pkt[:2], bytes([0x66, 0x89]))
        self.assertEqual(pkt[2:], bytes(60))

    def test_sirk_response_is_redacted(self) -> None:
        fake_sirk = bytearray(62)
        fake_sirk[0] = 0x66
        fake_sirk[1] = 0x83
        fake_sirk[12:18] = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF])
        parsed = qmod.parse_66_response(bytes(fake_sirk))
        self.assertIn("6/16 non-zero bytes at indices [12, 13, 14, 15, 16, 17], key redacted", parsed.summary)
        self.assertIn("<16-byte SIRK redacted>", parsed.redacted_hex)
        self.assertNotIn("aa bb cc", parsed.redacted_hex)

    def test_device_identity_0x81_parsing(self) -> None:
        rx_81 = bytes.fromhex(
            "66 81 b7 08 f0 03 09 31 20 48 50 2c 20 49 6e 63 "
            "48 79 70 65 72 58 20 43 6c 6f 75 64 20 49 49 49 "
            "20 57 69 72 65 6c 65 73 73"
        ).ljust(62, b"\x00")
        p_rx = qmod.parse_66_response(rx_81)
        self.assertIn("vid_pid=03f0:08b7", p_rx.summary)
        self.assertIn("headset_fw=0x3109 (v3.1.0.9)", p_rx.summary)
        self.assertIn("len=32", p_rx.summary)
        self.assertIn("HP, IncHyperX Cloud III Wireless", p_rx.summary)

    def test_battery_and_sidetone_parsing(self) -> None:
        batt = bytearray(62)
        batt[:5] = bytes([0x66, 0x89, 0x10, 0x37, 85])
        p_batt = qmod.parse_66_response(bytes(batt))
        self.assertIn("battery = 85%", p_batt.summary)
        self.assertIn("voltage=4151 mV / 0x1037", p_batt.summary)
        self.assertIn("valid=True", p_batt.summary)

        vol = bytearray(62)
        vol[:3] = bytes([0x66, 0x88, 0xFB])  # -5 in two's complement
        p_vol = qmod.parse_66_response(bytes(vol))
        self.assertIn("sidetone_volume = -5", p_vol.summary)

    def test_headset_off_zero_response_parsing(self) -> None:
        rx_off_81 = bytes([0x66, 0x81]) + bytes(60)
        p_off = qmod.parse_66_response(rx_off_81)
        self.assertIn("vid_pid=0000:0000", p_off.summary)
        self.assertIn("headset_fw=0x0000 (v0.0.0.0)", p_off.summary)
        self.assertIn("len=0", p_off.summary)


class TestListenEventsDecoding(unittest.TestCase):
    def test_decode_unsolicited_0x66_events(self) -> None:
        ev_mute = bytes([0x66, 0x0A, 0x01, 0x01]) + bytes(58)
        self.assertIn("EVENT_MIC_MUTE (0x0A): mic_muted = True (raw=0x01, byte[3]=0x01)", lmod.decode_input_report(ev_mute))

        ev_batt = bytes([0x66, 0x0D, 0x10, 0x45, 100]) + bytes(57)
        self.assertIn("battery = 100% (voltage=4165 mV / 0x1045)", lmod.decode_input_report(ev_batt))

        # 6-packet power-off burst verified on 03f0:05b7: 0x0B, 0x02, 0x0D, 0x08, 0x07, 0x0F
        self.assertIn("EVENT_WIRELESS_STATUS (0x0B): wireless_connected = False", lmod.decode_input_report(bytes([0x66, 0x0B, 0x00]) + bytes(59)))
        self.assertIn("EVENT_AUTO_SHUTDOWN (0x02): auto_shutdown = 0 min", lmod.decode_input_report(bytes([0x66, 0x02, 0x00]) + bytes(59)))
        self.assertIn("EVENT_BATTERY (0x0D): battery = 0%", lmod.decode_input_report(bytes([0x66, 0x0D, 0x00]) + bytes(59)))
        self.assertIn("EVENT_SILENT_MODE / PLAYBACK_MUTE (0x08): silent_mode (playback_muted) = True", lmod.decode_input_report(bytes([0x66, 0x08, 0x01]) + bytes(59)))
        self.assertIn("EVENT_MIC_CONNECTED (0x07): mic_connected = False", lmod.decode_input_report(bytes([0x66, 0x07, 0x00]) + bytes(59)))
        self.assertIn("EVENT_NOISE_GATE (0x0F): noise_gate_on = False", lmod.decode_input_report(bytes([0x66, 0x0F, 0x00]) + bytes(59)))

    def test_decode_consumer_and_telephony_reports(self) -> None:
        self.assertIn("Volume Increment (0xE9)", lmod.decode_input_report(bytes([0x0C, 0x01])))
        self.assertIn("Release (0x0000)", lmod.decode_input_report(bytes([0x0C, 0x00])))
        self.assertIn("Hook Switch (0x20)", lmod.decode_input_report(bytes([0x05, 0x01])))

    def test_decode_airoha_race_report(self) -> None:
        race_pkt = bytes([0x07, 0x05, 0x5B, 0x06, 0x00, 0x02, 0x1C]) + bytes(55)
        self.assertIn("[0x07 Airoha RACE Col01 Local]", lmod.decode_input_report(race_pkt))
        self.assertIn("race_id=0x1C02", lmod.decode_input_report(race_pkt))


class TestInspectFotaPackage(unittest.TestCase):
    def test_synthetic_fota_header_parsing_and_hash_verification(self) -> None:
        # Build a synthetic Airoha FOTA header using the exact verified 0x0100..0x01F5
        # TLV bytes from 03F005B7.bin (AB1565_ULL2_DONGLE v4.1.0.9) and a 64-byte dummy body.
        tlv_hex = (
            "11000a00020100100000f0671200"
            "13001c0076342e312e302e3900ffffffffffffffffffffffffffffffffffffff"
            "1200280003000000"
            "001000000090090000300100"
            "00a009000040130000200e00"
            "00e01c0000e0000000e02300"
            "1400640003000000"
            "f4784e8be416ac4eba6aa22e49fcebc61f2a08f346e0d805bbe4a8c1f18889be"
            "de217c4632d40ac364495f2390053c7978a5f0ddee1dc448c04326c13b1a4929"
            "e485c00088b867d53e2158662049ee0bf712930824e70d95e25a783a76471e4b"
            "200012004142313536355f554c4c325f444f4e474c45"
            "21001100646f6e676c655f7265665f64657369676e"
            "f000010001"
            "ffff"
        )
        tlv_bytes = bytes.fromhex(tlv_hex)
        body = tlv_bytes.ljust(0x0F00, b"\xFF") + b"\xAA" * 64
        hdr_hash = hashlib.sha256(body).digest()
        pkg = hdr_hash + (b"\xFF" * (0x0100 - 32)) + body

        meta = fmod.parse_fota_package(pkg)
        self.assertTrue(meta.header_sha256_valid)
        self.assertEqual(meta.version, "v4.1.0.9")
        self.assertEqual(meta.device_name, "AB1565_ULL2_DONGLE")
        self.assertEqual(meta.board_name, "dongle_ref_design")
        self.assertEqual(meta.compression_type, 0x02)
        self.assertEqual(meta.integrity_type, 0x01)
        self.assertEqual(meta.fota_offset, 0x00001000)
        self.assertEqual(meta.fota_length, 0x001267F0)
        self.assertEqual(meta.encryption_flag, 0x01)
        self.assertEqual(len(meta.partitions), 3)
        self.assertEqual(meta.partitions[0].flash_target_offset, 0x00013000)
        self.assertEqual(meta.partitions[1].flash_target_offset, 0x000E2000)
        self.assertEqual(meta.partitions[2].flash_target_offset, 0x0023E000)


if __name__ == "__main__":
    unittest.main()

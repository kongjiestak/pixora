import sys
from pathlib import Path
import unittest
import importlib.util
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'clients'))
from ble_wire import Assembler,derive_key,seal,open_frame,MAX_PLAINTEXT
from mac_usb_bridge import make_frame

TOKEN='A'*32  # Synthetic test credential; never a real display token.

@unittest.skipUnless(importlib.util.find_spec("cryptography"),"Install clients/requirements-ble.txt for BLE protocol checks")
class BleWireTests(unittest.TestCase):
    def test_signed_frame_roundtrip_at_every_split(self):
        plain=make_frame({'event':'offline'},TOKEN,'1'*32,1792700000,42)
        packet=seal(plain,TOKEN)
        for split in range(1,len(packet)):
            a=Assembler();self.assertFalse(a.feed(packet[:split]));self.assertTrue(a.feed(packet[split:]))
            self.assertEqual(open_frame(a.buffer,TOKEN),plain)

    def test_nonce_is_fresh(self):
        self.assertNotEqual(seal(b'x',TOKEN),seal(b'x',TOKEN))

    def test_tamper_wrong_key_and_truncation(self):
        packet=seal(b'private observation',TOKEN)
        for i in range(len(packet)):
            corrupt=bytearray(packet);corrupt[i]^=1
            with self.assertRaises(Exception):open_frame(corrupt,TOKEN)
        with self.assertRaises(Exception):open_frame(packet,'B'*32)
        for size in range(len(packet)):
            with self.assertRaises(Exception):open_frame(packet[:size],TOKEN)

    def test_bounded_poisoned_transfer(self):
        for chunk in [b'xxxx', b'PBL1'+b'\0'*12+b'\xff'*4, b'PBL1'+b'\0'*16, b'x'*(MAX_PLAINTEXT+37)]:
            a=Assembler()
            with self.assertRaises(ValueError):a.feed(chunk)
            with self.assertRaises(ValueError):a.feed(seal(b'x',TOKEN))
            a.reset();self.assertTrue(a.feed(seal(b'x',TOKEN)))
        a=Assembler();p=seal(b'x',TOKEN)
        with self.assertRaises(ValueError):a.feed(p+b'x')

    def test_maximum_and_one_byte_chunks(self):
        p=seal(b'x'*MAX_PLAINTEXT,TOKEN);a=Assembler()
        for n,b in enumerate(p):self.assertEqual(a.feed(bytes([b])),n==len(p)-1)
        self.assertEqual(open_frame(a.buffer,TOKEN),b'x'*MAX_PLAINTEXT)
        for value in [b'',b'x'*(MAX_PLAINTEXT+1)]:
            with self.assertRaises(ValueError):seal(value,TOKEN)

    def test_key_domain_and_validation(self):
        import hashlib
        self.assertNotEqual(derive_key(TOKEN),hashlib.sha256(TOKEN.encode()).digest())
        for value in ['x'*31,'x'*129,' '*32,'中'*32,None]:
            with self.assertRaises(ValueError):derive_key(value)

    def test_cross_language_fixture(self):
        # Fixed IV is exclusively for the public test vector; production seal
        # always obtains a fresh random IV and offers no caller override.
        with patch('ble_wire.os.urandom',return_value=bytes(range(12))):
            packet=seal(b'Pixora synthetic BLE fixture',TOKEN)
        fixture=Path(__file__).resolve().parents[1]/'firmware/esp32/host-tests/ble-fixture.hex'
        self.assertEqual(packet,bytes.fromhex(fixture.read_text()))

if __name__=='__main__':unittest.main()

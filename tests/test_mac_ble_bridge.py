import importlib.util
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'clients'))
from mac_ble_bridge import session,verify_ack,HELLO_UUID,DATA_UUID,ACK_UUID
from mac_usb_bridge import proof
from ble_wire import open_frame
TOKEN='A'*32
NONCE='1'*32

class FakeClient:
    is_connected=True
    mtu_size=23
    def __init__(self,bad_hello=False,bad_ack=False):
        self.chunks=[];self.bad_hello=bad_hello;self.bad_ack=bad_ack
    async def read_gatt_char(self,uuid):
        if uuid==HELLO_UUID:
            return f'PXUSB_HELLO {NONCE} {proof("B"*32 if self.bad_hello else TOKEN, ("hello "+NONCE).encode())}\n'.encode()
        assert uuid==ACK_UUID
        frame=open_frame(b''.join(self.chunks),TOKEN)
        assert frame.startswith(b'PXUSB1 '+NONCE.encode()+b' ')
        sequence=int(frame.split(b' ',4)[3]);kind='offline'
        signature=proof(TOKEN,f'ack {NONCE} {sequence} {kind}'.encode())
        if self.bad_ack:signature='0'*64
        return f'PXBLE_ACK {sequence} {kind} {signature}'.encode()
    async def write_gatt_char(self,uuid,data,response):
        assert uuid==DATA_UUID and response and len(data)<=20
        self.chunks.append(data)

@unittest.skipUnless(importlib.util.find_spec('cryptography'),'BLE test dependencies required')
class MacBleTests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_ordered_encrypted_transfer(self):
        client=FakeClient()
        with patch('mac_ble_bridge.fetch',return_value={'event':'offline'}) as fetch:
            self.assertTrue(await session(client,{'token':TOKEN},True))
            fetch.assert_called_once()
        self.assertGreater(len(client.chunks),1)
        self.assertNotIn(b'offline',b''.join(client.chunks))

    async def test_unmatched_candidate_cannot_trigger_fetch(self):
        with patch('mac_ble_bridge.fetch') as fetch:
            self.assertFalse(await session(FakeClient(bad_hello=True),{'token':TOKEN},True))
            fetch.assert_not_called()

    async def test_unsigned_ack_is_rejected(self):
        with patch('mac_ble_bridge.fetch',return_value={'event':'offline'}):
            with self.assertRaises(ValueError):
                await session(FakeClient(bad_ack=True),{'token':TOKEN},True)

    def test_ack_binds_nonce_sequence_kind_and_token(self):
        raw=f'PXBLE_ACK 42 data {proof(TOKEN,f"ack {NONCE} 42 data".encode())}'.encode()
        self.assertTrue(verify_ack(raw,TOKEN,NONCE,42,'data'))
        for key,nonce,seq,kind in [('B'*32,NONCE,42,'data'),(TOKEN,'2'*32,42,'data'),(TOKEN,NONCE,43,'data'),(TOKEN,NONCE,42,'revoked')]:
            self.assertFalse(verify_ack(raw,key,nonce,seq,kind))

if __name__=='__main__':unittest.main()

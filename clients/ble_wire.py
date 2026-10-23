"""Pixora BLE v1 encrypted transport. No radio or account credentials here.

The plaintext is the existing signed USB frame, bound to a fresh BLE session
nonce (never the USB nonce). GATT chunk boundaries carry no semantic meaning.
"""
import hashlib
import os
import re
import struct

MAGIC = b'PBL1'
HEADER_SIZE = 20
TAG_SIZE = 16
MAX_PLAINTEXT = 20000
SERVICE_UUID = '364b4de0-40f2-4d58-9db6-2ded36b6b601'


def derive_key(token):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token):
        raise ValueError('A scoped display token is required')
    return hashlib.sha256(b'Pixora BLE v1 key\x00' + token.encode('ascii')).digest()


def seal(plaintext, token):
    """Generate a fresh 96-bit IV for every encrypted frame; never reuse an IV."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not isinstance(plaintext, bytes) or not 0 < len(plaintext) <= MAX_PLAINTEXT:
        raise ValueError('Invalid BLE frame size')
    iv = os.urandom(12)
    header = MAGIC + iv + struct.pack('>I', len(plaintext))
    return header + AESGCM(derive_key(token)).encrypt(iv, plaintext, header)


def open_frame(packet, token):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if len(packet) < HEADER_SIZE + TAG_SIZE or packet[:4] != MAGIC:
        raise ValueError('Invalid BLE envelope')
    size = struct.unpack('>I', packet[16:20])[0]
    if not 0 < size <= MAX_PLAINTEXT or len(packet) != HEADER_SIZE + size + TAG_SIZE:
        raise ValueError('Invalid BLE envelope size')
    return AESGCM(derive_key(token)).decrypt(packet[4:16], packet[20:], packet[:20])


class Assembler:
    """Bounded stream parser: error poisons the session until an explicit reset.

    One envelope per session transfer. Caller must reset after consumption,
    disconnect or a 10 second transfer timeout. No silent resynchronization.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.buffer = bytearray()
        self.expected = None
        self.failed = False

    def feed(self, chunk):
        if self.failed:
            raise ValueError('Reset the rejected BLE transfer')
        try:
            if not chunk or len(self.buffer) + len(chunk) > HEADER_SIZE + MAX_PLAINTEXT + TAG_SIZE:
                raise ValueError('Invalid BLE chunk size')
            self.buffer.extend(chunk)
            if len(self.buffer) >= 4 and self.buffer[:4] != MAGIC:
                raise ValueError('Invalid BLE marker')
            if len(self.buffer) >= HEADER_SIZE:
                size = struct.unpack('>I', self.buffer[16:20])[0]
                if not 0 < size <= MAX_PLAINTEXT:
                    raise ValueError('Invalid BLE declared size')
                self.expected = HEADER_SIZE + size + TAG_SIZE
                if len(self.buffer) > self.expected:
                    raise ValueError('Trailing BLE bytes')
            return self.expected is not None and len(self.buffer) == self.expected
        except ValueError:
            self.failed = True
            raise

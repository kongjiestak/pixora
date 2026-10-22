import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
spec=importlib.util.spec_from_file_location('usb_bridge',Path(__file__).parents[1]/'clients/mac_usb_bridge.py')
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
KEY='example-device-key-not-a-real-token'
NONCE='0123456789abcdef0123456789abcdef'

class BridgeTests(unittest.TestCase):
    def test_hello_only_accepts_matching_device_proof(self):
        signature=hmac.new(KEY.encode(),('hello '+NONCE).encode(),hashlib.sha256).hexdigest()
        line=f'I (123) pixora: PXUSB_HELLO {NONCE} {signature}\r\n'.encode()
        self.assertEqual(bridge.hello_nonce(line,KEY),NONCE)
        self.assertIsNone(bridge.hello_nonce(line,'different-device-key'))
        self.assertIsNone(bridge.hello_nonce(line.replace(b'PXUSB_HELLO',b'garbage'),KEY))

    def test_frame_matches_independent_hmac(self):
        frame=bridge.make_frame({'event':'offline'},KEY,NONCE,1792634400,42)
        prefix,nonce,epoch,seq,signature,body=frame.rstrip(b'\n').split(b' ',5)
        self.assertEqual(prefix,b'PXUSB1')
        self.assertEqual(json.loads(body),{'event':'offline'})
        expected=hmac.new(KEY.encode(),b'data '+nonce+b' '+epoch+b' '+seq+b'\n'+body,hashlib.sha256).hexdigest()
        self.assertTrue(hmac.compare_digest(signature.decode(),expected))

    def test_oversized_and_nonfinite_payloads_rejected(self):
        for payload,nonce in [({'x':'x'*17000},NONCE),({'x':float('nan')},NONCE),({},'wrong')]:
            with self.assertRaises(ValueError):bridge.make_frame(payload,KEY,nonce,1792634400,1)

    def test_revocation_is_distinct_from_network_failure(self):
        class Opener:
            code=401
            def open(self,*args,**kwargs):raise urllib.error.HTTPError('https://example.invalid',self.code,'',None,None)
        opener=Opener()
        with patch('urllib.request.build_opener',return_value=opener):
            config={'server':'https://example.invalid','token':KEY,'device_id':'a'*24}
            for code in [401,403]:
                opener.code=code;self.assertEqual(bridge.fetch(config),{'event':'revoked'})
            for code in [301,500]:
                opener.code=code;self.assertEqual(bridge.fetch(config),{'event':'offline'})

    def test_bearer_redirects_are_not_followed(self):
        class Opener:
            def open(self,*args,**kwargs):raise OSError('network offline')
        with patch('urllib.request.build_opener',return_value=Opener()) as build:
            bridge.fetch({'server':'https://example.invalid','token':KEY,'device_id':'a'*24})
            policies=[c for c in build.call_args.args if isinstance(c,urllib.request.HTTPRedirectHandler)]
            self.assertEqual(len(policies),1)
            self.assertIsNone(policies[0].redirect_request(None,None,302,'',{},'https://other.invalid'))

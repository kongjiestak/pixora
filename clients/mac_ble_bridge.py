"""Opt-in encrypted Mac BLE display bridge. Requires requirements-ble.txt.

Matches the screen by signed hello, never by its advertised name or address.
The configuration is the existing independent scoped display configuration.
"""
import argparse
import asyncio
import hmac
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
from ble_wire import SERVICE_UUID,seal
from mac_usb_bridge import fetch,hello_nonce,make_frame,proof

HELLO_UUID=SERVICE_UUID[:-1]+'2'
DATA_UUID=SERVICE_UUID[:-1]+'3'
ACK_UUID=SERVICE_UUID[:-1]+'4'

def verify_ack(raw,token,nonce,sequence,kind):
    match=re.fullmatch(rb'PXBLE_ACK (\d+) (data|offline|revoked) ([0-9a-f]{64})',bytes(raw))
    return bool(match and int(match[1])==sequence and match[2].decode()==kind and
        hmac.compare_digest(match[3].decode(),proof(token,f'ack {nonce} {sequence} {kind}'.encode())))

def load_config(path):
    if path.stat().st_mode&0o077:raise ValueError('Configuration must be private (chmod 600)')
    config=json.loads(path.read_text());url=urlsplit(config['server'])
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('A plain HTTPS origin is required')
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}',config['token']) or not re.fullmatch(r'[0-9a-f]{24}',config['device_id']):
        raise ValueError('An independent scoped display configuration is required')
    return config

async def session(client,config,once):
    nonce=hello_nonce(bytes(await client.read_gatt_char(HELLO_UUID)),config['token'])
    if not nonce:return False
    print('Matching BLE screen authenticated',flush=True)
    sequence=int(time.time());feed_due=0;cached=None
    while client.is_connected:
        if time.monotonic()>=feed_due:
            cached=await asyncio.to_thread(fetch,config);feed_due=time.monotonic()+30
        payload=dict(cached)
        if config.get('activity_enabled') and 'event' not in payload and any(isinstance(p,dict) and p.get('provider')=='codex' for p in payload.get('providers',[])):
            from codex_activity import observe_activity
            payload['activity']=await asyncio.to_thread(observe_activity)
        sequence+=1
        packet=seal(make_frame(payload,config['token'],nonce,int(time.time()),sequence),config['token'])
        chunk_size=max(1,min(180,client.mtu_size-3))
        # Response writes provide ordered backpressure; all bytes remain encrypted.
        for offset in range(0,len(packet),chunk_size):
            await client.write_gatt_char(DATA_UUID,packet[offset:offset+chunk_size],response=True)
        kind=payload.get('event','data')
        ack=await client.read_gatt_char(ACK_UUID)
        if not verify_ack(ack,config['token'],nonce,sequence,kind):
            raise ValueError('Signed BLE acknowledgement mismatch')
        print('Encrypted BLE frame accepted: '+kind,flush=True)
        if once:return True
        await asyncio.sleep(5 if config.get('activity_enabled') else 30)
    return True

async def run(config,once=False):
    from bleak import BleakClient,BleakScanner
    from bleak.exc import BleakError
    while True:
        try:
            devices=await asyncio.wait_for(BleakScanner.discover(timeout=8,service_uuids=[SERVICE_UUID]),20)
            for device in devices:
                try:
                    async with BleakClient(device,services=[SERVICE_UUID],timeout=15) as client:
                        if await session(client,config,once) and once:return 0
                except (BleakError,OSError,ValueError,asyncio.TimeoutError):
                    print('BLE candidate unavailable or not authenticated',flush=True)
            if once:
                print('No matching enabled BLE screen accepted a frame',flush=True);return 1
        except (BleakError,OSError,asyncio.TimeoutError):
            if once:return 1
            print('BLE unavailable; retrying',flush=True)
        await asyncio.sleep(5)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--once',action='store_true')
    args=parser.parse_args()
    try:config=load_config(args.config)
    except (OSError,ValueError,KeyError):parser.error('Invalid private scoped display configuration')
    raise SystemExit(asyncio.run(run(config,args.once)))

if __name__=='__main__':main()

"""Read-only Pixora BLE service discovery; does not pair or send credentials.

No match is expected until BLE GATT firmware is installed. Discovery alone
does not authenticate a device or prove that the data bridge works.
"""
import asyncio
import subprocess
import sys
from ble_wire import SERVICE_UUID

async def probe():
    from bleak import BleakScanner
    from bleak.exc import BleakError
    try:
        devices=await BleakScanner.discover(timeout=8,service_uuids=[SERVICE_UUID])
        print(f'Pixora BLE service candidates: {len(devices)} (not authenticated)')
        return 0
    except (BleakError,OSError):
        print('BLE scan unavailable. Check Bluetooth permission for the launching app.')
        return 1

if __name__=='__main__':
    if '--worker' in sys.argv:
        raise SystemExit(asyncio.run(probe()))
    # CoreBluetooth initialization can block before its scan timeout starts
    # (for example pending permission). Bound the entire child, not only scan.
    try:
        result=subprocess.run([sys.executable,__file__,'--worker'],timeout=20)
        raise SystemExit(result.returncode)
    except subprocess.TimeoutExpired:
        print('BLE initialization timed out; check Bluetooth permission for the launching app.')
        raise SystemExit(2)

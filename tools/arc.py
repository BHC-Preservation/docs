#!/usr/bin/env python3
"""Talk to the Colonies ARC over BLE (Nordic UART Service), without the official app.

  .venv/bin/python arc.py scan            # list nearby BLE devices advertising NUS
  .venv/bin/python arc.py info [ADDR]     # read ARC ID, battery voltage, firmware (read-only)
  .venv/bin/python arc.py enter-dfu ADDR  # put ARC into bootloader (asks for confirmation)

Close the Colonies app first: ARC accepts only one connection.
Protocol notes: see protocol.md in the BHC docs.
"""
import asyncio, sys
from bleak import BleakClient, BleakScanner

NUS = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
RX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # write
TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # notify
DFU_SVC = "0000fe59-0000-1000-8000-00805f9b34fb"  # Nordic Secure DFU (bootloader)
PROTO_NEWEST = 5  # app: protocol.newest; negotiates downward on error 00 ff 47
ERR = bytes([0x00, 0xFF, 0x47])  # ARC "unsupported protocol version" payload

ARC_BATTERY_LV = {"alkaline": 4.8, "rechargable": 4.48}  # app thresholds (low)


def crc8(data, poly=0x07):
    c = 0
    for b in data:
        c ^= b
        for _ in range(8):
            c = ((c << 1) ^ poly) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c


def frame(payload, proto=PROTO_NEWEST):
    body = [0x55, proto, len(payload) + 4, *payload]
    return bytes(body + [crc8(body)])


assert frame([0x04, 0x01, 0x01], 3).hex() == "55030704010118"
assert crc8(bytes.fromhex("5501060302")) == 0x4D  # old-protocol battery frame from the app


class Reassembler:
    """NUS notifications are <=20 B; ARC frames can be longer (e.g. ID = 22 B).
    Buffer bytes and emit whole frames using the length byte (frame[2])."""

    def __init__(self, q):
        self.q, self.buf = q, bytearray()

    def __call__(self, _, data):
        self.buf += data
        while self.buf:
            if self.buf[0] != 0x55:
                self.buf.pop(0)  # resync
                continue
            if len(self.buf) < 3 or len(self.buf) < self.buf[2]:
                return
            n = self.buf[2]
            self.q.put_nowait(bytes(self.buf[:n]))
            del self.buf[:n]


def fw_version(n):
    """App's Firmware.versionString (4687.js): zero-pad to 6 digits, split in pairs."""
    d = f"{n:06d}"
    return f"{int(d[0:2])}.{int(d[2:4])}.{int(d[4:6])}"


assert fw_version(10013) == "1.0.13" and fw_version(10023) == "1.0.23"


def le(bs):
    return int.from_bytes(bytes(bs), "little")


async def find(addr=None):
    if addr:
        return addr
    devs = await BleakScanner.discover(timeout=6, service_uuids=[NUS], return_adv=True)
    if not devs:
        sys.exit("No NUS device found. Is ARC on and the Colonies app closed?")
    for a, (d, adv) in devs.items():
        print(f"{a}  {d.name or '?'}  rssi={adv.rssi}")
    return next(iter(devs))


async def drain(q, settle=0.3):
    await asyncio.sleep(settle)  # let late fragments/frames arrive, then drop them
    while not q.empty():
        print(f"  (dropped stale {q.get_nowait().hex(' ')})")


async def xfer(client, payload, q, proto, timeout=6):
    """Send one frame; return the raw response frame, or None on timeout."""
    await drain(q)
    f = frame(payload, proto)
    print(f"> {f.hex(' ')}")
    await client.write_gatt_char(RX, f, response=False)
    try:
        r = await asyncio.wait_for(q.get(), timeout)
    except asyncio.TimeoutError:
        print("  (no response)")
        return None
    ok = crc8(r[:-1]) == r[-1]
    print(f"< {r.hex(' ')}  crc={'ok' if ok else 'BAD'}")
    return r if ok else None


async def request(client, payload, q, proto, timeout=6):
    r = await xfer(client, payload, q, proto, timeout)
    if r is None or r[3:-1] == ERR or r[1] != proto:
        if r is not None:
            print("  (error / wrong protocol in reply)")
        return None
    return r


async def negotiate(client, q, retries=3):
    """Mirror the app: start at v5; step down ONLY on explicit 00 ff 47 error.
    Timeouts retry the same version. A reply counts only if its header version
    equals the one we asked with (a late reply to an earlier frame must not)."""
    for proto in range(PROTO_NEWEST, 0, -1):
        print(f"-- trying protocol v{proto}")
        for _ in range(retries):
            r = await xfer(client, [0x03, 0x02], q, proto)
            if r is None:
                continue  # timeout: retry same version
            if r[3:-1] == ERR:
                print(f"  v{proto} rejected by ARC")
                break  # step down
            if r[1] == proto:
                print(f"== ARC speaks protocol v{proto}")
                return proto
            print(f"  reply has header v{r[1]}, ignoring (late reply?)")
        else:
            sys.exit(f"No valid reply for v{proto} after {retries} tries; not downgrading on silence. Retry.")
    sys.exit("ARC rejected all protocol versions 5..1")


async def info(addr):
    addr = await find(addr)
    q = asyncio.Queue()
    async with BleakClient(addr) as c:
        await c.start_notify(TX, Reassembler(q))
        proto = await negotiate(c, q)
        r = await request(c, [0x03, 0x01], q, proto)
        if r:
            print(f"  ARC ID: {le(r[5:-1][:8]):016X} (raw LE payload {r[5:-1].hex()})")
        r = await request(c, [0x03, 0x02], q, proto)
        if r:
            v = le(r[5:-1]) * 0.0004615
            print(f"  battery: {v:.3f} V")
            for t, low in ARC_BATTERY_LV.items():
                print(f"    app '{t}' threshold {low} V -> {'OK' if v >= low else 'BLOCKED'}")
        r = await request(c, [0x03, 0x03], q, proto)
        if r:
            n = le(r[5:-1])
            print(f"  firmware: {fw_version(n)} (raw {n}, bytes {r[5:-1].hex()})")


async def enter_dfu(addr):
    if input(f"Put ARC {addr} into DFU bootloader? Type YES: ").strip().upper() != "YES":
        return print("aborted")
    q = asyncio.Queue()
    gone = asyncio.Event()
    async with BleakClient(addr, disconnected_callback=lambda _: gone.set()) as c:
        await c.start_notify(TX, Reassembler(q))
        proto = await negotiate(c, q)
        await drain(q, 1.0)
        f = frame([0x04, 0x01, 0x01], proto)
        print(f"> {f.hex(' ')}  (enter DFU, protocol v{proto})")
        await c.write_gatt_char(RX, f, response=False)
        try:
            await asyncio.wait_for(gone.wait(), 10)
            print("ARC disconnected -> rebooting into bootloader")
        except asyncio.TimeoutError:
            while not q.empty():
                print(f"< {q.get_nowait().hex(' ')}")
            sys.exit("ARC did NOT disconnect within 10 s: DFU command not accepted. Nothing changed; safe to retry.")
    print("Scanning for Secure DFU bootloader (service FE59)...")
    devs = await BleakScanner.discover(timeout=10, service_uuids=[DFU_SVC], return_adv=True)
    for a, (d, adv) in devs.items():
        print(f"  BOOTLOADER: {a}  {d.name or '?'}  rssi={adv.rssi}")
    if not devs:
        print("  none seen from the Mac (it may still be visible on the phone, often as 'DfuTarg').")
    print("Now on iPhone: nRF Device Firmware Update -> DFU zip (www/bhcapp-1.0.23.zip from the app) -> pick that device -> Upload.")


def main():
    cmd, *rest = sys.argv[1:] or ["info"]
    arg = rest[0] if rest else None
    if cmd == "scan":
        asyncio.run(find())
    elif cmd == "info":
        asyncio.run(info(arg))
    elif cmd == "enter-dfu" and arg:
        asyncio.run(enter_dfu(arg))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

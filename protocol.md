---
title: BLE protocol
---

# ARC BLE protocol

[← contents](index.md)

## Connection

The ARC advertises over BLE under its own device name. The bootloader appends `_DFU` to that name.
Communication goes through the **Nordic UART Service (NUS)**:

| role | UUID |
|---|---|
| service | `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` |
| write (app → ARC) | `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` |
| notify (ARC → app) | `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` |

- The ARC accepts **only one connection**. Close the Colonies app before connecting your own tool.
- You must enable notifications on the TX characteristic. All responses and events arrive there.
- In update mode the ARC is a completely different BLE device, described in [firmware update](update.md).

### Link details

| item | value |
|---|---|
| device name | `BHCHQ`, the same on every unit; the bootloader advertises as `BHCHQ_DFU` |
| advertising | full name and flags (LE only, limited discoverable) in the advertising data, the NUS UUID in the **scan response**. 40 ms interval, 180 s per burst, restarted until a client connects |
| connections | one link only. Pairing is refused, nothing is encrypted |
| connection parameters | interval 20–75 ms, latency 0, supervision timeout 4 s. The ARC asks for a parameter update 5 s after connecting, then every 30 s, three attempts; if negotiation fails it disconnects |
| MTU | the ARC requests 247 B (data length 251) |
| ARC → client | always **20-byte notifications, about 100 ms apart**, whatever the MTU. A 222 B response therefore takes over 1 s |
| client → ARC | writes are collected in a 512 B buffer and processed once per loop pass. Longest frame the ARC accepts: 246 B; a longer frame is dropped without an answer |

Two delays come from the BLE loop: right after a connection the ARC can take up to about 3 s before it reads
the first request, and each loop pass waits up to about 1 s for outgoing data before it reads the next one.

## Frame

Every message in both directions has the same shape:

```
55  <version>  <length>  <payload…>  <crc8>
```

| field | description |
|---|---|
| `55` | fixed start marker |
| `version` | protocol version, negotiated on connect (see below) |
| `length` | length of the **whole** frame in bytes, including `55` and the CRC |
| `payload` | command or response |
| `crc8` | CRC-8, polynomial `0x07`, initial value `0x00`, no reflection, no final XOR. Computed over all bytes before the CRC |

Example (confirmed): the battery query in version 5 is `55 05 06 03 02 15`.

```python
def crc8(data):
    c = 0
    for b in data:
        c ^= b
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c

def frame(payload, version=5):
    body = [0x55, version, len(payload) + 4, *payload]
    return bytes(body + [crc8(body)])
```

### Fragmentation

A single notification carries at most 20 bytes, and many responses are longer (game state is over 200 B).
The receiver has to append notifications to a buffer until both conditions hold: `buffer[2] == len(buffer)`
and the CRC matches. Only then is the frame complete. The app does exactly this (module `2432`). Skip the
reassembly and every response will be shifted by one.

In the other direction, send all chunks of one frame back to back so that they land in the same read. The ARC
looks for `55`, takes one frame per read and drops anything after it; it cannot reassemble a frame split across
two reads.

## ARC response

```
55  <version>  <length>  <category>  <status>  <data…>  <crc8>
offset: 0      1          2           3           4         5…
```

- **`category`** (byte 3) says what the response is about. The app checks it before parsing anything (module `2933`):

  | value | category |
  |---|---|
  | `01` | game engine (state, new game, round) |
  | `02` | modules and board events (buildings, NFC cards, lights) |
  | `03` | device info (ID, battery, firmware) |
  | `04` | operating mode (game mode, bootloader) |
  | `00` | generic error (e.g. unsupported protocol version) |
  | `05` | test commands (simulated events, see [in-game communication](game.md#simulating-events)) |

- **`status`** (byte 4): `01` means OK, `FF` means error. On error, byte 5 is the error code.
- **data** starts at offset 5 and runs up to the second-to-last byte. Multi-byte numbers are **little-endian**.

Known error codes:

| code | meaning |
|---|---|
| `47` (71) | unsupported protocol version. Full frame: `55 05 07 00 FF 47 EF` (confirmed) |
| other | the app shows a generic "problem with ARC" message and clears its queue |

> **Correction:** there are more codes. **The error code is an `errno` value.** The ARC runs the NuttX RTOS; handlers
> return `-errno`, and the low byte goes on the wire, with NuttX's numbering. A simple command that succeeds is
> answered `<category> 01 00`, i.e. error code 0.

| code | errno | meaning |
|---|---|---|
| `00` | – | no error |
| `01` (1) | `EPERM` | no game in progress (state queries, end round) |
| `0D` (13) | `EACCES` | the storage is not initialised, or a fleet lock/unlock is not authorised |
| `10` (16) | `EBUSY` | a simulated event is still pending; end round after the game has ended |
| `16` (22) | `EINVAL` | the usual answer to a malformed or refused request: bad length, unknown command, invalid player, locked fleet, a planet that does not exist… |
| `47` (71) | | unsupported protocol version. Full frame: `55 05 07 00 FF 47 EF` (confirmed) |
| `69` (105) | `ENOBUFS` | start data of a new game too long |

A frame with a bad CRC gets **no answer at all**, and so does an unknown command in categories `02`–`05`. In
category `01`, an unknown request `01 01 xx` is answered with `EINVAL`; any other second byte gets no answer.
If your client hears nothing, check the frame before assuming the ARC is slow.

Exception: for saved-game queries (`01 01 06 …`), status `FF` simply means there is no save, not an error.

## Protocol version negotiation

The app knows versions 1–5. It starts from the newest:

1. It sends a battery query (`03 02`) with version byte `05`.
2. If the ARC replies with error `00 FF 47`, it drops to version 4 and retries, down to 1. Below 1 it shows
   "the app is too old".
3. The first version the ARC answers normally is remembered and goes into byte 1 of every following frame.

An ARC with firmware 1.0.13 or 1.0.23 speaks **version 5** and rejects version 3 (confirmed).

**Caution (confirmed):** the ARC can take more than 4 s to reply. Only step down on an explicit `FF 47` error,
never on silence. Only a reply carrying the same version byte you sent counts. Otherwise the next command goes
out in the wrong version, and the ARC silently ignores it.

## Communication model

The app works strictly **one request, one response**:

- It keeps a task queue. It sends one request, locks the queue and waits for the response.
- A response is matched to the **last request sent**, not to a command code. Frames carry no request ID.
- The timeout is usually 10 s (initial game state 15 s, protocol version probe 2.5 s). After 5 failed attempts
  the app reports a problem with the ARC.
- A frame that arrives while nothing is waiting for a response is treated as a **board event** (category `02`).
  That is how placed buildings and scanned cards are reported. Details in
  [in-game communication](game.md#board-events).

Your own client should do the same: send, wait for a complete frame, only then send the next one.

## Command list

Payload (without header and CRC) and the ready-made frame for version 5.

### Device info (category `03`)

| command | payload | v5 frame | response (data from offset 5) |
|---|---|---|---|
| ARC ID | `03 01` | `55 05 06 03 01 1C` | 12 B: bytes 0–7 are the ID (LE, displayed as hex), bytes 8–11 are the "boot" value |
| battery | `03 02` | `55 05 06 03 02 15` | 2 B, LE: `value × 0.0004615` = voltage in V |
| firmware | `03 03` | `55 05 06 03 03 12` | 8 B, LE: a number, e.g. `10013`, read as `1.0.13` (zero-padded to 6 digits and split into pairs) |

What the values are:

- **ID**: the nRF52's FICR `DEVICEID`, two 32-bit words.
- **battery**: the raw 14-bit sample of the nRF52 ADC (internal reference, gain 1/4) on input AIN0,
  refreshed periodically by the main loop. The ARC never converts it; the factor is the app's. A reply of `0` means no
  sample has been taken yet.
- **firmware**: the `app_version` field of the Nordic bootloader settings page: the application version of the
  last DFU package installed, or the value written into the settings page when the ARC was programmed. The
  other 4 bytes are reserved (zero). The bootloader compares this number when updating (see
  [firmware update](update.md#the-bootloader)).

Examples (confirmed):

- battery `55 05 08 03 01 BC 34 C6`: `0x34BC × 0.0004615 = 6.23 V`,
- firmware `55 05 0E 03 01 1D 27 00 00 00 00 00 00 59`: `0x271D = 10013`, i.e. **1.0.13**.

The "boot" value (bytes 8–11 of the ID response) changed after a firmware update, while the ID stayed the same.
The app uses it to authenticate a new game (see [game](game.md#new-game)). Most likely it is a counter or
a random value generated at startup.

Older protocol versions had `01` instead of `03` here (e.g. `55 01 06 03 02 4D`).

> **Correction:** in protocol version 1 these commands are the same; only the version byte (and so the CRC)
> differs. In `55 01 06 03 02 4D` the `01` is the version and `03` still the category.

### Operating mode (category `04`)

| command | payload | v5 frame | effect |
|---|---|---|---|
| enter game mode | `04 01 03` | `55 05 07 04 01 03 5D` | response: byte 4 = `01` means the ARC is in game mode |
| enter bootloader (DFU) | `04 01 01` | `55 05 07 04 01 01 53` | the ARC disconnects and comes back as the bootloader. **Confirmed** |
| service mode | `04 01 02` | `55 05 07 04 01 02 5A` | answers OK |
| restart | `04 02` | `55 05 06 04 02 7E` | answers OK, then reboots the ARC about 2 s later |

Mode `01` is DFU, `02` service, `03` game. The DFU command is answered first (`04 01 00`); then the ARC tells
its tasks to quit, waits about 2 s, closes the BLE link, sets the "enter DFU" flag in the nRF52's `GPREGRET` register and resets into the
bootloader.

### Game (category `01`) and board (category `02`)

Described separately in [in-game communication](game.md).

## What is required and what is optional

**Required in every client:**

1. Connect and enable notifications on TX.
2. Negotiate the protocol version. Without it the ARC ignores commands or replies with error `47`.
3. Reassemble fragments and check the CRC.
4. One request at a time.

**Optional** (the app always does it, but the ARC does not require it):

- reading ID, battery and firmware. They are not needed for ordinary queries or for entering DFU.
  Exception: a new game needs the ID, "boot" and battery values (see [game](game.md#new-game)),
- checking for a saved game, fleets and synergies.

**What can be done without the app today (confirmed):** read ID, battery and firmware, switch the ARC into
the bootloader and flash firmware. Playing a game without the app is so far only theory, described from the code.

## How the app talks to the ARC after connecting

Task order after connecting (modules `3488`, `7616`):

1. **protocol version probe** (`03 02`, from version 5 downwards),
2. **ARC ID** (`03 01`),
3. **battery** (`03 02`),
4. **fleets** (`01 01 04 01`, see [game](game.md#fleets)),
5. **saved game**: static, dynamic and initial saved state (`01 01 06 01/02/03 00`),
6. **firmware** (`03 03`). If it is too old, or the server reports an update, the app offers to update.
   Details in [firmware update](update.md),
7. main menu.

When the connection drops mid-game, the app repeats this sequence and then returns to the game (game mode,
modules, load from save and state queries).

## Trying it yourself

Everything marked "confirmed" on this page was done with [`tools/arc.py`](tools/arc.py), a short Python
script built on [`bleak`](https://github.com/hbldh/bleak) (macOS, Linux, Windows):

```
python3 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/arc.py scan              # devices advertising NUS
.venv/bin/python tools/arc.py info ADDRESS      # ID, battery, firmware (read-only)
.venv/bin/python tools/arc.py enter-dfu ADDRESS # switch to the bootloader (asks for confirmation)
```

It negotiates the protocol version, reassembles fragments and checks the CRC, as described above.
On macOS `ADDRESS` is the UUID that `scan` prints, not a MAC address.

Without writing any code you can send the same frames by hand from **nRF Connect** (Nordic Semiconductor):
connect to the ARC, enable notifications on `6E400003-…` and write the frame bytes to `6E400002-…`.

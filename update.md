---
title: Firmware update
---

# ARC firmware update

[← contents](index.md)

## In short

- The ARC is a Nordic nRF52 chip with the **Nordic Secure DFU** bootloader. An update is a standard DFU package
  (a `.zip` with `manifest.json`, a `.bin` image and a signed `.dat` init packet).
- Packages are **signed with the publisher's key**. The bootloader rejects any image without a valid signature.
  You can only flash original firmware, not your own.
- The newest known firmware is **1.0.23**. It is bundled with app 1.3.13 as `www/bhcapp-1.0.23.zip`.
- The publisher's update server is down (as of November 2026), so 1.0.23 is most likely the last version.
- The update can be done **without the official app** (confirmed, 1.0.13 → 1.0.23).

## How the app decides to update

After connecting, the app reads the firmware version (`03 03`, see [protocol](protocol.md)), then:

1. It asks the server: `GET https://exogen.space/bhcapi/?a=fw_status/{ARC_ID}/{FW}/{APP}`. A response of
   `"status": "upgradeable"` means a newer version exists.
2. It asks the server about compatibility: `GET …?a=fw_app/{FW}/{APP}/update.zip` returns `200` (compatible)
   or `409` (incompatible).
3. If the server does not respond, it compares locally: firmware ≥ **1.0.23** (`MIN_FW`) means compatible.
   Older firmware forces an update.

It downloads the package from `…?a=fw/{ARC_ID}/{FW}/{APP}/update.zip`. On a brand-new device it uses
`…?a=fw/first_boot/0.0.0/{APP}/update.zip`. **If the download fails, the app falls back to the bundled
`bhcapp-1.0.23.zip`.**

Here `APP` = `1.3.13`, and `ARC_ID` and `FW` are the values read from the ARC.

### Server status (November 2026)

- `exogen.space` serves Traefik's self-signed default certificate, so the app cannot establish a TLS connection.
- With TLS verification skipped, every `bhcapi` endpoint returns `404 page not found`, i.e. there is no backend.
- The Wayback Machine has no `/bhcapi` URLs archived.

**Possible side effect:** the app may hang at "checking firmware". The code waits for the server
request, so if the request never finishes (we suspect this happens with the broken certificate), the app
never moves on. A workaround that should help, though we have not tested it: **airplane mode with Bluetooth
turned on**. The request should then fail immediately and the app fall back to the local check.
Another option is to point the app at a [replacement server](online.md#replacement-server) that answers
right away.

## The "UPGRADE BLOCKED" gate

Before updating, the app checks two batteries and blocks the update if either is too low:

| blocking condition | threshold |
|---|---|
| ARC voltage, alkaline batteries (default) | < 4.8 V |
| ARC voltage, rechargeable batteries (toggle in settings) | < 4.48 V |
| phone battery | < 25% |

The catch: on modern iOS (and on Apple Silicon Macs), the plugin the app uses to read the phone's battery
returns no value. The app then assumes 0% and **always blocks the update**, even with full batteries in both
the ARC and the phone (confirmed). Changing the battery type in settings does not help.

Bypassing the gate inside the app is not an option: any change to its files breaks the signature, and the
binary is encrypted by the App Store. The only way is a manual update.

## How an update works

The app does this, and the same can be done by hand:

1. **Enter-bootloader command** over NUS: payload `04 01 01`, in version 5 the frame `55 05 07 04 01 01 53`.
2. The ARC **disconnects** and shortly afterwards advertises as a separate device: the name with a **`_DFU`**
   suffix, a **different BLE address**, Secure DFU service `FE59`.
3. A DFU program connects to the `…_DFU` device and sends the `.zip` package. The app does this with Nordic's
   `iOSDFULibrary`, 5 s after sending the command.
4. The bootloader checks the signature, writes the image and starts the new firmware.
5. The app asks you to restart the ARC and reconnects (renegotiating the protocol version from scratch).

If nothing happens for about 2 minutes, the bootloader usually goes back to the old firmware. Then you have to
send the command from step 1 again.

## Manual update (without the Colonies app)

Confirmed in November 2026 on an ARC with firmware 1.0.13. After the update the ARC reports firmware 1.0.23
and the same ID. We sent the commands with [`tools/arc.py`](tools/arc.py) (see [protocol](protocol.md#trying-it-yourself));
the steps below use nRF Connect, which sends the same bytes. With the script, steps 2 and 3 are
`arc.py info ADDRESS` and `arc.py enter-dfu ADDRESS`, and step 6 is `arc.py info ADDRESS` again.

**You need:**

- **fresh batteries in the ARC.** Running out of power mid-flash is the biggest risk,
- the DFU package. Take it from your own copy of the app: the file `www/bhcapp-1.0.23.zip` inside the app
  bundle (on a Mac: `/Applications/Colonies.app/Wrapper/Colonies.app/www/`),
- a phone with **nRF Connect** (to send the command) and **nRF Device Firmware Update** (to upload the
  package). Both are free apps from Nordic Semiconductor. Instead of nRF Connect you can use `arc.py`
  on a computer, or any other BLE tool that can write bytes to a characteristic.

**Steps:**

1. Close the Colonies app on all devices. The ARC accepts only one connection.
2. In nRF Connect, connect to the ARC and enable notifications on characteristic `6E400003-…`.
   Check the battery: write `55 05 06 03 02 15` to characteristic `6E400002-…` and convert the reply
   as described in [protocol](protocol.md). It should be well above 4.8 V for alkaline batteries.
   Write `55 05 06 03 03 12` to read the firmware version. If the ARC replies with `55 05 07 00 FF 47 EF`,
   it does not speak version 5; see protocol version negotiation in [protocol](protocol.md).
3. Switch the ARC into the bootloader: write `55 05 07 04 01 01 53` to `6E400002-…`. The ARC disconnects.
   The version-3 frame `55 03 07 04 01 01 18` will be ignored.
4. Immediately open nRF Device Firmware Update, pick the `.zip` package and the device **with the `_DFU`
   suffix**, not the one without it. If it is not there, go back to step 3.
5. Wait for the upload to finish. Keep the phone close and do not turn the ARC off.
6. Check the result: connect again and read the firmware version (`55 05 06 03 03 12`). It should be `1.0.23`.

After the update, the "boot" value in the ID response (bytes 8–11) changes, while the ARC ID itself stays
the same. Since 1.0.23 is the app's minimum version, the official app should no longer force an update
(from the app code; not tested).

## The bootloader

The ARC uses Nordic's stock **Secure DFU bootloader from nRF5 SDK 16.0.0** with SoftDevice **S140 7.0.1** on an
**nRF52840**.

| setting | value |
|---|---|
| advertised name | `BHCHQ_DFU` (the application advertises as `BHCHQ`) |
| ways in | the `GPREGRET` flag set by the application (`04 01 01`), the buttonless-DFU flag in the bootloader settings (the application never sets it), or a missing or invalid application. Entry by button or pin reset is disabled |
| inactivity timeout | 120 s, then it starts the installed application again (the "about 2 minutes" above) |
| bonding | not required |
| signature | ECDSA P-256 with SHA-256, checked with the nRF52840's CryptoCell. Updates must be signed; at boot only the application's CRC is checked, not its signature |
| **downgrade** | **refused**: a package with a lower application version is rejected. The **same** version is accepted, so re-flashing 1.0.23 over 1.0.23 works |
| package requirements | hardware version 52, SoftDevice requirement `0xCA` (S140 7.0.1) |

The application version the bootloader compares is the number `03 03` reports (`10023` for 1.0.23).

**Memory map** (1 MB flash): MBR and SoftDevice at the bottom, the application from `0x27000` up to the
bootloader (836 KB, of which the top 12 KB are reserved for application data), the bootloader at `0xF8000`, the MBR parameter page at `0xFE000` and the bootloader settings page at `0xFF000`.

**Recovering a bricked ARC.** As long as the bootloader works and the installed version is not newer than
1.0.23, the ARC can be put back on 1.0.23 over BLE. Programming over SWD (the nRF52's debug interface) bypasses
the bootloader and its checks, but needs access to the SWD signals on the board (not documented here) and a
full flash image (SoftDevice, bootloader, settings page and application).

## What we don't know

- Whether the per-ARC packages from the server (`fw/{ARC_ID}/…`) differed from the `first_boot` package
  and from the bundled one. The bundled 1.0.23 worked on the unit we tested.
- Whether the bootloader allows flashing an older version. Secure DFU usually forbids it. **Correction:** it does
  not: older versions are refused, only the same or a newer version is accepted (see
  [the bootloader](#the-bootloader)).
- Whether any version newer than 1.0.23 existed. If you have a different DFU package for the ARC, please open an issue in this repository.

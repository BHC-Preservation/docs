---
title: Online services
---

# Online services and what was lost

[← contents](index.md)

Everything here comes **from the app code** (modules `3488`, `7616`, `9036`, `9073`, `4263`) plus a check of
the publisher's servers in November 2026.

## Summary

The app needs the network for very little. Game rules, planets, artwork, texts and sounds all ship inside the
app, and the colony itself runs on the ARC. The server was only used for firmware updates, a version check,
bug reports and an unfinished "backer registration". **No gameplay content was ever downloaded.**

What is really gone:

1. **Firmware newer than 1.0.23.** The app ships 1.0.23 as a fallback. If the server ever handed out
   anything newer, it was not archived.
2. **The Exogen metagame link** that was supposed to unlock fleets and extra planets. It was announced in
   the app's texts but never switched on (see [game setup](setup.md)).
3. **Tutorial videos.** The app opens them in the browser through short links on the publisher's domain.
   That domain now resolves to `127.0.0.1` (checked against public DNS) and the Wayback Machine has no copies.

## Endpoints

Base URL: `https://exogen.space/bhcapi/` (a hidden developer switch changes it to `https://dev.exogen.space/bhcapi/`).
The action goes in the `a` query parameter, e.g. `?a=fw_status/…`. Requests use plain `fetch` or jQuery
`ajax` with no certificate pinning.

| request | method | when | what the app does with it | if it fails |
|---|---|---|---|---|
| `fw_status/{ARC_ID}/{FW}/{APP}` | GET | after every connection | `status == "upgradeable"` offers a firmware update | ignored |
| `fw_app/{FW}/{APP}/update.zip` | GET | after every connection | HTTP 200 = app and firmware compatible, 409 = not | falls back to a local check (firmware ≥ 1.0.23) |
| `fw/{ARC_ID}/{FW}/{APP}/update.zip` | GET | firmware update | DFU package for this ARC | uses the bundled 1.0.23 |
| `fw/first_boot/0.0.0/{APP}/update.zip` | GET | update of an ARC without an ID | DFU package | uses the bundled 1.0.23 |
| `app/version/android/{APP}` | GET | never (the function exists but nothing calls it) | `current` / `upgradeable` | — |
| `app/log/{ARC_ID}` | POST | "Report bug" in settings; automatically on the "app too old" screen if analytics is on | sends a bug report, shows the returned report ID | error message |
| `registration_status/{ARC_ID}/{TOKEN}` | GET | "ARC registration" (debug builds only) | `registered` / `registerable` | error message |
| `registration/{TOKEN}` | PUT | confirming the registration | binds the ARC to a backer token | error message |

`APP` is the app version (`1.3.13`), `FW` the firmware version (e.g. `1.0.23`), `ARC_ID` the 16 hex digit ID.

### Bug report contents

`app/log` sends a form field `LOGS` with JSON: timestamp, ARC ID, backer token, firmware and app version,
phone model and OS, screen size, sound and battery settings, **the whole `localStorage`**, the app's internal
logs and the list of rounds of the current game. Worth knowing if anyone ever revives the endpoint.

### Backer registration

A backer token has the form `XXXXX-XXXXX-XXXXX-XXXXX` (optionally a fifth group), letters and digits.
The menu entry exists only in debug builds and only when the ARC is connected and not yet registered.
The app's own text says the binding was meant "for troubleshooting and for incoming CAMPAIGN MODE".
Registration unlocks nothing in this app version: it only stores `isArcRegistered` and the token in
`localStorage`.

## Server status (2026-11-15)

- `exogen.space` serves a self-signed "Traefik default" certificate, and every `bhcapi` path returns
  `404 page not found`. The backend is gone.
- Because nothing gameplay-related depends on the server, the app keeps working as long as its requests
  fail quickly. If the app hangs on "checking firmware", turn off the phone's internet access (airplane mode
  with Bluetooth on).

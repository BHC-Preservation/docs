---
title: ARC — unofficial documentation
---

# ARC: unofficial documentation

**ARC** is the electronic unit from the board game *Beyond Humanity: Colonies* (Three Headed Monster).
It talks to the *Colonies* companion app over Bluetooth Low Energy. The ARC computes the colony state;
the app only displays it and collects the players' moves.

App version 1.3.13 has not been updated since 2023, and the publisher's update server no longer responds.
This documentation exists so that the ARC can be used (read, updated and, some day, maybe played with)
without the official app.

## Contents

1. **[BLE protocol](protocol.md)**: frame format, how the app talks to the ARC, what is required and what is optional.
2. **[In-game communication](game.md)**: what flows between the ARC and the app, from a new game, through rounds, to the end of a match.
3. **[Firmware update](update.md)**: how updates work, why the app blocks them, and how to update manually.

## Where this comes from

- Analysis of the JavaScript code of app 1.3.13. It is a Cordova app, and all logic lives in the unencrypted
  `www/js/index.min.js`, obfuscated with obfuscator.io. We decoded it with `webcrack`.
  Where it matters, we give the webpack module number, e.g. `5891`.
- Tests on a real ARC (November 2026): reading device info, entering the bootloader and updating firmware
  1.0.13 → 1.0.23 without the official app.

We distinguish two levels of confidence:

- **confirmed**: verified on the device,
- **from the app code**: follows from code analysis but has not been tested on an ARC yet.

## Disclaimers

- This project is not affiliated with the publisher. Game and device names belong to their owners.
- This site describes the protocol and contains no app code, firmware or game artwork.
- The commands in the update section can brick the device if something goes wrong (e.g. batteries dying
  mid-flash). You do this at your own risk.

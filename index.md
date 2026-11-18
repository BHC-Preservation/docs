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

**New (November 2026):** you can [build the app yourself](app.md) from your own copy: same game code, a fresh
native shell for current iOS, no dependency on the publisher's servers.

## Contents

1. **[BLE protocol](protocol.md)**: frame format, how the app talks to the ARC, what is required and what is optional.
2. **[In-game communication](game.md)**: what flows between the ARC and the app, from a new game, through rounds, to the end of a match.
3. **[Firmware update](update.md)**: how updates work, why the app blocks them, and how to update manually.
4. **[Game setup](setup.md)**: planets and their effects, auxiliary fleets, managers, and traces of the planned metagame.
5. **[Scenarios and difficulty](scenarios.md)**: the hidden scenario mode (21 scenarios), how to turn it on, and what planet difficulty changes.
6. **[NFC cards and tokens](cards.md)**: manager, decree, directive, ambassador, governor and fleet cards, their IDs and the rules the app applies.
7. **[Online services](online.md)**: everything the app requested from the publisher's server, what was lost with it,
   and a [replacement server](online.md#replacement-server) you can run yourself.
8. **[Build the app yourself](app.md)**: turn your own copy of the app into one you build, sign and debug, for current iOS (Android and Fire: outline only, [see here](app.md#android-and-amazon-fire)).

## Where this comes from

- Analysis of the JavaScript code of app 1.3.13. It is a Cordova app, and all logic lives in the unencrypted
  `www/js/index.min.js`, obfuscated with obfuscator.io. We decoded it with `webcrack`.
  Where it matters, we give the webpack module number, e.g. `5891`.
  To get the same code from your own copy of the app, see [Build the app yourself](app.md).
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

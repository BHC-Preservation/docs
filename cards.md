---
title: NFC cards and tokens
---

# NFC cards and tokens

[← contents](index.md)

The ARC has an NFC reader. Players tap physical cards and tokens on it to register campaigns, decrees,
directives and the ambassador, to confirm who did what, and to undo moves. This page collects what the app
knows about those cards: their types, ID ranges and names, the rules the app enforces when one is tapped,
and how the result reaches the ARC.

Almost everything here comes **from the app code** (modules `1089`, `2432`, `465`, `194`, `3420`, `7562`,
`9943`, `7133`). Nothing about the cards themselves has been tested on a device yet. Only the frame format
and CRC (see [protocol](protocol.md)) and the fleet availability list (see [game setup](setup.md#auxiliary-fleets))
are **confirmed**. Frames are given for protocol version 5.

## How a tapped card reaches the app

The app never talks to the NFC reader. The ARC reads the card and sends a **board event**: an unsolicited
frame with category `02` (byte 3). The app's notification router (module `2432`) treats a complete frame as
an event when no request of its own is waiting for an answer and byte 3 is `02`. It strips the header and the
CRC and passes the data from offset 5 to `routerUserAction` (module `1089`).

```
55 05 <len> 02 <status> <data…> <crc8>
                        └─ data[0] = 01 building connected
                           data[0] = 02 NFC card, data[1] = card type, data[2…] = card value
```

Two details from the router are worth knowing if you write your own client:

- A frame whose byte 4 is `FF` is treated as an ARC error, not as an event.
- Events are only recognised while the app is not waiting for a response. An event that arrives while a
  request is pending would be handed to that request's parser. A client of your own should match responses
  to requests by category, not by timing alone.

### Card types

`nfcRouter` (module `1089`, ~l. 1604) switches on `data[1]`. The constants are exported as `NFC_PLAYER`,
`NFC_DECREE`, `NFC_GOVERNOR`, `NFC_AMBASSADOR` and `NFC_FLEET`.

| data | constant | card | handler |
|---|---|---|---|
| `02 01 <id>` | `NFC_PLAYER` = 1 | manager card (the app's texts call it the "manager token") | `nfcActionPlayer` |
| `02 02 <id>` | `NFC_DECREE` = 2 | decree (1–200) or directive (201–209) | `nfcActionDecree` |
| `02 03 01` | `NFC_GOVERNOR` = 3 | governor token | `nfcGovernorOrAmb` → `governorAction` |
| `02 03 <other>` | `NFC_AMBASSADOR` = 3 | ambassador card | `nfcGovernorOrAmb` |
| `02 04 <bytes…>` | `NFC_FLEET` = 4 | fleet card | `fleetNfcAction` (logs only) |
| anything else | | | logged as "Didn't recognized NFC type" |

The governor and the ambassador share type `3`; the value `1` means governor and any other value means
ambassador. The app's own simulation of the ambassador card uses value `2`.

For types 1–3 the app reads a **single byte** (`data[2]`). For the fleet card it passes **all bytes from
`data[2]` to the end**, so the fleet card is the only type with a multi-byte value.

### Service mode

Settings → **Service mode** (available in release builds, module `465`) is a hardware test screen: "Here, You
can check your hardware (decrees, modules, etc.)". While it is open, every board event goes to
`onUserAction` instead of the game logic, and the screen shows the type, ID and name of what was tapped or
plugged in. `getNfcType` and `getNfcName` show how the app classifies each card:

| type byte | value | shown as | name |
|---|---|---|---|
| 1 | any | Manager | manager name |
| 2 | 1–200 | Decree | decree name (or "free" for IDs without a name) |
| 2 | > 200 | Directive | directive name |
| 3 | 1 | Governor token | (none) |
| 3 | other | Ambassador | (none) |
| 4 | any | (empty) | (empty) |

Service mode is the easiest way to map a physical card to its ID with the official app: open it, tap the
card, read the ID. A fleet card shows an empty type and name, and the ID field shows only the first value byte.

## IDs and names

### Managers (type 1)

IDs 1–9 (module `7562`, class `Manager`). The constructor accepts `0`–`9` and `255`; `255` is the solo
player, which has no card.

| ID | role | name | directive |
|---|---|---|---|
| 1 | Preacher | Art Chen | 209 Pilgrimage |
| 2 | Racketeer | Ava Xu | 203 Hidden stash |
| 3 | Engineer | Paul Bloch | 206 Humanoid subroutines |
| 4 | Inventor | Boris Artyomov | 207 The Discovery Program |
| 5 | Warden | Lucas Johannes | 208 State of Emergency |
| 6 | Explorer | Giselle Carter | 204 Private expedition |
| 7 | Broker | Mac McCain | 205 Offshore account |
| 8 | Major | Athena Gore | 201 War! |
| 9 | Visionary | Vlad Pokorny | 202 Promised Land |

### Directives (type 2, IDs 201–209)

One per manager, listed above. The app's names have the form "Athena Gore - War!" (keys `directive_201` to
`directive_209`, module `7133`); artwork is `DIR_001` to `DIR_009`. What a directive does is decided by the
ARC; the app only has its name.

### Decrees (type 2, IDs 1–200)

The decree class (module `3420`, export `nX`) gives names to **IDs 1–108** (keys `decree_1` to `decree_108`)
and artwork `DEC_001` to `DEC_108`. Any other ID in 1–200 is accepted by the game logic but gets the name
"free" and no artwork. We found no decree data beyond 108 in the app: no names, no descriptions, no effects.
The app does not describe what a decree does; the ARC resolves it and reports it in the
[dynamic state](game.md#dynamic-state-01-01-03-02).

The class also overrides the decree's type by ID: **1–65 become type 2 and 66–108 type 1**, `255` (ambassador)
type 4, everything else type 3 (directive). The app shows a "support" icon next to decrees 1–65 when one is
registered. What the two groups mean in the board game is not stated in the code. (The dynamic state has
per-player counters for "green" and "red" decrees, but the app does not link them to these ranges.)

The app also has 200 short citizen comments shown after a decree vote (`decCom_1` to `decCom_200`, module
`4939`). Those are comment IDs, not decree IDs. Each comment lists the decrees (all within 1–108) and
colony conditions it applies to.

Decrees 1–65:

| ID | decree | ID | decree | ID | decree |
|---|---|---|---|---|---|
| 1 | Private agricultural expansion | 23 | Return bodies to Terra | 45 | Colony monitoring |
| 2 | Colony research enterprise | 24 | Pro bono government | 46 | Discounted license purchase |
| 3 | Greenery habitats | 25 | Respect civil rights | 47 | Shorter work shifts |
| 4 | Mortgage subsidy | 26 | Accelerated government | 48 | Research budget cuts |
| 5 | Issue back bonds | 27 | Guest ID cards | 49 | AI Rapid Court bails |
| 6 | Lowering taxes | 28 | Strict customs | 50 | Tourism program |
| 7 | Tax the wealthy | 29 | Fire preparedness plan | 51 | Immigration promotional campaign |
| 8 | Colony summit | 30 | Free work clothes | 52 | Industrial preference |
| 9 | Colony fair | 31 | Live streamed court sessions | 53 | Geological surveys |
| 10 | Chain gang | 32 | Assistants control bureau | 54 | Urban development |
| 11 | Free EV transportation | 33 | Federal intervention | 55 | Organic home farms |
| 12 | Free communication network | 34 | The Chronicle newspaper | 56 | Recycling program |
| 13 | Colonist training program | 35 | Colony radio station | 57 | Free health program |
| 14 | Right to arms | 36 | Federal news channel | 58 | Accumulators technical inspection |
| 15 | SimStim education program | 37 | Superconductor approval | 59 | Independence funding program |
| 16 | After-hours militia | 38 | The R&D commission | 60 | Side consultations |
| 17 | Marines recruitment program | 39 | Political transparency | 61 | Inventory checkout |
| 18 | Disaster relief security funds | 40 | Due diligence | 62 | Colonial Guard Force creation |
| 19 | Governor elections | 41 | Private liability | 63 | Military pilots civil contracts |
| 20 | Colony holiday | 42 | A 3d printer in every home | 64 | Technician preference |
| 21 | Free SimStim program | 43 | Communication satellite | 65 | Public science consulting act |
| 22 | Serving the community | 44 | Improving constitutional rights |  |  |

Decrees 66–108:

| ID | decree | ID | decree | ID | decree |
|---|---|---|---|---|---|
| 66 | Building permits | 81 | Research frontrunners | 96 | Census |
| 67 | Food rationing | 82 | Prisoners as private contractors | 97 | Contraception ban |
| 68 | Paid healthcare | 83 | Closed court sessions | 98 | Closed environment |
| 69 | Prohibition | 84 | Terran consulate | 99 | Hired guns |
| 70 | Private military contract | 85 | Background investigations | 100 | Additional technical shifts |
| 71 | Terran debt | 86 | Budget cuts | 101 | Stricter customs |
| 72 | Expedition leader | 87 | Big Brother program | 102 | Water distribution strategy |
| 73 | Legalize narcotics | 88 | Social engineering | 103 | Immunization program |
| 74 | Legalize gambling | 89 | Additional payments | 104 | Genetically modified crops |
| 75 | Smoking ban | 90 | Political upheaval | 105 | Stem-cell research permit |
| 76 | Amnesty | 91 | SimStim from Terran Republic | 106 | Gene modification permit |
| 77 | Curfew | 92 | SecForce duties expansion | 107 | Multilayered storage system |
| 78 | Military drills | 93 | Deregulated pressure standards | 108 | Additional research budget |
| 79 | Secret Militia | 94 | Lowering constitutional standards |  |  |
| 80 | Home imprisonment | 95 | Observation satellite |  |  |

### Governor token and ambassador (type 3)

- **Governor token** (`02 03 01`): opens the **undo** screen. It is not an action and is never sent to the ARC.
- **Ambassador** (`02 03 <other>`): becomes a type 2 action with value `FF` (255). The app names it
  "Ambassador"; its text says it removes one Terran dependence.

## Rules the app enforces

All of these are checks in the app (module `1089` unless noted). The ARC is only told the final list of
actions at the end of the round, so a client of your own has to apply the same rules or accept that the ARC
may receive moves the app would have refused. Whether the ARC checks any of them itself is unknown.

### Always

| rule | where |
|---|---|
| While service mode is open, cards only show their ID. | `routerUserAction` → `465` `onUserAction` |
| **25 actions per round.** At 25, every board event shows "maximum actions exceeded" and is dropped. | `routerUserAction` (~l. 1498) |
| While a decree, directive, ambassador or building waits for confirmation, only manager cards are accepted. | `nfcRouter` (~l. 1604) |
| Cards are ignored while a popup is open, outside the game screen, or on the round summary. Manager cards are checked for registration and confirmation first, so they still work in those cases. | `isScreenOccupied` (~l. 1807) |

The 25-action message tells players to use the governor token to undo. The limit check runs before the card
type is looked at, so as written the governor token is blocked by the same check. This is how the code reads;
it has not been tried in a game.

### Manager card

| situation | result |
|---|---|
| player registration screen | adds the manager to the game: at most 5, no duplicates, at least 2 to continue (`handleRegisterPlayers`) |
| multiplayer, manager not in this game | "Wrong manager" popup (`incorrectManager`) |
| multiplayer, a move is waiting for confirmation | **confirms** that move for this player (`handlePlayerConfirmation`) |
| otherwise | registers a **campaign** for this player (action type 1) |
| solo | any manager card registers a campaign for the solo player (`255`) |

In multiplayer modes, a decree, directive, ambassador or building is not registered until a player taps their
own manager card ("register manager token to confirm identity"). On confirmation the app refuses a second
action of the same type by the same player in this round ("player cannot register more actions of the same
type"; `playerRegisteredSimilarAction`, ~l. 1801). An earlier ambassador is excluded from that count. Because
decrees and directives share action type 2, **a player gets one decree or one directive per round, not both**.
Campaigns are not limited this way.

### Decree and directive card

| rule | mode | where |
|---|---|---|
| No decrees or directives in the **last round** ("Cannot register decree or directive on last round"). Not checked in scenarios. | all | `nfcActionDecree` (~l. 1840) |
| The same decree ID cannot be registered twice in a round. | multiplayer | `isDecRegistered` (~l. 1943) |
| A directive (201–209) can only be confirmed by **its owner**. Anyone else gets "Wrong manager tried to register action". IDs 210–254 always fail this check. | multiplayer | `confirmDecDir` (~l. 1731), `isDirectiveCorrect` (~l. 1033) |
| IDs up to 200 are accepted from any player. | multiplayer | `confirmDecDir` |
| **No directives** in solo. | solo | `nfcActionDecree` |
| **One decree per round** for the solo player. | solo | `nfcActionDecree` |

In solo there is no confirmation step: the decree is registered at once.

### Ambassador card

| rule | where |
|---|---|
| Only **once per round**. | `nfcGovernorOrAmb` (~l. 1898) |
| Only while the colony has at least one **Terran dependence** (special state from the static state); otherwise ignored ("No TD, ambassador not needed"). | `nfcGovernorOrAmb` |
| Multiplayer: needs a manager card to confirm. Solo: registered at once for player `255`. | `nfcGovernorOrAmb`, `confirmDecDir` |

The ambassador is not blocked in the last round. The same-type check on confirmation is asymmetric: a player
who has already sent the ambassador can still play a decree, but a player who has already played a decree or
directive cannot confirm the ambassador, because the check counts their existing type 2 actions other than
the ambassador.

### Governor token

Opens "Undo action": a list of all actions registered this round. Players tap the ones to remove and confirm
(`governorAction`, ~l. 1072). The same token is the documented way to undo actions restored after a lost
connection ("if you wish to undo them, use governor token").

## How actions reach the ARC

Nothing is sent to the ARC when a card is tapped. The app collects actions (class `Action`, module `9943`) and
sends them all with "end round" (`01 01 02 01`, see [in-game communication](game.md#round)). Each action is
5 bytes: type, player, data, parent, legs.

| card | type | player | data |
|---|---|---|---|
| manager (campaign) | `01` | manager ID, `FF` in solo | `00` |
| decree | `02` | confirming manager, `FF` in solo | decree ID |
| directive | `02` | its owner | 201–209 (`C9`–`D1`) |
| ambassador | `02` | confirming manager, `FF` in solo | `FF` |
| governor, fleet | not sent | | |

Bytes 3 and 4 (parent and legs) are `00` for all card actions.

Example end-of-round frames (CRC checked with the script from [protocol](protocol.md#frame)):

| round | frame |
|---|---|
| player 3 played decree 13 | `55 05 0E 01 01 02 01 01 02 03 0D 00 00 74` |
| player 8 played directive 201 (War!) | `55 05 0E 01 01 02 01 01 02 08 C9 00 00 D8` |
| player 2 sent the ambassador | `55 05 0E 01 01 02 01 01 02 02 FF 00 00 D8` |
| solo: ambassador | `55 05 0E 01 01 02 01 01 02 FF FF 00 00 25` |
| player 3: campaign, then decree 13 | `55 05 13 01 01 02 01 02 01 03 00 00 00 02 03 0D 00 00 1A` |

### Simulating a card

Module `194` contains test functions that ask the ARC to simulate a board event: command `05 01` followed by
16 bytes of event data (zero-padded). The app's code never calls the decree, governor and ambassador variants;
the manager variant is called only from debug helpers. There is no fleet card variant.

| simulated card | function | v5 frame |
|---|---|---|
| manager 3 | `playerCard` | `55 05 16 05 01 02 01 03 00 00 00 00 00 00 00 00 00 00 00 00 00 1E` |
| decree 13 | `decreeCard` | `55 05 16 05 01 02 02 0D 00 00 00 00 00 00 00 00 00 00 00 00 00 AB` |
| directive 201 | `decreeCard` | `55 05 16 05 01 02 02 C9 00 00 00 00 00 00 00 00 00 00 00 00 00 00` |
| governor token | `governorCard` | `55 05 16 05 01 02 03 01 00 00 00 00 00 00 00 00 00 00 00 00 00 BE` |
| ambassador | `ambassadorCard` | `55 05 16 05 01 02 03 02 00 00 00 00 00 00 00 00 00 00 00 00 00 96` |

Most likely the ARC answers by sending the event back as if the card had been tapped. We have not seen what
the ARC actually sends for a simulated or a real card (frame length, status byte, padding).

> **Correction:** the ARC first answers `05 01 00`, then about 1 s later sends the event as if the card had
> been tapped. The request must be exactly 22 bytes long and the event type must be `01` (building) or `02`
> (card), otherwise the answer is `05 FF 16` (`EINVAL`). Only one simulation can be pending at a time
> (`05 FF 10`, `EBUSY`). A request whose second byte is not `01` gets no answer. A simulated card skips the
> checks a real one gets (type range and CRC).
>
> The event frame is always 22 bytes: `55 <ver> 16 02 01 <event type> <15 bytes> <crc>`. Byte 4 (`01`) is not
> a status but the subcommand "callback". For a card, the 15 bytes are the card record's bytes 0–14 (the card's
> own CRC is dropped); for a building see [board events](game.md#board-events). Unused bytes are zero.

## Fleet cards

What the app does with a fleet card (`02 04 …`):

- `fleetNfcAction` (~l. 792) writes the value bytes to the console and does nothing else. Like other cards,
  it is ignored when a popup is open or the game screen is not active.
- Service mode shows it with an empty type and name.
- The app has no code that writes to a card, unlocks a fleet on the ARC, or moves a fleet between ARCs.
  **No transfer mechanism exists in the app.**

What the app's texts promise (info screen, `infoScreen_fleetTxt_*`): fleets are earned in the Exogen
metagame, "saved on your ARC module, not in your app", tied to the corporation's profile "unless you use the
fleet cards to trade or transfer them to another player", and all of it would be enabled after most game sets
had been delivered. That never happened.

What is **confirmed**: a real ARC on firmware 1.0.23 reports fleets 1–10 as available and the other slots as
locked (see [game setup](setup.md#what-a-real-arc-reports-confirmed)). How the other fleets would be unlocked
is unknown.

On the ARC side the picture is different (see [the card record](#the-card-record)): the firmware can **write**
a record to a card when asked over BLE, not only read one. So the card side of the transfer the texts promise
was built into the ARC; only the app side that would trigger it is missing.

## The card record

This section comes **from static analysis of firmware 1.0.23**, not from the app. It has not yet been checked
against a real card.

### Reader and tags

- The ARC's reader is an **NXP MFRC522** (or its FM17522 clone), the common 13.56 MHz ISO 14443A reader.
- The firmware talks to tags with the MIFARE Ultralight / NTAG command set: READ (`0x30`, 16 bytes from a page)
  and COMPATIBILITY WRITE (`0xA0`, 4 bytes per page). Game cards are therefore most likely **NTAG21x or
  MIFARE Ultralight** tags, which any phone with NFC can read. **Correction:** the reader driver reads
  without MIFARE Classic authentication, so it works only with Ultralight-compatible tags (MIFARE Ultralight,
  NTAG).

### Layout

The ARC reads **16 bytes starting at page 8** (pages 8–11) and checks them before passing them on:

| byte | content |
|---|---|
| 0 | card type, must be **1–5**, otherwise the card is rejected |
| 1–14 | data for that type (the ID and anything else; exact layout not known yet) |
| 15 | **CRC-8 of bytes 0–14**: polynomial `0x07`, initial value `0x00`, the same CRC as BLE frames |

There is **no encryption or signature**. A record with the right type byte and CRC is accepted.

The ARC does not interpret the record. It only checks the type range and the CRC, then forwards bytes 0–14
unchanged to the app as a board event: `55 05 16 02 01 02 <type> <bytes 1–14> <crc>`. Everything after that is
the app's job. Bytes 2–14 are ignored by both the firmware and app 1.3.13 (the app only logs them for fleet
cards), so what real cards store there can only be learned by reading them.

> **Correction:** on all cards bytes 2–14 are zero (see [what the cards contain](#what-the-cards-contain)).

| type | meaning (app) | byte 1 |
|---|---|---|
| 1 | manager card | manager ID |
| 2 | decree or directive | decree ID (201–209 = directive) |
| 3 | governor token or ambassador | `1` = governor, anything else = ambassador |
| 4 | fleet card | logged only |
| 5 | **nothing**: accepted by the ARC, but app 1.3.13 logs it as an unknown card type. **Correction:** the firmware's ambassador card type | — |

Type 5 has no meaning anywhere in firmware 1.0.23 or app 1.3.13; it was most likely reserved for something
that never shipped.

> **Correction:** type 5 is the firmware's separate **ambassador card** type. The ambassador ended up as type 3
> with value 2, which is what the app expects, but the ARC still accepts type 5.

### What the cards contain

Every card record has the same simple form: **type, one value byte, 13 zero bytes, CRC-8**.

| card | record (pages 8–11) |
|---|---|
| manager 1–9 | `01 <id> 00…00 <crc>`, e.g. manager 3: `01 03 00 00 00 00 00 00 00 00 00 00 00 00 00 9D` |
| decree 1–108 | `02 <id> 00…00 <crc>`, e.g. decree 13: `02 0D 00 … 00 28` |
| directive 201–209 | `02 <id> 00…00 <crc>`, e.g. War! (201): `02 C9 00 … 00 83` |
| governor token | `03 01 00 … 00 3D` |
| ambassador | `03 02 00 … 00 15` |
| fleet 1–4 | `04 <fleet> 00…00 <crc>`, e.g. fleet 1: `04 01 00 … 00 3F` |

The ID is the single byte 1. Bytes 2–14 are zero on every card type, fleet cards included.

To make a replacement card, write such a record to pages 8–11 of a blank NTAG/Ultralight tag with a phone. The CRC is the one from [protocol](protocol.md#frame).

### All card records

Every record is 16 bytes: byte 0 (type), byte 1 (ID), bytes 2–14 `00`, byte 15 (CRC). The tables give bytes 0,
1 and 15. For example decree 13 is `02 0D 00 00 00 00 00 00 00 00 00 00 00 00 00 28`.

**Managers, governor, ambassador, fleets**

| card | byte 0 | byte 1 | CRC |
|---|---|---|---|
| manager 1: Art Chen | `01` | `01` | `50` |
| manager 2: Ava Xu | `01` | `02` | `78` |
| manager 3: Paul Bloch | `01` | `03` | `9D` |
| manager 4: Boris Artyomov | `01` | `04` | `28` |
| manager 5: Lucas Johannes | `01` | `05` | `CD` |
| manager 6: Giselle Carter | `01` | `06` | `E5` |
| manager 7: Mac McCain | `01` | `07` | `00` |
| manager 8: Athena Gore | `01` | `08` | `88` |
| manager 9: Vlad Pokorny | `01` | `09` | `6D` |
| governor token | `03` | `01` | `3D` |
| ambassador | `03` | `02` | `15` |
| fleet 1: Light bulk carrier fleet | `04` | `01` | `3F` |
| fleet 2: Research Vessel | `04` | `02` | `17` |
| fleet 3: Terran bulk carrier fleet | `04` | `03` | `F2` |
| fleet 4: Orbital solar array | `04` | `04` | `47` |

Fleet cards exist only for fleets 1–4.

**Directives** (type `02`)

| directive | byte 1 | CRC |
|---|---|---|
| 201 War! | `C9` | `83` |
| 202 Promised Land | `CA` | `AB` |
| 203 Hidden stash | `CB` | `4E` |
| 204 Private expedition | `CC` | `FB` |
| 205 Offshore account | `CD` | `1E` |
| 206 Humanoid subroutines | `CE` | `36` |
| 207 The Discovery Program | `CF` | `D3` |
| 208 State of Emergency | `D0` | `21` |
| 209 Pilgrimage | `D1` | `C4` |

**Decrees 1–108** (type `02`, byte 1 = decree ID; names in [decrees](#decrees-type-2-ids-1200))

| ID | b1 | CRC | ID | b1 | CRC | ID | b1 | CRC | ID | b1 | CRC |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `01` | `88` | 28 | `1C` | `B7` | 55 | `37` | `56` | 82 | `52` | `35` |
| 2 | `02` | `A0` | 29 | `1D` | `52` | 56 | `38` | `DE` | 83 | `53` | `D0` |
| 3 | `03` | `45` | 30 | `1E` | `7A` | 57 | `39` | `3B` | 84 | `54` | `65` |
| 4 | `04` | `F0` | 31 | `1F` | `9F` | 58 | `3A` | `13` | 85 | `55` | `80` |
| 5 | `05` | `15` | 32 | `20` | `99` | 59 | `3B` | `F6` | 86 | `56` | `A8` |
| 6 | `06` | `3D` | 33 | `21` | `7C` | 60 | `3C` | `43` | 87 | `57` | `4D` |
| 7 | `07` | `D8` | 34 | `22` | `54` | 61 | `3D` | `A6` | 88 | `58` | `C5` |
| 8 | `08` | `50` | 35 | `23` | `B1` | 62 | `3E` | `8E` | 89 | `59` | `20` |
| 9 | `09` | `B5` | 36 | `24` | `04` | 63 | `3F` | `6B` | 90 | `5A` | `08` |
| 10 | `0A` | `9D` | 37 | `25` | `E1` | 64 | `40` | `82` | 91 | `5B` | `ED` |
| 11 | `0B` | `78` | 38 | `26` | `C9` | 65 | `41` | `67` | 92 | `5C` | `58` |
| 12 | `0C` | `CD` | 39 | `27` | `2C` | 66 | `42` | `4F` | 93 | `5D` | `BD` |
| 13 | `0D` | `28` | 40 | `28` | `A4` | 67 | `43` | `AA` | 94 | `5E` | `95` |
| 14 | `0E` | `00` | 41 | `29` | `41` | 68 | `44` | `1F` | 95 | `5F` | `70` |
| 15 | `0F` | `E5` | 42 | `2A` | `69` | 69 | `45` | `FA` | 96 | `60` | `76` |
| 16 | `10` | `17` | 43 | `2B` | `8C` | 70 | `46` | `D2` | 97 | `61` | `93` |
| 17 | `11` | `F2` | 44 | `2C` | `39` | 71 | `47` | `37` | 98 | `62` | `BB` |
| 18 | `12` | `DA` | 45 | `2D` | `DC` | 72 | `48` | `BF` | 99 | `63` | `5E` |
| 19 | `13` | `3F` | 46 | `2E` | `F4` | 73 | `49` | `5A` | 100 | `64` | `EB` |
| 20 | `14` | `8A` | 47 | `2F` | `11` | 74 | `4A` | `72` | 101 | `65` | `0E` |
| 21 | `15` | `6F` | 48 | `30` | `E3` | 75 | `4B` | `97` | 102 | `66` | `26` |
| 22 | `16` | `47` | 49 | `31` | `06` | 76 | `4C` | `22` | 103 | `67` | `C3` |
| 23 | `17` | `A2` | 50 | `32` | `2E` | 77 | `4D` | `C7` | 104 | `68` | `4B` |
| 24 | `18` | `2A` | 51 | `33` | `CB` | 78 | `4E` | `EF` | 105 | `69` | `AE` |
| 25 | `19` | `CF` | 52 | `34` | `7E` | 79 | `4F` | `0A` | 106 | `6A` | `86` |
| 26 | `1A` | `E7` | 53 | `35` | `9B` | 80 | `50` | `F8` | 107 | `6B` | `63` |
| 27 | `1B` | `02` | 54 | `36` | `B3` | 81 | `51` | `1D` | 108 | `6C` | `D6` |

A tag whose SAK byte is `04` is ignored. The ARC also reads the tag's UID before every read or write, but the
record is what identifies the card.

### Writing

The firmware can write a 16-byte record to pages 8–11 of the card on the reader, retrying up to 20 times.
The write is requested **over BLE**, with a category `02` command the app never sends:

```
55 05 15 02 02 <15 bytes: type + bytes 1–14> <crc>
```

The ARC computes the record's own CRC (byte 15) itself and does not check the type byte when writing. Only one
write can be pending at a time. A client other than the app could therefore use the ARC itself to write cards,
for example to recreate a lost card. This has not been tried on a device.

### Consequences for preservation

- A lost or damaged card can most likely be **recreated on a blank NTAG/Ultralight tag** by writing the same
  16 bytes to pages 8–11. That needs the original record (read it from the card) or the layout of bytes 1–14.
  **Correction:** it can, and no original is needed: every record is in [all card records](#all-card-records).
- The ARC could in principle store a fleet on a card and read it back, which is what the promised fleet trade
  would need.

## What is unknown

- **What real cards store in bytes 2–14**, especially fleet cards (type 4).
- **The exact event frames** the ARC sends (length, status byte, padding), and whether the ARC sends events
  outside game mode.
- **Whether the ARC enforces any of the rules above** or accepts any action list it is given.

> **Correction:** bytes 2–14 are zero on every card ([all card records](#all-card-records)). The event frames
> are described in [simulating a card](#simulating-a-card). The ARC sends card events in any mode, and it
> does not de-duplicate: every successful read of the reader loop (which runs about once a second) is sent as a
> new event. The rules the ARC itself checks are listed in [what the ARC checks](game.md#round).

How to find out:

1. Read pages 8–11 of real cards with a phone. Check that byte 0 is the card type and byte 15 the CRC-8 of
   bytes 0–14, then compare cards of the same type to find the ID byte(s).
   - **iPhone:** *NFC Tools* (Read shows tag type and memory; *Other → Advanced NFC commands* can send the raw
     READ command `30 08`) or *NXP TagInfo*, which dumps the whole memory.
   - **Android:** *NXP TagInfo* (full memory dump per page) or *NFC Tools*.
2. Tap the same cards on the ARC in service mode (or with a BLE client that prints every category `02` frame)
   to pair each record with the ID the ARC reports.
3. Do not write to original cards. Experiment on blank NTAG213 tags.

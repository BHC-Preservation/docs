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
a record to a card on request from its game engine, not only read one. So the transfer mechanism the texts
promise was at least partly built into the ARC; only the app side that would trigger it is missing.

## The card record

This section comes **from static analysis of firmware 1.0.23**, not from the app. It has not yet been checked
against a real card.

### Reader and tags

- The ARC's reader is an **NXP MFRC522** (or its FM17522 clone), the common 13.56 MHz ISO 14443A reader.
- The firmware talks to tags with the MIFARE Ultralight / NTAG command set: READ (`0x30`, 16 bytes from a page)
  and COMPATIBILITY WRITE (`0xA0`, 4 bytes per page). Game cards are therefore most likely **NTAG21x or
  MIFARE Ultralight** tags, which any phone with NFC can read.

### Layout

The ARC reads **16 bytes starting at page 8** (pages 8–11) and checks them before passing them on:

| byte | content |
|---|---|
| 0 | card type, must be **1–5**, otherwise the card is rejected |
| 1–14 | data for that type (the ID and anything else; exact layout not known yet) |
| 15 | **CRC-8 of bytes 0–14**: polynomial `0x07`, initial value `0x00`, the same CRC as BLE frames |

There is **no encryption or signature**. A record with the right type byte and CRC is accepted.

Card types 1–4 match the board events the app knows (manager, decree/directive, governor/ambassador, fleet).
**Type 5 is accepted by the ARC but unknown to the app.**

A tag whose SAK byte is `04` is ignored. The ARC also reads the tag's UID before every read or write, but the
record is what identifies the card.

### Writing

The firmware's reader loop can write a 16-byte record (15 data bytes plus the CRC it computes) to pages 8–11 of
the card on the reader, retrying up to 20 times. The write is requested by the ARC's game engine. Which game
action triggers it, and what it writes, is not known yet. No BLE command in the app requests a write.

### Consequences for preservation

- A lost or damaged card can most likely be **recreated on a blank NTAG/Ultralight tag** by writing the same
  16 bytes to pages 8–11. That needs the original record (read it from the card) or the layout of bytes 1–14.
- The ARC could in principle store a fleet on a card and read it back, which is what the promised fleet trade
  would need.

## What is unknown

- **The layout of bytes 1–14** for each card type, especially fleet cards (type 4) and type 5.
- **When the ARC writes a card** and what it writes.
- **The exact event frames** the ARC sends (length, status byte, padding), and whether the ARC sends events
  outside game mode.
- **Whether the ARC enforces any of the rules above** or accepts any action list it is given.

How to find out:

1. Read pages 8–11 of real cards with a phone. Check that byte 0 is the card type and byte 15 the CRC-8 of
   bytes 0–14, then compare cards of the same type to find the ID byte(s).
   - **iPhone:** *NFC Tools* (Read shows tag type and memory; *Other → Advanced NFC commands* can send the raw
     READ command `30 08`) or *NXP TagInfo*, which dumps the whole memory.
   - **Android:** *NXP TagInfo* (full memory dump per page) or *NFC Tools*.
2. Tap the same cards on the ARC in service mode (or with a BLE client that prints every category `02` frame)
   to pair each record with the ID the ARC reports.
3. Do not write to original cards. Experiment on blank NTAG213 tags.

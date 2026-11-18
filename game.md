---
title: In-game communication
---

# In-game communication

[← contents](index.md)

Everything on this page comes **from the app code** (mainly modules `5891`, `1089`, `2432`, `4244`). It has
not yet been verified on an ARC without the official app. Frames are given for protocol version 5. The frame
format is described in [protocol](protocol.md).

## Who does what

- **The ARC is the game engine.** It stores the colony state, resolves the round (population, resources,
  economy, riots, end of game) and keeps the save in memory. The app does not compute rules; it asks for results.
- **The board is a network of modules.** Physical buildings plug into the ARC and into each other (by "legs").
  The ARC knows what is connected and where. It also reads NFC cards (players, decrees, ambassador, governor).
- **The app is the interface.** It collects the players' moves during a round, shows summaries and artwork,
  and at the end of the round sends all moves at once.

```
         ┌──────────── events (NFC card, new building) ────────────┐
 ARC ────┤                                                         ├──► app
         └──◄── state queries / "end round" with the action list ──┘
```

## Dictionaries

### Game type

| value | mode |
|---|---|
| 1 | semi-coop |
| 2 | coop |
| 3 | solo |
| 130 | scenario coop |
| 131 | scenario solo |
| 129 | reserved |

### Players (managers)

IDs 1–9 are the manager characters from the game. ID `255` (`FF`) is the player in solo mode. `0` is an empty seat.

### Buildings (modules)

| ID | building | ID | building |
|---|---|---|---|
| 0 | ARC | 17 | Nuclear Power Plant |
| 1 | Industrial Dome | 18 | Temporary Residential Cubes |
| 2 | Automatic Well | 19 | Academy |
| 3, 4 | Solar Power Plant | 20 | Health & Sports Center |
| 5 | Landing Pad | 21 | Hangar |
| 6 | Storage | 22 | Test Chamber |
| 7 | Community Dome | 23 | Community Tower |
| 8, 9, 10 | Residential Dome | 24 | Consulate |
| 11 | Life Support System | 25 | Laboratory |
| 12 | Gas & Liquids Tanks | 26 | Bunker |
| 13 | Atmospheric Synthesizer | 27 | Terran Embassy |
| 14 | Hydroponics Dome | 28 | Obelisk |
| 15 | Technical Zone | 29 | Spaceport |
| 16 | Security Dome | 30 | Prison Dome |
| | | 31 | Cryogenic Cubes |
| | | 32 | Galactic Marketplace |

Buildings 21–31 are available only to specific managers. The app enforces this itself; the ARC does not.

### Decrees and directives

A decree card has an ID of 1–255. IDs 201–209 are **directives** (not available in solo). ID `255` in a
"decree" action means the **ambassador**.

## Game flow

### New game

Once the players have chosen the mode, planet, fleet and managers, the app sends in order:

| # | request | payload | v5 frame |
|---|---|---|---|
| 1 | enter game mode | `04 01 03` | `55 05 07 04 01 03 5D` |
| 2 | list connected modules | `02 03` | `55 05 06 02 03 07` |
| 3 | **new game** | `01 01 01 01` + start data | (variable) |
| 4 | **authentication** | `01 01 01 04` + 16 B MD5 | (variable) |
| 5 | synergies | `01 01 03 05` | `55 05 08 01 01 03 05 F1` |
| 6 | static state | `01 01 03 01` | `55 05 08 01 01 03 01 ED` |
| 7 | dynamic state | `01 01 03 02` | `55 05 08 01 01 03 02 E4` |
| 8 | initial state | `01 01 03 03` | `55 05 08 01 01 03 03 E3` |

The app will not send a new game, authentication or state queries until the ARC confirms game mode
(step 1 already happens when entering the game setup screen).

#### Start data (command `01 01 01 01`)

| offset | size | field |
|---|---|---|
| 0 | 4 | start time, unix timestamp in seconds, LE |
| 4 | 1 | game type |
| 5 | 2 | planet: quadrant X, LE |
| 7 | 2 | planet: quadrant Y, LE |
| 9 | 1 | planet: system X |
| 10 | 1 | planet: system Y |
| 11 | 1 | planet: ID |
| 12 | 1 | fleet (ID, `0` = none) |
| 13 | 5 | players: manager IDs, empty seats are `0`. Solo: `FF 00 00 00 00` |
| 18 | … | scenario configuration (length byte + records, see [scenarios](scenarios.md#configuration-format)). Outside scenarios a single `00` byte |

With no planet selected the app sends defaults: quadrant (10, 27010), system (50, 50), ID 3.

#### Authentication (command `01 01 01 04`)

Right after the new game the app sends an MD5 hash (16 B):

```
MD5( start data zero-padded to 222 B
   ‖ ARC ID (8 B from the 03 01 response)
   ‖ battery (2 B, raw data of the last 03 02 response)
   ‖ boot (4 B, bytes 8–11 of the 03 01 response) )
```

ARC ID, battery and "boot" must come from the same session (the app reads them on every connection).
It looks like a guard against a client that has not talked to this particular ARC first.
We do not know what the ARC does if this step is skipped.

### Continuing a saved game

The ARC keeps the save itself. After connecting, the app asks for it with three commands:

| request | payload | v5 frame |
|---|---|---|
| save: static state | `01 01 06 01 00` | `55 05 09 01 01 06 01 00 64` |
| save: dynamic state | `01 01 06 02 00` | `55 05 09 01 01 06 02 00 5B` |
| save: initial state | `01 01 06 03 00` | `55 05 09 01 01 06 03 00 4E` |

The responses have the same layout as the regular states (below). Status `FF` means there is no save. If there
is a save and the game has not ended, the menu shows "continue". The app then sends:

1. game mode `04 01 03`,
2. module list `02 03`, and asks the players to plug in missing buildings (compared against the save),
3. **load save** `01 01 01 02 00` + the current timestamp (4 B, LE),
4. synergies and the three states, same as for a new game.

### Round

During a round the app only **collects board events** (cards, buildings) and builds an action list from them.
Nothing goes to the ARC until the players end the round. Actions can be undone, and the app also keeps them in
phone storage in case the connection drops.

Ending the round is a single command with the whole list:

```
01 01 02 01  <action count>  <action 1: 5 B>  <action 2: 5 B> …
```

Action (5 B):

| byte | field |
|---|---|
| 0 | type: `1` campaign, `2` decree / directive / ambassador, `3` building |
| 1 | player ID (1–9, `FF` in solo) |
| 2 | data: `0` for a campaign, the decree ID for a decree (`FF` = ambassador), the building ID for a building |
| 3 | building: ID of the parent building it was attached to. `0` for other actions |
| 4 | building: legs, upper 4 bits are the parent's leg, lower 4 bits the new building's leg. `0` for other actions |

The limit is 25 actions per round.

Example: a round with no actions is `55 05 09 01 01 02 01 00 CF`. A single "decree 13 in solo" action is
`55 05 0E 01 01 02 01 01 02 FF 0D 00 00 9F`.

After the ARC confirms, the app fetches synergies and the three states (as above) and shows the round summary.

### End of game

The end of the game is signalled by the dynamic state (`hasEnded`, result and reason, below). The app then
computes the score and sends **ARC lights**:

| effect | payload | v5 frame |
|---|---|---|
| win | `02 04 FF 01` | `55 05 08 02 04 FF 01 FF` |
| loss | `02 04 FF 02` | `55 05 08 02 04 FF 02 F6` |

## Board events

The ARC sends these on its own, without a request, in a frame with category `02`. Data from offset 5:

| data | event |
|---|---|
| `01 <building> <parent> <legs>` | a building was connected. Legs as in the action: upper 4 bits are the parent's leg, lower the building's |
| `02 01 <player>` | manager card: the player's campaign (or player registration on the player selection screen) |
| `02 02 <decree>` | decree or directive card |
| `02 03 01` | governor token |
| `02 03 <other>` | ambassador card (needed only under Terran dependence) |
| `02 04 …` | another NFC card type. The app only logs it |

The app filters events by the rules: no duplicate buildings, one decree per round and no directives in solo,
no decrees in the last round, ambassador only once. In multiplayer modes the app waits for a player to tap
their manager card to assign a building or decree to them.

Card types, IDs and the full rule set are described in [NFC cards and tokens](cards.md).

### Simulating events

The app has hidden test functions that send the ARC command `05 01` + 16 B of event (format as in the table
above, zero-padded). For example, "player 3 tapped their card" is the frame
`55 05 16 05 01 02 01 03 00 00 00 00 00 00 00 00 00 00 00 00 00 1E`. Most likely the ARC then sends it back
as a regular event, which is handy for testing without a board.

## Response structures

Offsets are counted from the start of the data (frame offset 5). Single-byte signed values are int8;
two-byte values are LE (signed where noted).

### Static state (`01 01 03 01`)

| offset | field |
|---|---|
| 0 | current round |
| 1 | number of rounds |
| 2 | special-state flags, bit 0 = least significant: 0 catastrophe, 1 overcrowding, 2–4 riots, 5–7 Terran dependence |
| 3, 4, 5 | happiness, security, technical state (int8) |
| 6, 7, 8 | a second value for each of those three indicators (int8, most likely the change) |
| 10–15 | migration: colonists, security force, marines, scientists, prisoners, total (int8) |
| 22–31 | population (u16): colonists 22, security force 24, marines 26, scientists 28, prisoners 30 |
| 32 | number of citizens (u16) |
| 34–43 | population change since the previous round (int16), same groups in the same order |
| 46 | colony capacity (u16) |
| 86–89 | resources, usage: power, gas, liquids, life support |
| 90–93 | resources, maximum (same order) |
| 94–97 | accumulators, maximum |
| 98–101 | accumulators, usage |
| 102, 104 | stock: two values (int16) |
| 106–110 | income: taxes, other, modules, construction, import (int8) |

### Dynamic state (`01 01 03 02`)

| offset | field |
|---|---|
| 0 | number of buildings in the build queue |
| 1–108 | up to 18 buildings, 6 B each (below) |
| 109 | number of active decrees |
| 110–133 | up to 6 decrees, 4 B each: ID, type, state byte (upper 5 bits: manager, lower 3: state), percent |
| 134 | current occurrence (event) ID (u16) |
| 141 | end-of-game timestamp (u32) |
| 149 | game ended (0/1) |
| 150 | result: `2`, `3` = win, `4` = loss |
| 151 | reason: `1` depopulation, `5` Terran dependence, `6` riots |
| 152 | DT (int8) |
| 157 | vote in progress (0/1) |
| 158 | vote type |
| 159 | score (int16) |
| 161–210 | up to 5 players, 10 B each: manager, points, president, green decrees, red decrees, campaigns, modules, directives, ambassador, order of command points |

Building in the queue (6 B): ID, build progress in %, then a 32-bit LE bit field. From the most significant bit:

| bits | field |
|---|---|
| 4 | reserved |
| 2 | completed |
| 3 | parent's leg |
| 3 | building's leg |
| 6 | parent ID |
| 2 | tier |
| 5 | `tol` (meaning unknown) |
| 5 | counter |
| 2 | state |

### Initial state (`01 01 03 03`)

The same data the app sent for the new game (timestamp, type, planet, fleet, players, configuration),
222 B. This lets the app rebuild the game after reconnecting.

### Module list (`02 03`)

Byte 0 is the number of modules, then 3 B per module: building ID, parent ID and the legs byte.

**Caution:** for this response the app reads the legs the other way round than in the event (lower 4 bits as
the parent's leg). Either the firmware really encodes them differently here, or it is a bug in the app.
This needs checking on a device.

### Synergies (`01 01 03 05`)

Byte 0 is the number of synergies, then 2 B pairs: type (`1` minor, `2` major, `3` epic) and synergy ID.

### Fleets

Request `01 01 04 01` (frame `55 05 08 01 01 04 01 86`). Response: one byte per fleet slot.
Value `2` means the fleet is available, `1` locked. The app reads only the first 25 slots.
**Confirmed** on firmware 1.0.23: the ARC sends 150 slots, fleets 1–10 are `2` and the rest `1`, and it
answers outside game mode too. See [game setup](setup.md#auxiliary-fleets).

Unlock `01 01 04 02 <slot>` and lock `01 01 04 03 <slot>` (slot = fleet − 1) change the table; the reply is
`01 01 00`. **Confirmed** with fleet 11 (`55 05 09 01 01 04 02 0a bb` → `55 05 07 01 01 00 94`). The change is
stored in the ARC's EEPROM. See [how fleets are granted](setup.md#how-fleets-are-granted-firmware-analysis-unlock-confirmed).

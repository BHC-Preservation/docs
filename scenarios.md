---
title: Scenarios and difficulty
---

# Scenarios and difficulty

[← contents](index.md)

App 1.3.13 contains a nearly complete **scenario mode**: 21 scenarios, each with its own planet, rules, win and
loss conditions and a start configuration for the ARC. The release build hides it. This page describes what the
app code contains (modules `5183`, `9546`, `6606`, `7616`, `8736`, `9073`), how firmware 1.0.23 runs a scenario
(static analysis of the firmware, November 2026), how to turn scenarios on in a rebuilt app, and how the planet
**difficulty** levels work. Nothing about scenarios has been tested on an ARC yet.

## Why scenarios are not visible

Two gates hide them:

1. **Main menu.** The global config has a constant `_scenariosEnabled = false` (module `9073`). The main menu
   (`8736`) only shows the "scenarios" entry when that flag is on, the ARC is connected and its firmware is
   compatible.
2. **Scenario list.** Each scenario has an `isAvailable` flag (`5183`). Outside debug builds the picker lists only
   the available ones (`6606`). Seven are marked available: **1, 7, 9, 11, 12, 17, 19**.

The rebuilt app can lift the first gate with
[`setup.sh --unlock-scenarios`](https://github.com/BHC-Preservation/app-rebuild#scenarios---unlock-scenarios).
It changes the flag and nothing else, so the picker still shows only the seven available scenarios.

Firmware 1.0.23 does support scenario games (see [How the ARC runs a scenario](#how-the-arc-runs-a-scenario)),
but this has not been tried on a device.

## The scenarios

| ID | title | available | difficulty | rounds | tracker | start buildings | config |
|---|---|---|---|---|---|---|---|
| 0 | Tutorial | no | 0 | – | – | – | empty |
| 1 | Wrath Of Ares | **yes** | 3 | 12 | asteroid distance, 12 → 0 | 5 | 129 B |
| 2 | Authority | no | 2 | 20 | offenses against the Republic, 0 → 3 | – | 49 B |
| 3 | Den of Thieves | no | 2 | 20 | obscured capital, 0 → 100 | – | 29 B |
| 4 | Artifact Hunters | no | 2 | 20 | – | – | empty |
| 5 | Angel's Peak | no | 3 | 10 | time left, 10 → 0 | 6 | 109 B |
| 6 | Ghost Colony | no | 3 | 20 | – | 7 | 96 B |
| 7 | Behind Bars | **yes** | 2 | 12 | time left, 0 → 12 | 5 | 87 B |
| 8 | Epidemic Embargo | no | 2 | 20 | cure research, 0 → 100 | 7 | 110 B |
| 9 | Money Train | **yes** | 1 | 20 | list of requirements, 0 → 5 | 7 | 106 B |
| 10 | Messiah | no | 2 | 20 | – | 5 | 54 B |
| 11 | The Lord Cometh | **yes** | 3 | 12 | time until arrival, 12 → 0 | 5 | 100 B |
| 12 | Colonial Olympics | **yes** | 1 | 12 | Olympics start, 12 → 0 | 5 | 93 B |
| 13 | Terran Exodus | no | 2 | 20 | refugees saved, 0 → 100 | 5 | 97 B (header says 100) |
| 14 | Haywire | no | 1 | 20 | – | – | 6 B |
| 15 | The Petard | no | 2 | 10 | borehole depth, 0 → 10 | 5 | 102 B |
| 16 | War Machine | no | 2 | 20 | marines sent, 0 → 30 | – | 20 B |
| 17 | Clouds of Bermuda | **yes** | 2 | 20 | – | – | 14 B |
| 18 | A Friend in Need | no | 2 | 20 | orders fulfilled, 0 → 5 | – | 25 B |
| 19 | First To Stars | **yes** | 1 | 20 | – | – | **empty** |
| 20 | Boiling Point | no | 2 | 20 | current strength, 15 → 30 | 7 | 117 B |

- **difficulty** is the scenario's own 0–3 rating. The picker sorts by it and nothing else uses it. It is unrelated
  to the planet difficulty below.
- **rounds** comes from the scenario's rule text. The app reads the actual round limit from the ARC, like in a
  standard game.
- **tracker** is the "doom tracker" shown during the game: name, start value and goal.
- **start buildings**: the modules the players must connect before the game starts (always a basic set: well,
  solar plant, residential dome, life support, atmospheric synthesizer, sometimes more).
- **config** is the scenario configuration sent to the ARC (below). Scenarios 0, 4 and 19 have none. Scenario 19 is
  marked available anyway; it would start as a plain coop or solo game with the default rules.
- Some scenarios name obligatory managers (1: two, 7: one, 12: four) and suggested managers.
  Scenario 4 asks at the end for the number of fully researched artifacts: the players win with at least 3 per
  player (9 in solo).

## How a scenario game starts

1. "scenarios" in the main menu → the picker (`6606`) → the players choose **coop** (game type `130`) or **solo**
   (`131`), see [game types](game.md#game-type).
2. Three intro screens: story, special rules / win and loss conditions, setup notes (managers, decrees, modules).
3. The planet is the scenario's own (module `9546`, e.g. "Training Facility" for the tutorial). The app sends
   coordinates `0x7FFF`, `0x7FFF`, `0xFF`, `0xFF` and the **scenario ID** as the planet ID.
4. If the scenario has start buildings, a popup asks the players to connect them. The ID of each connected building is
   written into the configuration in place of the building name (`getConfig`, `7616`).
5. New game (`01 01 01 01`) with the configuration as the start-data tail, see
   [start data](game.md#start-data-command-01-01-01-01). Outside scenarios that tail is a single `00`.

### Configuration format

The first byte is the number of bytes that follow. Then come records:

```
[category] [sub] [length] [length bytes of data]
```

The record types the scenarios use:

| record | length | used in | meaning (from the firmware) |
|---|---|---|---|
| `01 05`, `01 06`, `01 07` | 1 | 2, 15 | unknown. **Correction:** `01 05` is meant as the Terran dependence at the start (bits 0–4 counter, bit 5 active), but the ARC never copies it into the game state, so it has no effect; `01 06`, `01 07` unknown |
| `03 0e` | 7 | most | **start building**: slot (0–17), building ID, construction progress (≤ 100), position. The app writes the connected building's ID into the second byte |
| `03 0a`, `03 0b` | 7 | 1 | properties of a building type, unknown. **Correction:** **migration tendencies of a building type** for tier 1 / tier 2: building type, then colonists, security, marines, scientists, prisoners, total (signed bytes; their sum also adds to the migration amount, the total byte is ignored) |
| `04 05`, `04 06` | 3 | 3, 5, 6, 14, 15 | colony status (happiness / security / technical), probably start values. **Correction:** `04 05` is a **permanent offset** added every round (default `0, 0, −5`), `04 06` the values at the start |
| `05 01` | 15 | 2 | a decree definition: decree ID + 14 bytes. **Correction:** **redefine a decree**: decree index, type, the requirement/effect counts (low / high 4 bits), then six (type, value) pairs, the same block format as the event in the [dynamic state](game.md#dynamic-state-01-01-03-02) |
| `06 01` … `06 09` | 2–6 | most | **end-of-game conditions and the tracker**, see below |
| `09 05` | 12 | most | **start population**: six signed 16-bit values in hundreds of people (colonists, security, marines, scientists, prisoners, total) |
| `09 02`, `09 07`, `09 08` | 1–6 | 1, 7, 8, 10, 13, 16, 20 | unknown. **Correction:** `09 02` (1 B) is a constant added to migration every round, `09 07` (6 B) the base migration weights (colonists, security, marines, scientists, prisoners, total); `09 08` unknown |
| `0a 0f`, `0a 10`, `0a 11` | 1–2 | most | unknown |

The firmware also has category `0d` (events: force an event in a given round, redefine a standard event), which no
scenario uses. An unknown record or a wrong length makes the ARC refuse the game. Scenario 13's length byte (100)
does not match its data (97 bytes), so that scenario most likely fails to start; it is not available anyway.

More records exist that the scenarios do not use:

| record | length | setting | default |
|---|---|---|---|
| `01 01` … `01 04` | 1 | catastrophe, overcrowding, riot stage 1, riot stage 2 at the start (bits 0–4 counter, bit 5 active) | 0 |
| `02 01`, `02 02`, `02 03` | 1 | Cryogenic Cubes: chance in %, stock gained, prisoner units used | 30, 10, 1 |
| `03 01`, `03 02`, `03 03` | 2 | building type, then: build time / special function / population group hit by a catastrophe | |
| `03 04`, `03 05` | 6 | building type, then power, gas, liquids, life support, stock (in tenths), tier 1 / tier 2 | |
| `03 06`, `03 07` | 9 | building type, then storage capacity and fill for power, gas, liquids, life support, tier 1 / tier 2 | |
| `03 08`, `03 09` | 4 | building type, then happiness, security, technical, tier 1 / tier 2 | |
| `03 0c`, `03 0d` | 3 | building type, then capacity normal / overcrowded, tier 1 / tier 2 | |
| `03 0f` | 1 | rounds added once, at the start, to the build time of every building type whose build time is not 0 | 0 |
| `03 10` | 1 | extra buildings hit by every catastrophe | 0 |
| `04 01` … `04 04` | 1 | colony status weights: population on happiness, security force on security, prisoners on security, colonists on technical | 1, 10, 10, 10 |
| `05 02` | 2 | decree index, then `−1` to disable that decree | |
| `08 01` | 4 | rounds with a score poll (bit mask) | rounds 6, 12, 18, 24 |
| `09 01` | 1 | life support per population (stored, but not used) | 5 |
| `09 03` | 1 | chance in % per round that a unit becomes a prisoner while security is negative | 10 |
| `09 04` | 1 | chance in % per prisoner unit to be released (every second round) | 20 |
| `09 06` | 2 | base capacity, normal and overcrowded | 0, 0 |
| `0a 01` | 1 | unused | 0 |
| `0a 02` … `0a 06` | 1 | tax per unit in hundredths: colonists, scientists, security force, marines, prisoners | 12, 24, 0, 0, 0 |
| `0a 07` … `0a 0a` | 1 | loss in % per round: power, life support, gas, liquids | 2, 2, 0, 0 |
| `0a 0b` | 6 | base balance of power, gas, liquids, life support (signed bytes) and starting stock (int16; only the low byte is used) | −5 each, 30 |
| `0a 0c` | 8 | base storage capacity × 4 and fill × 4 | 0 |
| `0a 0d` | 1 | stock cost per unfinished building, per round | 5 |
| `0a 0e` | 1 | stock bonus per round while under Terran dependence | 30 |
| `0c 01` | 1 | campaign effect (`1` decree, `2` happiness, `3` technical, `4` security), but the ARC ignores it: a campaign always raises the player's decree chance and score | 1 |
| `0d 01` | 3 | force an event: round (1 B), event ID (u16; only the low byte is stored) | |
| `0d 02` | 15 | redefine an event: event index (u16), then the 13-byte requirement/effect block | |

Categories: `01` special states, `02` building network (Cryogenic Cubes settings), `03` buildings, `04` colony status, `05` decrees,
`06` end of game, `07` players, `08` score poll, `09` population, `0a` resources, `0b` tracker (no settings), `0c` actions,
`0d` events.

## How the ARC runs a scenario

From a static analysis of firmware 1.0.23. Not tested on a device.

- **Game type.** A scenario is bit 7 of the game type: `0x82` (130) is coop, `0x83` (131) is solo. Semi-coop with bit
  7 is rejected, and so is a fleet in a scenario. Apart from that a scenario plays like coop or solo, with one
  difference: the coop/solo "not enough points" loss is skipped.
- **Configuration.** The records are parsed in **every** new game, not only in scenarios. Each category is a group
  of settings with default values that give the standard game; a record overrides one of them. When a saved game is
  loaded, the records are not parsed again, so a loaded scenario game probably runs with the default rules
  (to be checked on a device).
- **Scenario ID.** The ARC uses the ID for two things only: the scenario planet (built in for IDs 0–20; any other ID
  makes the ARC refuse the game) and the scenario events 1001–1084 (four built-in events for each scenario 0–20).
  Everything else (tracker, win, loss) comes from the configuration.

### End-of-game conditions (`06 01` … `06 08`)

| record | setting | default |
|---|---|---|
| `06 01` | population threshold (16-bit) | 150 |
| `06 02` | **win 1** condition mask (result 2) | `0x0f` |
| `06 03` | number of completed modules | 15 |
| `06 04` | round limit (no scenario changes it) | 20 |
| `06 05` | points threshold | 1 |
| `06 06` | loss threshold (16-bit, −1 = depopulation) | −1 |
| `06 07` | **loss** condition mask (result 4) | `0x31` |
| `06 08` | **win 2** condition mask (result 3) | `0` |

The masks are 32-bit (4 bytes LE). Each bit is a built-in condition; when it is met, the game ends with that result
and the bit's reason code:

| bit | condition | reason |
|---|---|---|
| 0 | population vs the threshold | 1 |
| 1 | number of completed modules | 2 |
| 2 | points (coop/solo outside scenarios) | 3 |
| 3 | round limit reached | 4 |
| 4 | third Terran dependence | 5 |
| 5 | third month of riots | 6 |
| 6 | tracker ≤ minimum | 8 |
| 7 | tracker ≥ maximum | 7 |
| 8 | security above 3 | 9 |
| 9–14 | combinations written for particular scenarios (e.g. bit 13: a set of buildings completed and all colony statuses ≥ 0, the Colonial Olympics goal) | 10–15 |

Conditions are checked once per round, tracker first, then loss, win 1 and win 2; a later result overrides an
earlier one, so a win beats a loss in the same round.

### The tracker (`06 09`)

```
06 09 06 | enabled (1) | max | min | start | up rule | down rule
```

All values are signed bytes. The app only sends this record at the start and never touches the tracker again.
The ARC sets the value to `start`, updates it **once per round** (at "end round", `01 01 02 01`) and reports it in
byte 152 of the [dynamic state](game.md#dynamic-state-01-01-03-02). Reaching `max` or `min` ends the game only if
the matching mask bit (7 or 6) is set.

| rule | up | down | used by |
|---|---|---|---|
| 0 | – | – | |
| 1 | +1 every round | −1 every round | up: 7, 15; down (countdowns): 1, 5, 11, 12 |
| 2 | +1 per active decree of certain types | −1 for the same | 2 |
| 3 | +1 when a certain counter grows (orders, probably) | −1 likewise | 18 |
| 4 | while security is negative, + the sum of some colony values | – | 3 |
| 5 | grows with one population group | – | 8 |
| 6 | = the number of completed modules from a fixed set (Industrial Dome, Landing Pad, Storage, Tanks, Temporary Residential Cubes) | – | 9 |
| 7 | = the population | – | 13 |
| 8 | + marines | – | 16 |
| 9 | +1 per active decree of one type | −1 per decree of another type, −1 while security > 0, minus one population group | 20 |

Down rules 4–8 do not exist. Some rule details (which decrees, which counters) are still inferred from scenario texts.

### Events

The ARC picks the round's event in this order: an event forced for this round (category `0d`), then a random one
among the current scenario's events 1001–1084 whose conditions are met (many depend on the tracker value or the
round), then a random standard event. Each event fires at most once per game.

### During and after the game (app)

- The decree rule "no decrees or directives in the last round" does not apply ([cards](cards.md)).
- The app has texts and news posts for events 1001–1084 and shows them only in scenario games (`3118`).
- The end screen shows the scenario's own win/loss text.

## Writing your own scenario

The app side is simple. A scenario is a data entry, and a [rebuilt app](app.md) can add or change one with a diff
on the deobfuscated modules (`setup.sh --from-deob --patch=FILE`):

| what | where |
|---|---|
| scenario entry: ID, `isAvailable`, difficulty, title and text keys, tracker (name, range, multiplier), start buildings, obligatory and suggested managers, `config` | module `5183` |
| planet with the same ID (name, parameters, artwork) | module `9546` |
| texts (`scenario_<ID>_…`) in each language | module `7133` |
| artwork `img/scenarios/s_<ID>.jpg` (picker) and `l_<ID>.jpg`, splash background class `.bg<ID>` | `www/img`, `www/css/style.min.css` (CSS exists for 0–20 only) |

The ARC decides what is possible. With the configuration alone a scenario can set:

- the tracker: min, max, start, one of 9 up rules and 4 down rules;
- any combination of the 15 condition bits for loss, win 1 and win 2, and the thresholds (population, modules,
  round limit, points);
- the start population and up to 18 start buildings;
- building types, decree definitions and standard event definitions, and a forced event for a given round
  (category `0d`, events up to 255).

It cannot add new rules, new conditions, new events 1001+, or use an ID above 20. A new scenario has to borrow an
ID from 0–20 and gets that scenario's planet and its four events with it. The app's planet table (`9546`) must
then match the borrowed ID.

Before any of this: check on a real ARC that an original scenario starts at all.

## Planet difficulty

Every planet in the standard list has one of seven difficulty levels: very easy, easy, normal, hard, very hard,
extreme, nightmare ([planet parameters](setup.md#planet-parameters)). The difficulty is **not sent** to the ARC.
Only the planet coordinates are, and the ARC presumably derives everything from them.

In the app the difficulty only sets a **victory point modifier**, shown on the planet screen and the end screen in
coop and solo games (not in semi-coop or scenarios). The table is `VP_MODS` (module `9073`):

| difficulty | VP modifier |
|---|---|
| very easy | 150 |
| easy | 125 |
| normal | 100 |
| hard | 75 |
| very hard | 50 |
| extreme | 25 |
| nightmare | 0 |

There is no difficulty setting apart from the choice of planet (and, in scenarios, the choice of scenario).

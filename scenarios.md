---
title: Scenarios and difficulty
---

# Scenarios and difficulty

[← contents](index.md)

App 1.3.13 contains a nearly complete **scenario mode**: 21 scenarios, each with its own planet, rules, win and
loss conditions and a start configuration for the ARC. The release build hides it. This page describes what the
code contains (modules `5183`, `9546`, `6606`, `7616`, `8736`, `9073`), how to turn it on in a rebuilt app, and
how the planet **difficulty** levels work. Everything here comes **from the app code**. Nothing about scenarios
has been tested on an ARC yet.

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

**Open question:** it is unknown whether firmware 1.0.23 handles scenario games. Firmware strings contain no
"scenario" text. The app, however, has texts for scenario-only ARC events (occurrences 1001–1084, below), which
suggests the ARC side was at least planned.

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
  marked available anyway, so it probably starts as a plain game, or fails.
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

The record types used (category/sub, data length):

| record | length | used in | notes |
|---|---|---|---|
| `01 05`, `01 06`, `01 07` | 1 | 2, 15 | |
| `03 0a`, `03 0b`, `03 0e` | 7 | most | `03 0e` carries a start building: the app puts the connected building's ID in byte 2 of the data |
| `04 05`, `04 06` | 3 | 3, 5, 6, 14, 15 | |
| `05 01` | 15 | 2 | |
| `06 01` | 2 | 1 | |
| `06 02`, `06 07`, `06 08` | 4 | most | |
| `06 09` | 6 | most | |
| `09 02` | 1 | 1 | |
| `09 05` | 12 | most | |
| `09 07` | 6 | 7 | |
| `09 08` | 1 | 8, 10, 13, 16, 20 | |
| `0a 0f` | 2 | most | |
| `0a 10`, `0a 11` | 1, 2 | 18 | |

The meaning of the records is not known yet; it is decided by the firmware. Scenario 13's length byte (100) does not
match its data (97 bytes), a mistake in the app's table. That scenario is not available anyway.

### During and after the game

- The decree rule "no decrees or directives in the last round" does not apply ([cards](cards.md)).
- ARC events (occurrences) 1001–1084 are scenario-only: the app has their texts and news posts and shows those only
  in scenario games (`3118`).
- The game ends like a semi-coop game: the ARC reports win (result 2 or 3) or loss. The end screen shows the
  scenario's own win/loss text.

## Who runs a scenario: app or ARC

The app only **presents** a scenario. Everything that decides the game comes from the ARC:

- the tracker value: byte 152 of the [dynamic state](game.md#dynamic-state-01-01-03-02) (signed). The app only shows it next to the
  scenario's tracker name and range (`dtSummaryScreen`, `6606`);
- win or loss and its reason (bytes 149–151), and the round limit;
- the scenario events 1001–1084.

So the scenario **rules** live in the firmware: built in and selected by the scenario ID (sent as the planet ID),
driven by the configuration records, or both. Which of these it is has not been checked yet.

## Writing your own scenario

The app side is simple. A scenario is a data entry, and a [rebuilt app](app.md) can add or change one with a diff
on the deobfuscated modules (`setup.sh --from-deob --patch=FILE`):

| what | where |
|---|---|
| scenario entry: ID, `isAvailable`, difficulty, title and text keys, tracker (name, range, multiplier), start buildings, obligatory and suggested managers, `config` | module `5183` |
| planet with the same ID (name, parameters, artwork) | module `9546` |
| texts (`scenario_<ID>_…`) in each language | module `7133` |
| artwork `img/scenarios/s_<ID>.jpg` (picker) and `l_<ID>.jpg`, splash background class `.bg<ID>` | `www/img`, `www/css/style.min.css` (CSS exists for 0–20 only) |

The ARC side is the hard part, and it decides what is possible:

1. **Re-telling an existing scenario** (same ID and `config`, new story, texts or start buildings): app-only, works
   as far as the original scenario works.
2. **New ID with an existing scenario's `config`**: shows whether the ARC cares about the ID. If it ignores the ID
   and follows the records, new scenarios can be put together from the known records.
3. **New rules**: needs the meaning of the configuration records, i.e. analysis of how firmware 1.0.23 handles
   game types 130/131 and the start-data tail.

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

---
title: Game setup
---

# Game setup: planets, fleets, managers

[← contents](index.md)

Before a standard game the players pick a **planet**, an **auxiliary fleet** and their **managers**. The app
packs those choices into the "new game" command (see [in-game communication](game.md#start-data-command-01-01-01-01))
and the ARC does the rest. Everything below comes **from the app code** (modules `4330`, `5330`, `7067`, `6214`,
`881`, `4244`, `7562`, `9073`) and from text found in firmware 1.0.23. None of it has been tested on a device yet.

## Planets

### Where the list comes from

The selection screen shows **34 planets** from a table bundled in the app (module `2160`), in 15 star systems
near Sol (Alpha Centauri, Tau Ceti, Groombridge, …). The app's info screen says this is the starting list
("planets in the Republic system") and that planets discovered in the **Exogen** metagame would be added once
the metagame link went live. It never did, so these 34 are all there is. The table also has metagame fields
(`colony`, `activeMission`, `pioneered`, `lunarBaseCount`, …) that no code reads.

Scenarios use their own planets (module `9546`) and send coordinates `0x7FFF`/`0xFF` and the scenario
planet ID.

### What is sent to the ARC

Only the **coordinates**: quadrant X/Y, system X/Y and the planet number. No parameters. The coordinates are
global galaxy coordinates (a quadrant is `floor(real / 100) * 10`).

Firmware 1.0.23 contains the debug strings of a **procedural galaxy generator** ("star exoplanets count",
"choosing exoplanet or terrestial", "exoplanet parameters for %s %s special bursts", the planet type names…).
So the ARC most likely **rebuilds the planet from its coordinates** and applies its effects itself.
The app's table is a precomputed copy of the same generator output, used for the artwork and descriptions.
This also means any coordinates should work, not just the 34 in the app. That is unverified.

### Planet parameters

| parameter | values |
|---|---|
| type | Desert, Dunes, Rocky, Metal, Volcanic, Craters and their combinations (e.g. DunesVolcanic), EarthlikeWorld |
| liquids | lack, minimal, periodic rivers, rivers, lakes, seas, oceans, dense |
| atmosphere | lack, minimal, scattered clouds, heavy clouds, storms, dense |
| relief | plains, mountains, deep canyons, spiky hills, porous ground, monoliths |
| temperature | ice cold, frost, cold, medium, warm, hot, boiling hot |
| stability | stable, unstable ground, earthquakes |
| special | extreme weather, magnetic interference, radioactive, plasma burst, ice caps, seasons |
| gravity | low (< 0.65 g), normal, high (> 1.35 g), with g = 9.83 |
| difficulty | very easy, easy, normal, hard, very hard, extreme, nightmare |

### Effects

The planet details screen lists effects built from this rule table (module `7067`). Each parameter adds
modifiers. Numeric modifiers are summed and capped (module `6214`); flags are switched on.

| condition | effects |
|---|---|
| Desert | ID −1 |
| Dunes | ID −1, TTB |
| Rocky | ID +1 |
| Metal | ID +1, TTB |
| Volcanic | ID +2, TTB, CAT |
| no atmosphere | AS −1 |
| no liquids | AW −1 |
| rivers, seas or oceans | AW +2 |
| cloudy (scattered, heavy, storms) | SPP −1, LSS +1, HYDRO −1 |
| any relief except plains and monoliths | TTB |
| ice cold, boiling hot | H −1, S −1, T −1 |
| frost, hot | S −1 |
| medium temperature | H +1 |
| unstable ground, earthquakes | OCC, CAT |
| extreme weather | OCC, CAT, T −1, LPSP |
| magnetic interference | OCC |
| radioactive | OCC, S −1, NUC |
| plasma burst | OCC, CAT |
| low gravity | OCC |
| high gravity | OCC, CAT |

| code | meaning | range |
|---|---|---|
| ID | Industrial Dome stock output | −1 … +2 |
| AS | Atmospheric Synthesizer gas output | −1 … 0 |
| AW | Automatic Well liquids output | −1 … +1 |
| SPP | Solar Power Plant power output | −1 … 0 |
| LSS | Life Support System output | 0 … +1 |
| HYDRO | Hydroponics Dome stock output | −1 … 0 |
| H, S, T | happiness, security, technical state | H −4 … +1, S and T −4 … 0 |
| TTB | longer construction | flag |
| CAT | catastrophes can spread to neighbouring modules | flag |
| OCC | dangerous planetary events can happen | flag |
| LPSP | Landing Pad and Spaceport give no stock | flag |
| NUC | Nuclear Power Plant gives a lot of stock | flag |

So the planet choice is not cosmetic: it changes building output, the colony indicators, construction time
and the event pool. The app only *describes* the effects; the numbers that matter are computed by the ARC.

The app also uses the planet for ambient sounds (no atmosphere → "deep space" ambience, extreme weather,
no liquids) and for a "planet modifier" on the score screen: nightmare 0, extreme 25, very hard 50, hard 75,
normal 100, easy 125, very easy 150. The modifier is shown as a separate line, but the final total comes
from the score the ARC reports (in co-op/solo the app adds and subtracts it, so it cancels out).

## Auxiliary fleets

A fleet is a one-off bonus for the whole game: extra stock, resources, citizens or indicator boosts.
The app knows 27 fleets with names and effects and reads availability for fleets 1–25 from the ARC.

| ID | fleet | effect (app text, shortened) |
|---|---|---|
| 1 | Light bulk carrier fleet | extra stock at start |
| 2 | Research Vessel | happiness up, scientists join |
| 3 | Terran bulk carrier fleet | extra stock, but one Terran dependence |
| 4 | Orbital solar array | small power boost |
| 5 | Asteroid field mining company | managers start with an expedition |
| 6 | Off-world passenger shuttles | colonists work off-planet: more tax stock |
| 7 | Luxury liner | managers start with 4 CR, 2 TG, 2 decrees |
| 8 | Orbital gas tanker | small gas reserve |
| 9 | Orbital liquids tanker | small liquids reserve |
| 10 | Subroutine orbital landers | ARC uses less stock |
| 11 | Military frigate | security up, marines and security force at start |
| 12 | Small orbital marketplace | a little stock every month |
| 13 | Beacon space station | managers start with 2 CR, 1 TG, 4 decrees |
| 14 | Orbital subroutine station | technical state greatly up |
| 15 | Orbital space dock | module proposal bank with an endorsement |
| 16 | Unmanned energy refinery | power reserve |
| 17 | Luxury orbital hotel | migration and happiness up, security down |
| 18 | Long range antenna array | managers start with an artifact |
| 19 | Satellite network | happiness, security and technical up |
| 20 | Small orbital cargo facility | stock production and starting stock |
| 21 | Hussar | 4 extra TG, governor flips an assistant |
| 22 | SIM-STIM sleepers barge | 100 of each citizen group |
| 23 | Rapid Squadron | security and technical up for stock up front |
| 24 | UAT station | extra stock |
| 25 | Quantum datacenter vessel | scientists pay more tax |
| 26 | Pilgrims Barge Fleet | migration and happiness up, security and technical down (no ARC slot) |
| 27 | Terran Charter Shuttles | migration slightly up (no ARC slot) |

Each fleet has a rarity group 1–3 (the app's "three-star" ranking). Group 3: 3, 7, 13, 17, 21, 22.
Group 1: 1, 4, 5, 11, 15, 18, 20, 23. The rest are group 2.

### How fleets were supposed to be unlocked

According to the app's info screen, fleets were to be **earned in Exogen** (the publisher's online metagame) or
through achievements in Colonies, **stored on the ARC** (not in the app) and tradeable between players with
**fleet NFC cards**. All of it was to switch on "after the majority of game sets have been delivered".

What the 1.3.13 code actually does:

- It asks the ARC which fleets are available (`01 01 04 01`, value `2` = available).
- **In a release build every fleet is locked anyway.** The `Fleet` constructor ignores the ARC's answer and
  sets `isAvail = false` unless the app's internal `_debug` flag is on. Players can only pick "no fleet",
  and the game starts with fleet `0`.
- The handler for the fleet NFC card (event `02 04 …`) only writes the card data to the console.
- There is no command in the app that unlocks a fleet on the ARC.
- The ARC firmware, on the other hand, can read and write a 16-byte record on a card (see
  [the card record](cards.md#the-card-record)), so the card side of fleet trading existed on the device.

### What a real ARC reports (confirmed)

Read on an ARC with firmware 1.0.23 (November 2026), outside game mode, with no game in progress:

```
> 55 05 08 01 01 04 01 86
< 55 05 9c 01 01  02 02 02 02 02 02 02 02 02 02  01 01 … 01  e1
```

- The response is **150 bytes** of data, one per fleet slot, not the 25 the app reads (the app drops
  everything after slot 25).
- **Fleets 1–10 have value `2` (available)**, and all other slots have `1` (most likely "locked").
  The query works without entering game mode first.
- This matches the app's debug simulation (`simulateFleetData` marks exactly fleets 1–10 as available),
  so 1–10 is most likely the factory default.

So the ARC already offers ten fleets, and only the app's `_debug` gate hides them from players.
A client without that gate (our own, or the rebuilt app with the check removed) should be able to start a
game with fleets 1–10. That last step is not yet tested on a device. How fleets 11+ would be unlocked
(NFC card or a command we have not found) is still unknown and probably lives only in the firmware.

## Managers

There are 9 managers (IDs 1–9) plus the solo player (`255`). Each one has a role, a personal **directive**
card and access to some special buildings. The app enforces both; the ARC is only told who plays.

| ID | role | name | directive (card ID) |
|---|---|---|---|
| 1 | Preacher | Art Chen | Pilgrimage (209) |
| 2 | Racketeer | Ava Xu | Hidden stash (203) |
| 3 | Engineer | Paul Bloch | Humanoid subroutines (206) |
| 4 | Inventor | Boris Artyomov | The Discovery Program (207) |
| 5 | Warden | Lucas Johannes | State of Emergency (208) |
| 6 | Explorer | Giselle Carter | Private expedition (204) |
| 7 | Broker | Mac McCain | Offshore account (205) |
| 8 | Major | Athena Gore | War! (201) |
| 9 | Visionary | Vlad Pokorny | Promised Land (202) |

A directive can be played only by its owner (module `1089`). Special buildings (module `4244`):

| building | managers |
|---|---|
| 21 Hangar | Engineer, Explorer, Major |
| 22 Test Chamber | Engineer, Inventor |
| 23 Community Tower | Preacher, Racketeer, Visionary |
| 24 Consulate, 29 Spaceport | Broker |
| 25 Laboratory | Inventor, Explorer |
| 26 Bunker | Major |
| 27 Terran Embassy | Visionary |
| 28 Obelisk | Preacher |
| 30 Prison Dome | Racketeer, Warden |
| 31 Cryogenic Cubes | Warden |

The solo player may build all of them. The app's check is loose: it accepts a special building if **any**
manager in the game may build it, not necessarily the player who plugged it in (module `4244`,
`isModuleCorrect`). It also rejects a building already on the board, the same building twice in a round, and
a second building from the same player in one round.

Beyond that, the app treats managers the same way: the end-of-game screen has a victory title and quote for
each role, and per-player points (presidency, decrees, modules, directives, ambassador, order of command) come
from the ARC. What a directive does is decided by the ARC; the app only has its name. Manager-specific
rules that live on the physical cards and boards are outside this documentation.

## Multiple colonies and campaigns

The app has **no code** for linking games, sharing a planet between groups or any online play. There are
only traces of plans:

- planet coordinates are global galaxy coordinates shared with the Exogen metagame;
- the planet table has unused fields for colonies and missions on each planet;
- the ARC has events about "other colonies on the planet" (sending colonists or supplies, trade, scientific
  exchange, rivalry) and about "no other colonies visible". The ARC picks events on its own, so we do not know
  what triggers them without a network link, possibly just chance or the planet itself;
- backer registration was meant for an "incoming campaign mode";
- fleet cards were meant to move fleets between players.

Each game runs on one ARC; the app connects to one ARC at a time.

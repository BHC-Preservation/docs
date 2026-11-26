---
title: Hardware
---

# ARC hardware and the building network

[← contents](index.md)

The ARC's board, as the firmware drives it, and the bus that connects the buildings.

## The board

| part | details |
|---|---|
| MCU | Nordic **nRF52840**, 1 MB flash, 256 KB RAM, Cortex-M4 at 64 MHz. The low-frequency clock runs from the internal RC oscillator (the 32 kHz crystal is not used) |
| operating system | the **NuttX** RTOS, with Nordic's SoftDevice S140 7.0.1 as the BLE stack |
| BLE | Nordic UART Service, see [protocol](protocol.md#link-details) |
| NFC reader | NXP **MFRC522** on SPI, see [NFC cards](cards.md#reader-and-tags) |
| EEPROM | a **24xx32** (4 KB) on I²C at address `0x50`, see [below](#eeprom) |
| LEDs | 6 LEDs on GPIOs, active low |
| battery | measured with the nRF52's ADC on pin `P0.02`, gain 1/4 (see [protocol](protocol.md#device-info-category-03)) |
| building bus | a UART at 9600 baud, see [the building network](#the-building-network) |
| buttons, buzzer | none |

### Pins

| function | pins |
|---|---|
| console UART | RX `P0.24`, TX `P1.00` |
| building bus UART | RX `P0.31`, TX `P0.29` |
| SPI (NFC reader) | SCK `P0.08`, MOSI `P0.06`, MISO `P0.04`; MFRC522 CS `P1.09`, reset `P0.26`, IRQ `P0.12` (unused) |
| I²C (EEPROM) | SDA `P0.22`, SCL `P0.20` |
| battery ADC | `P0.02` (AIN0) |
| LEDs | `P1.10`, `P0.00`, `P0.01`, `P0.17`, `P0.15`, `P0.13` |

### The ARC's own LEDs

All six LEDs light up when the firmware has started. A distinct pattern (`0b001001`) is shown when the LED
thread exits.

## Software structure

A supervisor task starts two NuttX tasks:

- the **engine**: the colony simulation, the planet generator and the EEPROM storage. It answers
  everything in [category `01`](game.md);
- the **UI**: BLE, NFC, the building bus, the LEDs and the battery measurement. It answers the other
  categories itself and passes category `01` to the engine.

The two talk through named FIFOs. The UI has one thread per peripheral (BLE, NFC, building bus, LEDs). There is
no watchdog.

The ARC has no power-saving mode: it advertises and polls its peripherals for as long as it has power. That
matters little for battery life, because the ARC is not the biggest consumer in the game: the LEDs are.

## The building network

The buildings contain their own controllers and LEDs. They talk to the ARC over a
**9600 baud UART bus**. The ARC reads back an echo of everything it sends.

### Frame format

```
FF  AA  <len>  <sum>  <cmd>  <data…>  <route…>
```

| field | meaning |
|---|---|
| `FF AA` | sync and start of frame |
| `len` | number of bytes after `FF` |
| `sum` | checksum: the sum of all bytes from `AA` to the end, with this byte counted as 0, `& 0x7F` |
| `cmd` | bits 0–2 command, bits 3–5 error, bit 6 "discovery" |

| command | meaning |
|---|---|
| 0 | slave |
| 1 | no operation |
| 2 | set the building's LEDs (fixed values) |
| 3 | custom LED effect |
| 4 | **write type** |

Data of the commands:

| command | data |
|---|---|
| 2, fixed LEDs (6 B) | `blue1 blue2 green1 green2 red1 red2`, one brightness byte per channel |
| 3, custom LED effect (11 B) | `colour top bottom up_speed down_speed wait_top wait_bottom wait_between series cycles wait_next`. The ARC never sends it |
| 4, write type (1 B) | the type. The ARC never sends it |
| discovery (from a building) | `ttl neighbours type route…`: `ttl` and `neighbours` are only read and logged |

The ARC has a set of LED states it can show on a building: default, construction progress in 10 % steps (0 to
100 %), catastrophe, riot stage 1 and 2. Every state sends the same fixed-LED frame (all six channels `1`).

### How buildings are found

The ARC never queries the buildings. A building announces itself with a **discovery frame** (`cmd` bit 6 set) that carries
`ttl`, `neighbours`, a type byte and its **route**. The ARC ignores the type byte and gives buildings
sequential IDs 1, 2, 3… in the order they are discovered.

The route is the address of the building: a list of 4-bit hop numbers (1–15) from the ARC (`0`) outwards,
packed two per byte, with up to 14 hops (the address holds 15 entries including the ARC's `0`) and up to 15 buildings (16 entries
including the ARC itself). The
packing differs by direction. In frames the ARC sends, the hop nearest the ARC is in the last byte's low nibble:

| route | bytes sent by the ARC |
|---|---|
| ARC → 2 | `02` |
| ARC → 2 → 6 | `62` |
| ARC → 2 → 6 → 5 | `05 62` |
| ARC → 2 → 6 → 1 → 1 | `11 62` |

In a discovery frame the building sends the route the other way round: `20` means ARC → 2, and `24 50` means
the hops 2, 4, 5 seen from the building, i.e. ARC → 5 → 4 → 2 (sent back by the ARC as `02 45`).

When a building appears at a route the ARC has not seen, it reports it to the app as a board event and answers
the building with an LED command. A building that is plugged in again at the same place is reported again.
Removing a building is not detected: the ARC remembers what it has seen until it restarts.

The ARC reads the bus about once a second, so a building can take a moment to show up after it has been
plugged in.

## EEPROM

The ARC stores everything that must survive a restart in its 4 KB EEPROM, of which the firmware uses the first
2 KB. Each section ends with its own CRC-32 (the standard zlib CRC-32 over the section without its last 4
bytes), so a damaged section is detected and not used.

| offset | size | section | contents |
|---|---|---|---|
| 0 | 32 | settings | magic number `EF BE AD DE` (`0xDEADBEEF`, LE) that marks a formatted EEPROM, 24 reserved bytes, CRC |
| 32 | 528 | key | 512 bytes for a public key, which the firmware never reads, 12 reserved, CRC |
| 560 | 160 | fleets | one byte per fleet slot (150 × `01` locked / `02` available, see [fleets](setup.md#how-fleets-are-granted-firmware-analysis-unlock-confirmed)), 6 padding bytes, CRC |
| 720 | 240 | start data | the 222-byte [start data](game.md#start-data-command-01-01-01-01) of the current game, 14 padding bytes, CRC |
| 960 | 1024 | round save | the colony state and the active modifiers after the last round, for [continuing a game](game.md#continuing-a-saved-game), CRC |

The CRC is the last 4 bytes of each section (LE).

When the magic number or the CRC of the settings section is wrong, for example on a brand-new board, the
firmware **formats** the EEPROM: the first 2 KB are zeroed and the factory fleet table (`02` in slots 0–9) is
written. A corrupted settings section therefore resets the fleets too.

The fleet section can be changed over BLE with the lock and unlock requests (see [fleets](setup.md#how-fleets-are-granted-firmware-analysis-unlock-confirmed)).

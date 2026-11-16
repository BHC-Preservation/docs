---
title: The app code
---

# The app code: extracting and rebuilding

[← contents](index.md)

This site describes the app but contains none of its code. If you own the app, you can get the exact
same code we analysed and check that it matches, byte for byte.

## Why this works

*Colonies* is a Cordova app. Its native binary is FairPlay-encrypted, but all game logic, texts, artwork and
sounds sit in the bundle's `www/` folder as plain files, unencrypted. The native part is only a set of public
Cordova plugins (Bluetooth, Nordic DFU, file access and so on).

That gives two independent pieces:

| piece | where it comes from | can it be shared? |
|---|---|---|
| `www/` (game logic and assets) | your own copy of app 1.3.13 | no, it is the publisher's copyrighted work |
| native shell (Cordova + plugins) | public open-source projects | yes |

## Extracting `www/`: [`extract`](https://github.com/BHC-Preservation/extract)

You need app 1.3.13, the last version, from an Apple ID that owns it:

- an **Apple Silicon Mac** with the app installed from the App Store, or
- an **`.ipa`** downloaded with your own Apple ID (for example with `ipatool`).

```bash
git clone https://github.com/BHC-Preservation/extract.git
cd extract && mise install && mise trust
./extract.sh                          # source: /Applications/Colonies.app
./extract.sh ~/Downloads/Colonies.ipa # or an .ipa / .zip of the app
```

The script writes two folders:

- `out/app-snapshot/`: `www/`, `Info.plist` and `config.xml`, checked against `SHA256SUMS` (2087 files),
- `out/deob/`: `index.min.js` decoded with [webcrack](https://github.com/j4k0xb/webcrack) at a pinned version,
  109 webpack modules, also checked (111 files).

When both checks pass, the module numbers used on this site (e.g. `3488`, `7616`) and the line references in
our notes point at the same code in your copy. A different app version or webcrack version gives different numbers.

**Confirmed (November 2026):** extracting from the installed Mac app and from a zipped copy of it gives
output identical to our reference copy.

Keep the output to yourself. The repo contains only the script and checksums.

## Rebuilding the app

The App Store build can't be patched or re-signed: any change to `www/` breaks its signature. To keep the app
running when the store version stops installing, and to get a debuggable build, we rebuild the native shell from
public sources and put the **original, unmodified `www/`** inside it:

- cordova-ios 8 (required by current Xcode), the original 23 plugins at their original versions, apart from a few
  documented exceptions needed by current iOS and Xcode,
- separate bundle ID, so it installs next to the original app and keeps its own data,
- two small scripts loaded before the game code: compatibility shims for current WebKit and a guard for the dead
  publisher API (time out, block, answer locally, or forward to a [replacement server](online.md#replacement-server)),
- optional on-screen debug log and Safari Web Inspector.

The rebuild takes `www/` from wherever you extracted it, so the two steps are:

```bash
extract/extract.sh                 # → extract/out/app-snapshot
app-rebuild/setup.sh               # finds ../extract/out/app-snapshot on its own
# or: app-rebuild/setup.sh --snapshot=/path/to/app-snapshot
```

**Status:** runs in the iOS Simulator up to the main menu. Bluetooth (ARC) and firmware updates through the
rebuilt app have not been tested on a device yet. The rebuild project itself is not public yet.

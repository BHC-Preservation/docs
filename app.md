---
title: Build the app yourself
---

# Build the app yourself

[← contents](index.md)

If you own *Colonies* 1.3.13, you can turn your copy into an app that **you build, sign and debug yourself**.
It is the same game code, byte for byte, in a fresh native shell made for current iOS and Xcode. It keeps
working when the App Store version stops installing, and it doesn't depend on the publisher's servers.

None of our repositories contains the publisher's code or artwork. You bring the app, and our scripts do the rest.

## The pipeline

```
your copy of the app        extract                       app-rebuild                  Xcode
(Mac App Store or .ipa)  →  www/ + SHA256 check        →  Cordova 8 shell            →  Simulator, iPhone,
                            (+ deobfuscated modules)      + original plugins            iPad, Mac
                                                          + your www/, unchanged
```

| step | repo | what it does | how it is checked |
|---|---|---|---|
| 1. extract | [`extract`](https://github.com/BHC-Preservation/extract) | copies `www/` out of your app, decodes `index.min.js` with webcrack | 2087 + 111 files compared against SHA-256 sums |
| 2. rebuild | [`app-rebuild`](https://github.com/BHC-Preservation/app-rebuild) | creates a cordova-ios 8 project with the original plugin set and puts your `www/` inside | JS plugin modules compared with the original app's `cordova_plugins.js` |
| 3. run | Xcode | Simulator, or your own device with your Apple ID | |

## Why this works

*Colonies* is a Cordova app. Its native binary is FairPlay-encrypted and can't be re-signed. But all of the game
logic, texts, artwork and sounds sit in the bundle's `www/` folder as plain files, and the native side is just
public Cordova plugins (Bluetooth LE, Nordic DFU, files and so on). So we keep the original `www/` and rebuild
only the native shell, from public sources.

| piece | comes from | in our repos? |
|---|---|---|
| `www/` (game logic and assets) | your own copy of app 1.3.13 | no, it is the publisher's work |
| native shell (Cordova + plugins) | public open-source projects | yes, with build fixes for current Xcode |

## 1. Extract

You need app 1.3.13, the last version, from an Apple ID that owns it:

- an **Apple Silicon Mac** with the app installed from the App Store, or
- an **`.ipa`** downloaded with your own Apple ID (for example with `ipatool`).

```bash
git clone https://github.com/BHC-Preservation/extract.git
cd extract && mise install && mise trust
./extract.sh                          # source: /Applications/Colonies.app
./extract.sh ~/Downloads/Colonies.ipa # or an .ipa / .zip of the app
```

Output:

- `out/app-snapshot/`: `www/`, `Info.plist` and `config.xml`, checked against `SHA256SUMS` (2087 files),
- `out/deob/`: `index.min.js` decoded with [webcrack](https://github.com/j4k0xb/webcrack) at a pinned version,
  109 webpack modules (111 files), also checked.

When both checks pass, the module numbers on this site (e.g. `3488`, `7616`) point at the same code in your copy.

**Confirmed (November 2026):** extracting from the installed Mac app and from a zipped copy of it gives output
identical to our reference copy.

## 2. Rebuild

Needs macOS, Xcode with an iOS Simulator runtime, CocoaPods and mise. Clone it next to `extract`:

```bash
git clone https://github.com/BHC-Preservation/app-rebuild.git
cd app-rebuild && mise install
./setup.sh                            # finds ../extract/out/app-snapshot on its own
cd colonies
LANG=en_US.UTF-8 mise exec -- npx cordova build ios --emulator --buildConfig=build.json
```

`setup.sh` builds the project from scratch on every run: cordova-ios 8.2.0, the original 23 plugins at their
original versions (with a few documented exceptions), your `www/`, and two small scripts loaded before the game
code. The first run takes a few minutes (npm and CocoaPods).

Options:

| option | effect |
|---|---|
| `--snapshot=DIR` | take `www/` from another folder |
| `--api=timeout` (default), `block`, `fake`, or a URL | what happens to requests for the dead publisher API: fail after 1 s, fail at once, answer locally, or forward to a [replacement server](online.md#replacement-server). Without this, the app could hang on "checking firmware" |
| `--unlock-fleets` | opt-in, one-line patch: the fleet picker uses the ARC's fleet table instead of hiding every fleet (see [setup](setup.md)) |
| `--fix-task-queue` | opt-in, one-line patch: the connect screen no longer stays at "synchronizing with ARC" when the API answers slowly |
| `--from-deob`, `--patch=FILE` | build the game code from the deobfuscated modules and apply fixes as diffs (see below) |

## Fixing the game code

The App Store build can't be fixed, but your own rebuild can. `extract` gives you the game code in several forms:

| folder | what it is | use it for |
|---|---|---|
| `out/deob/` | webcrack output, 109 modules, verified by checksums | the base that patches apply to |
| `out/annotated/` | the same modules with about 3100 names found automatically (`u_startScan`, `buildFrame`, `loadingEl`, `_asyncToGenerator`), **same line numbers** | reading and finding the place to fix |
| `out/map.md` | map of all modules: dependencies, exports, templates, storage keys, BLE frames, messages, bundled libraries | finding the right module |
| `out/readable/` | the annotated modules run through [wakaru](https://github.com/pionxzh/wakaru): `async`/`await`, classes, `let`/`const`; different line numbers | reading the logic |

`extract/rebundle.mjs` puts the modules back into a runnable bundle. With `setup.sh --from-deob` the rebuilt app
runs that bundle instead of the original file, with your patches applied:

```bash
cp extract/out/deob/3488.js .           # edit it, using annotated/3488.js to read
diff -U1 --label a/3488.js --label b/3488.js extract/out/deob/3488.js 3488.js > my-fix.patch
app-rebuild/setup.sh --from-deob --patch=my-fix.patch
```

The two fixes we ship (`--unlock-fleets`, `--fix-task-queue`) are one-line patches of this kind.
**Confirmed (November 2026):** an app built this way, with names applied or without, runs in the Simulator the same
way as the original up to the main menu.

Under EU law (Article 5 of the Software Directive) the lawful user of a program may correct its errors. Share
**patches**, with as little context as possible, never patched files or built apps.

## 3. Run

- **Simulator:** open `colonies/platforms/ios/App.xcworkspace` in Xcode and run.
- **iPhone, iPad or Apple Silicon Mac:** in the same workspace pick your Team under *Signing & Capabilities* and
  run on your device. A free Apple ID works, but the build expires after 7 days. Bluetooth (the ARC) needs a real device.

The rebuilt app is called **Colonies BHC** and has its own bundle ID, so it installs next to the original and keeps
its own settings and saved games.

For debugging there's an on-screen log (triple-tap the top-left corner: console, errors, every request, hung native
calls) and Safari Web Inspector.

## Android and Amazon Fire

So far the rebuild targets iOS only, but an Android build should be possible, and with it Amazon Fire tablets:
Fire OS is Android without Google services (Fire OS 7 is Android 9, Fire OS 8 is Android 11), and the game doesn't
use Google services.

- The game code is the same on every platform and already handles Android: Bluetooth and location permissions
  (including the Android 12+ ones) and Android asset paths for audio.
- The original app was configured for Android too, and every plugin it uses has an Android implementation,
  including Bluetooth LE and Nordic DFU.
- The `www/` you extract from the iOS app is enough. Cordova generates its own platform files.

Roughly: the same `www/` and plugin list as for iOS, `cordova platform add android` instead of `ios`, then
`cordova build android` and install the APK with `adb install` (on Fire: allow apps from unknown sources). This
needs JDK 17 and the Android SDK, but no Mac.

**Not tried yet.** [`app-rebuild/android/`](https://github.com/BHC-Preservation/app-rebuild/tree/master/android)
has notes and an outline script, not a working build. Expected work: newer versions of a few plugins for current
Android (notably the Nordic DFU library), audio paths under cordova-android's `https://localhost` scheme, and
checking Bluetooth permissions on Android 12+. Reports are welcome.

## What differs from the original

- Native shell: cordova-ios 8 instead of 6, needed by current Xcode and iOS.
- A few plugins at newer versions or with build fixes, each listed with its reason in the `app-rebuild` README.
- `bhc-compat.js`: shims for current WebKit (e.g. `screen.orientation.lock()` no longer settles) and the API guard above.
- `bhc-debug.js`: the debug overlay.
- The game code itself (`www/js/index.min.js`) is **not modified** unless you choose `--unlock-fleets`.

## Status

- **Confirmed:** extract matches the reference copy. The rebuild runs in the iOS Simulator (iOS 27.2) through the
  intro and disclaimer to the main menu.
- **Not tested yet:** Bluetooth with a real ARC and firmware updates through the rebuilt app.
- **Not started:** an Android / Fire OS build (outline only, see above).

## How we handle copyright

The goal is a game that keeps working for the people who bought it, not a copy of the publisher's work.

- **We publish tools and knowledge, never the app.** Scripts, checksums, build fixes and this documentation. Code,
  artwork, sounds and firmware stay on the owner's machine.
- **You start from your own copy.** Every step runs on an app you obtained yourself, and the result is for your own use.
  Don't share the extracted files or the apps you build.
- **Reverse engineering serves interoperability:** describing how the app and the ARC talk, so the device can be used
  without the official app. This site describes behaviour and protocols, not code.
- **A future independent client** will be written from this documentation, not from the app's code, with its own
  interface and no assets from the original.

This project is not affiliated with Three Headed Monster. If you represent the publisher and have concerns, please
open an issue in one of the repositories.

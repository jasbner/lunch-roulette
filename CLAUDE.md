# Lunch Roulette

Random DoorDash lunch picker for one office. The office's coordinates are in `office.json`,
which is gitignored so the public repo doesn't show where it is.

- `lunch-roulette.html` — the whole app (one page). Also published as a claude.ai artifact:
  https://claude.ai/artifact/JS8GKnyof3LbNzZVir7d6Z (republish after page changes).
- `refresh.py` — rebuilds the PLACES list from read-only `dd-cli search` calls (DoorDash CLI
  private beta). Never run cart or order commands. DoorDash rate-limits after ~80 searches in
  half an hour (one refresh is 27), so don't run it repeatedly.
- `android/` — WebView wrapper built with plain SDK tools (`build.sh`, no Gradle).

## Shipping the Android app

Distribute through GitHub releases on the public repo jasbner/lunch-roulette, not the LAN
(phones on the home Wi-Fi couldn't reliably reach this computer). The link stays the same:
https://github.com/jasbner/lunch-roulette/releases/latest/download/lunch-roulette.apk

1. Bump `versionCode` and `versionName` in `android/AndroidManifest.xml`.
2. Run `android/release.sh` (builds, then creates release `v<versionName>`).

Signing key: `~/.config/lunch-roulette/release.jks`, referenced by `android/keystore.properties`.
Every update must be signed with it; losing it means uninstalling the app to update.

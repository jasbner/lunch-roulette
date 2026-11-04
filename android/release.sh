#!/usr/bin/env bash
# Builds the APK and publishes it as a GitHub release on jasbner/lunch-roulette.
# The download link never changes:
#   https://github.com/jasbner/lunch-roulette/releases/latest/download/lunch-roulette.apk
# Bump versionCode and versionName in AndroidManifest.xml first, or the phone refuses the update.
set -euo pipefail
cd "$(dirname "$0")"

VERSION=$(sed -n 's/.*android:versionName="\([^"]*\)".*/\1/p' AndroidManifest.xml)
if gh release view "v$VERSION" --repo jasbner/lunch-roulette >/dev/null 2>&1; then
  echo "Release v$VERSION already exists; bump versionCode and versionName in AndroidManifest.xml" >&2
  exit 1
fi
bash build.sh
gh release create "v$VERSION" dist/lunch-roulette.apk --repo jasbner/lunch-roulette \
  --title "Lunch Roulette $VERSION" \
  --notes "Tap lunch-roulette.apk below to download, then open it to install. Android 10 or later."
echo "Download: https://github.com/jasbner/lunch-roulette/releases/latest/download/lunch-roulette.apk"

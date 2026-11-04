#!/usr/bin/env bash
# Builds dist/lunch-roulette.apk from ../lunch-roulette.html with the plain Android SDK tools (no Gradle).
# Signs with the key named in keystore.properties (~/.config/lunch-roulette/release.jks). Every
# update must use that same key to install over the old app, so back it up.
set -euo pipefail
cd "$(dirname "$0")"

SDK="${ANDROID_HOME:-$HOME/Android/Sdk}"
BT="$SDK/build-tools/35.0.0"
JAR="$SDK/platforms/android-35/android.jar"
OUT=build
[ -f keystore.properties ] || { echo "Missing keystore.properties" >&2; exit 1; }
KS=$(sed -n 's/^storeFile=//p' keystore.properties)
export PASS=$(sed -n 's/^storePassword=//p' keystore.properties)
[ -f "$KS" ] || { echo "Missing signing key $KS" >&2; exit 1; }
rm -rf "$OUT" && mkdir -p "$OUT"/{res,gen,classes,assets} dist

# The page has no document skeleton (the artifact host adds one), so add it here.
{
  printf '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
  printf '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
  cat ../lunch-roulette.html
} > "$OUT/assets/index.html"

"$BT/aapt2" compile --dir res -o "$OUT/res.zip"
"$BT/aapt2" link -o "$OUT/unsigned.apk" -I "$JAR" --manifest AndroidManifest.xml \
  --java "$OUT/gen" -A "$OUT/assets" "$OUT/res.zip"
javac -source 11 -target 11 -Xlint:-options -cp "$JAR" -d "$OUT/classes" \
  $(find src "$OUT/gen" -name '*.java')
"$BT/d8" --lib "$JAR" --min-api 29 --output "$OUT" $(find "$OUT/classes" -name '*.class')
(cd "$OUT" && zip -q unsigned.apk classes.dex)
"$BT/zipalign" -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
"$BT/apksigner" sign --v4-signing-enabled false --ks "$KS" --ks-pass env:PASS \
  --ks-key-alias lunch-roulette --key-pass env:PASS \
  --out dist/lunch-roulette.apk "$OUT/aligned.apk"
echo "Built: $(pwd)/dist/lunch-roulette.apk"

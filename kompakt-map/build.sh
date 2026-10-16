#!/usr/bin/env bash
# Build the III Points Kompakt APK without Gradle (Debian android-sdk + platform 23).
#   sudo apt-get install android-sdk android-sdk-platform-23 dalvik-exchange
set -euo pipefail
cd "$(dirname "$0")"
SDK=${ANDROID_SDK:-/usr/lib/android-sdk}
BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)
JAR="$SDK/platforms/android-23/android.jar"
OUT=build
rm -rf "$OUT" && mkdir -p "$OUT/classes" "$OUT/gen" "$OUT/res"

python3 tools/build_map.py >/dev/null                     # refresh map.json / icons.json / mockup svg

"$BT/aapt2" compile --dir app/res -o "$OUT/res.zip"
"$BT/aapt2" link -I "$JAR" --manifest app/AndroidManifest.xml -A app/assets \
    --java "$OUT/gen" -o "$OUT/unsigned.apk" "$OUT/res.zip" --min-sdk-version 21 --target-sdk-version 23

javac -nowarn -source 8 -target 8 -bootclasspath "$JAR" -d "$OUT/classes" \
    $(find app/src "$OUT/gen" -name '*.java') 2>&1 | grep -v "bootstrap class path\|^1 warning\|^warning: \[options\]" || true
dalvik-exchange --dex --min-sdk-version=21 --output="$OUT/classes.dex" "$OUT/classes"
(cd "$OUT" && zip -q unsigned.apk classes.dex)

"$BT/zipalign" -f 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
KS=${KEYSTORE:-tools/debug.keystore}
if [ ! -f "$KS" ]; then
  keytool -genkeypair -keystore "$KS" -storepass android -keypass android -alias kompakt \
    -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=III Points Kompakt" >/dev/null 2>&1
fi
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android --ks-key-alias kompakt \
    --out iiipoints-kompakt.apk "$OUT/aligned.apk"
"$BT/apksigner" verify iiipoints-kompakt.apk
ls -la iiipoints-kompakt.apk

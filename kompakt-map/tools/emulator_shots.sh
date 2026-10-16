#!/usr/bin/env bash
# Runs inside the emulator job: install the APK at Kompakt resolution and capture each screen.
set -x
OUT=kompakt-map/test-shots
rm -rf $OUT && mkdir -p $OUT
adb shell wm size 480x800
adb shell wm density 240
adb install -r kompakt-map/iiipoints-kompakt.apk
NOW="2026-10-16 21:42"
FAVS="Parcels,Floating Points,Lil' Kim,Honey Dijon,Jacques Greene"
shot() {
  adb shell am force-stop com.iiipoints.kompakt
  adb shell am start -W -n com.iiipoints.kompakt/.MainActivity --es now "\"$NOW\"" --es favs "\"$FAVS\"" --es screen "$2"
  sleep 4
  adb exec-out screencap -p > $OUT/$1.png
}
adb logcat -c
shot 1-map map
shot 2-map-stage mapstage:mind-melt
shot 3-lineup lineup
shot 4-lineup-az az
shot 5-stage stage:mind-melt
shot 6-favorites favs
shot 7-filter filter
shot 8-info info
# interaction: zoom out from the map (tap the minus button)
adb shell am force-stop com.iiipoints.kompakt
adb shell am start -W -n com.iiipoints.kompakt/.MainActivity --es now "\"$NOW\"" --es screen map
sleep 3
adb shell input tap 450 186
sleep 2
adb exec-out screencap -p > $OUT/9-map-zoomed-out.png
adb logcat -d -s AndroidRuntime:E > $OUT/logcat.txt
grep -q "FATAL EXCEPTION" $OUT/logcat.txt && echo "CRASH" > $OUT/CRASHED || true
exit 0

#!/usr/bin/env bash
# Runs inside the emulator job: install the APK, emulate the Kompakt screen, capture each screen.
set -x
OUT=kompakt-map/test-shots
mkdir -p $OUT
adb shell wm size 480x800
adb shell wm density 240
adb install -r kompakt-map/iiipoints-kompakt.apk
NOW="2026-10-16 21:42"
shot() {
  adb shell am force-stop com.iiipoints.kompakt
  adb shell am start -W -n com.iiipoints.kompakt/.MainActivity --es now "\"$NOW\"" --es screen "$2"
  sleep 4
  adb exec-out screencap -p > $OUT/$1.png
}
adb logcat -c
shot 1-home none
shot 2-map map
shot 3-map-mindmelt map:mind-melt
shot 4-stage-mindmelt stage:mind-melt
shot 5-now now
shot 6-stages stages
shot 7-legend legend
shot 8-info info
# interaction: zoom out to fit from the map screen
adb shell am force-stop com.iiipoints.kompakt
adb shell am start -W -n com.iiipoints.kompakt/.MainActivity --es now "\"$NOW\"" --es screen map
sleep 3
adb shell input tap 160 770
sleep 2
adb exec-out screencap -p > $OUT/9-map-fit.png
adb logcat -d -s AndroidRuntime:E ActivityManager:W > $OUT/logcat.txt
grep -q "FATAL EXCEPTION" $OUT/logcat.txt && echo "CRASH" > $OUT/CRASHED || true
exit 0

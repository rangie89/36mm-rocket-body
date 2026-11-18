#!/usr/bin/env bash
# Rebuild the 36 mm rocket body from build_body_36mm.py and show the verification.
#
#   ./build.sh
#
# Edit the P dict at the top of build_body_36mm.py first, then run this.
# Override the FreeCAD build with:  FREECAD_APP=/path/to/FreeCAD.AppImage ./build.sh
set -uo pipefail
cd "$(dirname "$0")"

APP="${FREECAD_APP:-$HOME/Downloads/FreeCAD_1.1.4-Linux-x86_64-py311.AppImage}"
if [ ! -x "$APP" ]; then
  echo "FreeCAD AppImage not found or not executable: $APP" >&2
  echo "Set it with:  FREECAD_APP=/path/to/FreeCAD.AppImage ./build.sh" >&2
  exit 2
fi

# FreeCAD IMPORTS the script, so stale bytecode can run old code while the file
# on disk reads correctly.  Same-size, same-second edits are the trap.
rm -rf __pycache__

echo "FreeCAD: $APP"
echo "Building from build_body_36mm.py ..."
echo

# stdin from /dev/null, or FreeCAD drops into its interactive console and lingers.
"$APP" --console build_body_36mm.py < /dev/null > build.log 2>&1
rc=$?

tr '\r' '\n' < build.log \
  | sed '/^== summary ==/,$d' \
  | grep -avE 'saving\.\.\.|Recompute\.\.\.|\([0-9]+ %\)|Console mode|^ *>>>|Importing project|^\[FreeCAD' \
  | grep -av '^[[:space:]]*$'

echo
echo "=============== result ================"
if [ "$rc" -ne 0 ]; then
  echo "BUILD REFUSED (exit $rc) - nothing was exported." >&2
  echo "Fix the parameter/check errors above, then run ./build.sh again." >&2
  exit "$rc"
fi
grep -aE '^params ok|^  body is one|^  volume|^  OD measures|^  bore measures|slides over|^  chute bay|^  body needs|^  cord anchor needs' \
  build.log | sed 's/^[[:space:]]*//'
echo "---------------------------------------"
ls -l --time-style=+%H:%M:%S body36*.stl body36.step
for f in body36.stl body36_gauge.stl body36_cord_anchor.stl; do
  echo "$f  sha256 $(sha256sum "$f" | cut -c1-16)"
done
python3 preview_body.py
python3 interface_section.py
echo
echo "re-render the section image with:  convert -density 150 interface_section.svg interface_section.png"
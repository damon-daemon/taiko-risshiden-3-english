#!/bin/bash
# tomenu.sh [max] : in a battle, press Circle until the daily own-unit menu is up (grey menu box at
# 112..206 x 52..152 of the 320x240 frame); leaves build/shots/tomenu.png. Exit 1 = not found.
D=$(cd "$(dirname "$0")" && pwd); P="$D/../../build/shots/tomenu.png"
for i in $(seq ${1:-30}); do
  "$D/hpress.sh" "$P" w
  "$D/../../.venv/bin/python" - "$P" <<'PY' && exit 0
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGB'); sx = im.width / 320; sy = im.height / 240
n = 0
for x, y in ((116, 56), (200, 56), (116, 146), (200, 146)):
    r, g, b = im.getpixel((int(x * sx), int(y * sy)))
    n += abs(r - g) < 14 and abs(g - b) < 14 and 130 < r < 215
sys.exit(0 if n == 4 else 1)
PY
  "$D/hpress.sh" /dev/null X w
done
exit 1

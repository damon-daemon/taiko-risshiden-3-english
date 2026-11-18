#!/bin/bash
# toaide.sh [out.png] : cold boot -> slot 5 -> audience -> Request Aide (filter poked: the first man of the
# list becomes the hero's aide) -> the hero's Home -> Give Orders -> the aide's menu (Assign Work / Strategist /
# Return Aide). ~2 min. Nothing is saved.
D=$(cd "$(dirname "$0")" && pwd)
SLOT=5 "$D/loadgame.sh" /dev/null
"$D/hpress.sh" /dev/null X w w w X w w X w w w                     # castle -> audience menu
python3 - <<P
import sys; sys.path.insert(0, '$D')
import gdbmem
g = gdbmem.G(); g.cmd('M800f5820,4:00000000'); g.resume()
P
"$D/hpress.sh" /dev/null w Down w X w w X w w X w w X w w X w w w  # Request Aide, first man, Yes
"$D/hpress.sh" /dev/null Z w w w Z w w w w                         # leave the audience and the castle
"$D/hpress.sh" /dev/null A w w Down w Down w X w w Down w X w w w  # place list -> Samurai Home -> Home
"$D/hpress.sh" /dev/null X w w X w w X w w w                       # greeting -> home menu
"$D/hpress.sh" /dev/null Down w Down w X w w X w w X w w w         # Give Orders -> the aide's menu
if [ -n "$1" ] && [ "$1" != /dev/null ]; then "$D/hshot.sh" "$1"; fi

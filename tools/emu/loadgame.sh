#!/bin/bash
# loadgame.sh [out.png] : cold boot the English build (CUE= for another image) and load a memory-card save:
# title -> Continue -> Memory Card -> slot -> confirm -> town. ~60 s. SLOT=n picks the slot (default 1):
#   1 = Iwamura (Mino) 1560/8/7, "Check Prices" done, 4995 kan
#   2 = Kiyosu 1560/8/1, "Check Prices" running, every building opens
#   3 = Kiyosu 1560/9/17, inside the hero's Home (Nene's greeting first), rank 3, no mission, "Nene is ill"
#       errand done (medicine delivered), 4994 kan  [session 33; was the 8/14 save]
#   4 = Kiyosu 1560/8/26, rank 3, "Buy Guns" running (80 days, in competition)  [session 25]
#   5 = Kiyosu 1560/8/26, no mission running, rank set to 3 (Ashigaru Gen.) over GDB: the castle opens
D=$(cd "$(dirname "$0")" && pwd)
WAIT=25 "$D/restart.sh" >/dev/null 2>&1
"$D/hpress.sh" /dev/null Return w w w w w
"$D/hpress.sh" /dev/null Return w w w
"$D/hpress.sh" /dev/null Down w X w w w
"$D/hpress.sh" /dev/null X w w w
for i in $(seq 2 ${SLOT:-1}); do "$D/hpress.sh" /dev/null Down; done
"$D/hpress.sh" /dev/null X w w X w w w w w w
"$D/hpress.sh" /dev/null X w w w w w w w w w
"$D/hpress.sh" /dev/null X w w w
"$D/hpress.sh" /dev/null w w w w
if [ -n "$1" ] && [ "$1" != /dev/null ]; then "$D/hshot.sh" "$1"; fi

#!/bin/bash
# tobattle.sh [out.png] : cold boot -> card slot 5 -> forced council -> forced Battle policy with the hero
# among the four officers -> siege of Ogaki (castle 96) -> battle organisation screen. ~3 min.
# Pokes (notes/engine.md, session 27): council counter 0x8015200c = 1; the officer sort key MAPPOINT
# 0x8010a068 patched in RAM to return 0x7fff for person 0 (the hero); the policy branch 0x8010dd60 nopped
# (any adopted policy marches) and the target chooser 0x80109b60 returns castle 0x60.
D=$(cd "$(dirname "$0")" && pwd); G="$D/../../.venv/bin/python $D/gdbmem.py"
SLOT=5 "$D/loadgame.sh" || exit 1
$G raw M8015200c,1:01 >/dev/null
$G raw M8010a0fc,24:211052001c00bf8f1800b28f1400b18f020000161000b08fff7f02340800e0032000bd27 >/dev/null
# the policy branch 0x8010dd60 (bnez = not Battle) becomes a nop: any decision marches
$G raw M8010dd60,4:00000000 >/dev/null; $G raw M80109b60,8:0800e00360000224 >/dev/null   # target chooser returns castle 0x60
"$D/hpress.sh" /dev/null X w w X w w w
# press on until BATTLE.BIN is loaded (its army getter prologue at 0x80136608)
for i in $(seq 40); do
  "$D/hpress.sh" /dev/null X w w
  [ "$($G read 0x80136608 4)" = e0ffbd27 ] && break
done
"$D/hpress.sh" /dev/null w w w
if [ -n "$1" ] && [ "$1" != /dev/null ]; then "$D/hshot.sh" "$1"; fi

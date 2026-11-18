#!/bin/bash
# tocastle.sh : cold boot -> slot 5 -> audience; Request Aide's list call (0x800f5980) redirected in RAM to
# TARGET (default 0x800fd4b0 = the lord's castle-rename command; 0x800fd148 = rename castle CASTLE directly,
# e.g. CASTLE=101 Kiyosu, 160 Bitchu-Takamatsu). RANK=6 pokes the hero's rank. Ends at "Request Aide" said;
# Circle opens the screen. Nothing saved; the aide flow loops back into the redirect afterwards.
D=$(cd "$(dirname "$0")" && pwd)
SLOT=${SLOT:-5} "$D/loadgame.sh" /dev/null
"$D/hpress.sh" /dev/null X w w w X w w X w w w
python3 - <<P
import struct, sys; sys.path.insert(0, '$D')
import gdbmem
jal = lambda a: 0x0c000000 | a >> 2 & 0x3ffffff
W = {0x800f5820: 0, 0x800f5970: 0x24040000 | ${CASTLE:-0x2479}, 0x800f5980: jal(${TARGET:-0x800fd4b0}), 0x800f5990: 0, 0x800f59a8: 0}
g = gdbmem.G(); print(g.read(0x801563a4,4).hex()); W[0x801563a4] = (g.read(0x801563a4,4)[0] & 0xe0 | ${RANK:-3}) | int.from_bytes(g.read(0x801563a4,4),"little") & ~0xff
for a, w in W.items():
    g.cmd('M%08x,4:%s' % (a, struct.pack('<I', w).hex()))
g.resume()
P
"$D/hpress.sh" /dev/null w Down w X w w

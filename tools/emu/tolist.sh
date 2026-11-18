#!/bin/bash
# tolist.sh TYPE [out.png] [ids...] : show one of the lord-only MAPPOINT lists (types 6, 7, 9, 10) in place of
# Request Aide's officer list: cold boot -> slot 5 (SLOT=n for another) -> audience -> RAM redirect of the
# opener / chooser calls at 0x800f596c.. -> Request Aide. ids = the u16 list entries (persons for 6 / 7, clans
# for 9, provinces for 10; default 0-9), written to 0x8016EC00; the u32 counts of 9 / 10 are at 0x8016EC40.
# MIS="id:command:target[:result[:arg]] ..." gives persons a mission first (person record 0x80157d04 + 24 id:
# +6 target, +7 command, +0xa u16 result, +0xc u16 argument = the skill of command 6). Nothing is saved; cold boot afterwards (the chooser's result is used as an aide index).
D=$(cd "$(dirname "$0")" && pwd)
T=$1; OUT=$2; shift 2
SLOT=${SLOT:-5} "$D/loadgame.sh" /dev/null
"$D/hpress.sh" /dev/null X w w w X w w X w w w                     # castle -> audience menu
python3 - "$T" "$@" <<P
import struct, sys; sys.path.insert(0, '$D')
import gdbmem
t = int(sys.argv[1]); ids = [int(x, 0) for x in sys.argv[2:]] or list(range(10))
obj, opener, chooser = {6: (0x1b54, 0x8014b898, 0x80149b28), 7: (0x1c8c, 0x8014b95c, 0x80149b28),
                        9: (0x1d34, 0x8014d33c, 0x8014d458), 10: (0x1d88, 0x8014d764, 0x80149b28)}[t]
jal = lambda a: 0x0c000000 | a >> 2 & 0x3ffffff
W = {0x800f5820: 0,
     0x800f5970: 0x24840000 | obj, 0x800f5974: 0x24050000 | len(ids), 0x800f5978: 0x3c068017,
     0x800f597c: 0x24c6ec00, 0x800f5980: jal(opener), 0x800f5984: 0x24c70040,
     0x800f598c: 0x24840000 | obj, 0x800f5990: jal(chooser), 0x800f59a0: 0x24840000 | obj}
g = gdbmem.G()
for a, w in W.items():
    g.cmd('M%08x,4:%s' % (a, struct.pack('<I', w).hex()))
b = struct.pack('<%dH' % len(ids), *ids).ljust(0x40, b'\0') + struct.pack('<%dI' % len(ids), *[(7 * i + 3) % 130 for i in range(len(ids))])
g.cmd('M8016ec00,%x:%s' % (len(b), b.hex()))
import os
for m in os.environ.get('MIS', '').split():
    i, c, tg, *r = (int(x, 0) for x in m.split(':'))
    g.cmd('M%08x,2:%02x%02x' % (0x80157d0a + 24 * i, tg, c))
    if r:                                               # result value (+0xa), argument (+0xc: skill of command 6)
        g.cmd('M%08x,4:%s' % (0x80157d0e + 24 * i, struct.pack('<2H', r[0], (r + [0])[1]).hex()))
g.resume()
P
"$D/hpress.sh" /dev/null w Down w X w w X w w w                    # Request Aide -> the list
if [ -n "$OUT" ] && [ "$OUT" != /dev/null ]; then "$D/hshot.sh" "$OUT"; fi

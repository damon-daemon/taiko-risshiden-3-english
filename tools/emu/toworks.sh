#!/bin/bash
# toworks.sh [out.png] [command] : the mission works screen (the hero carries out a domestic mission):
# cold boot -> slot 5 -> the hero's mission poked (person record 0x80157d04: +6 target = Kiyosu 0x65,
# +7 command; default 27 Train; 12 New Fields, 13 Commerce, 14 Mine Work, 15 Repairs, 17 Win Hearts,
# 18 Land Survey, 19 Sabotage) with a budget of 3000 kan (0x80159684) -> out to the map -> back into Kiyosu
# -> "Carry out X?" -> the screen (~90 s). L1 / R1 = Details; Circle on a work = the officer pick list.
# Nothing is saved; cold boot afterwards.
D=$(cd "$(dirname "$0")" && pwd)
SLOT=${SLOT:-5} "$D/loadgame.sh" /dev/null
python3 - "${2:-27}" <<P
import struct, sys; sys.path.insert(0, '$D')
import gdbmem
g = gdbmem.G()
g.cmd('M80157d0a,2:65%02x' % int(sys.argv[1], 0))
g.cmd('M80159684,4:' + struct.pack('<I', 3000).hex())
g.resume()
P
"$D/hpress.sh" /dev/null Z w w X w w w w w w w X w w w X w w w w     # Go outside -> map -> Enter Kiyosu
"$D/hpress.sh" /dev/null X w w w X w w w                             # Carry out X? -> the help line -> screen
if [ -n "$1" ] && [ "$1" != /dev/null ]; then "$D/hshot.sh" "$1"; fi

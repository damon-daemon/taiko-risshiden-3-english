#!/bin/bash
# torename.sh : cold boot -> slot 5 -> Kiyosu farmhouse -> "Ask about area", redirected in RAM (0x80124410) to
# Ganmaku's rename event 0x80125590 (block 5 @128-@142). Ends at "Well now..."; then Circle x 3 = the menu
# Leave to Ganmaku (Hideyoshi) / Decide myself (name entry 0x80125410: family, given, Koichiro's given).
cd "$(dirname "$0")/../.."
SLOT=5 tools/emu/loadgame.sh /dev/null
python3 - <<'P'
import struct,sys; sys.path.insert(0,'tools/emu'); import gdbmem
g=gdbmem.G()
for a,w in {0x80124410:0x0c000000|(0x80125590>>2&0x3ffffff), 0x80124418:0, 0x80124420:0, 0x8012442c:0}.items():
    g.cmd('M%08x,4:%s'%(a,struct.pack('<I',w).hex()))
g.resume()
P
tools/emu/hpress.sh /dev/null A w Down Down Down X w Down Down Down X w w w w X w w X w w X w X w w

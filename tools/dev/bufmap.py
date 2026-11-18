"""List fixed RAM addresses built with lui+ori/addiu at or above a floor (the game's fixed load buffers).
usage: .venv/bin/python tools/dev/bufmap.py 0x80150000
"""
import sys
from collections import defaultdict
from mips import Image, s16
floor = int(sys.argv[1], 0); found = defaultdict(list)
for name in ('jp', 'jp:BATTLE.BIN', 'jp:MAPPOINT.BIN'):
    img = Image(name)
    for va in range(img.base, img.end - 7, 4):
        w = img.word(va)
        if w >> 26 != 0x0F: continue
        hi = (w & 0xFFFF) << 16; n = img.word(va + 4); op, imm = n >> 26, n & 0xFFFF
        if (n >> 21) & 31 != (w >> 16) & 31: continue
        t = hi | imm if op == 0x0D else (hi + s16(imm)) & 0xFFFFFFFF if op == 0x09 else None
        if t and floor <= t < 0x80200000:
            found[t].append('%s:%08x' % (name[3:6] or 'exe', va))
for t in sorted(found):
    print('%08x  %3d  %s' % (t, len(found[t]), ' '.join(found[t][:4])))

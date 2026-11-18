import sys
sys.path.insert(0, '/home/leto2/Projects/taiko_risshiden_3_translation/tools/dev')
from mips import Image, jals
import pkinds
img = Image('jp:BATTLE.BIN')
SHOW = {0x80142edc: 4, 0x80142f1c: 4, 0x80142c34: 5, 0x80142cdc: 6, 0x80142df0: 5}
def jal(w):
    return (w & 0x03FFFFFF) << 2 | 0x80000000 if w >> 26 == 3 else None
def regval(a, reg):
    for b in range(a + 4, a - 40, -4):
        w = img.word(b)
        if w >> 26 == 9 and (w >> 21) & 31 == 0 and (w >> 16) & 31 == reg:
            return w & 0xFFFF
        if b < a and jal(w): break
    return None
res = []
for f, r in SHOW.items():
    for va in jals(img, f):
        res.append((va, regval(va, r), f))
res.sort()
for va, n, f in res:
    print('%08x %s %s' % (va, n, '%x' % f))

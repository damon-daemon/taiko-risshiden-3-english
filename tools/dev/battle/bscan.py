import sys
sys.path.insert(0, '/home/leto2/Projects/taiko_risshiden_3_translation/tools/dev')
from mips import Image, jals, s16
import pkinds
img = Image('jp:BATTLE.BIN')
SHOW = {0x80142edc: 4, 0x80142f1c: 4, 0x80142c34: 5, 0x80142cdc: 6, 0x80142df0: 5, 0x8007df18: 5}
KIND = dict(pkinds.KIND)
KIND.update({0x80139a9c: 'UNIT', 0x80136608: 'ARMY'})
def jal(w):
    return (w & 0x03FFFFFF) << 2 | 0x80000000 if w >> 26 == 3 else None
def regval(a, reg):
    # search back for li reg
    for b in range(a + 4, a - 40, -4):
        w = img.word(b)
        if w >> 26 == 9 and (w >> 21) & 31 == 0 and (w >> 16) & 31 == reg:
            return w & 0xFFFF
        if b < a and jal(w): break
    return None
def shows(va, n=120):
    out = []
    for a in range(va + 8, va + 4 * n, 4):
        t = jal(img.word(a))
        if t in SHOW:
            out.append(str(regval(a, SHOW[t])))
            if len(out) >= 4: break
        if t == 0x8007cc20 and out: break
        if img.word(a) == 0x03E00008: break
    return out
def unitmode(va):
    # find the jal 0x80139a9c before va and the a1 value
    for b in range(va, va - 120, -4):
        if jal(img.word(b)) == 0x80139a9c:
            return regval(b, 5)
for va in jals(img, 0x8007cc20):
    idx = None
    for b in (va + 4, va - 4, va - 8, va - 12, va - 16):
        w = img.word(b)
        if w >> 16 == 0x2405: idx = w & 0xFFFF; break
        if w == 0x00002821: idx = 0; break
    kind, v = pkinds.source(img, va)
    if kind == 'call':
        src = KIND.get(v, 'fn %08x' % v)
        if src == 'UNIT': src += ' mode %s' % unitmode(va)
    elif kind == 'str':
        src = 'str %08x' % v
    else:
        src = '%s %s' % (kind, v)
    print('%08x p%s = %-22s -> %s' % (va, idx, src, ' '.join(shows(va))))

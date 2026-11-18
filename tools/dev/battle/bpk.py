import sys
sys.path.insert(0, '/home/leto2/Projects/taiko_risshiden_3_translation/tools/dev')
from mips import Image, jals, s16
from pkinds import source, KIND, jal
img = Image('jp:BATTLE.BIN')
# show helpers: func -> arg register holding message number
SHOW = {0x80142f1c: 4, 0x80142edc: 4, 0x80142c34: 5, 0x80142df0: 5, 0x80142cdc: 6, 0x8007df18: 5}
def msgno(va, reg):
    for b in (va + 4, va - 4, va - 8, va - 12, va - 16, va - 20):
        w = img.word(b)
        if w >> 16 == (0x2400 | reg):
            return w & 0xFFFF
        if w >> 16 == (0x3400 | reg):
            return w & 0xFFFF
    return None
shows = []
for f, r in SHOW.items():
    for va in jals(img, f):
        shows.append((va, f, msgno(va, r)))
shows.sort()
lo, hi = int(sys.argv[1]), int(sys.argv[2])
def nextshows(va, n=120):
    out = []
    for a in range(va + 8, va + 4 * n, 4):
        t = jal(img.word(a))
        if t in SHOW:
            out.append('%s@%x' % (msgno(a, SHOW[t]), a))
            if len(out) >= 3: break
        if img.word(a) == 0x03E00008: break
    return out
for va in jals(img, 0x8007cc20):
    idx = None
    for b in (va + 4, va - 4, va - 8, va - 12, va - 16):
        w = img.word(b)
        if w >> 16 == 0x2405: idx = w & 0xFFFF; break
        if w == 0x00002821: idx = 0; break
    kind, v = source(img, va)
    src = KIND.get(v, 'fn %08x' % v) if kind == 'call' else '%s %s' % (kind, v if not isinstance(v,int) else hex(v))
    sh = nextshows(va)
    if any(s.split('@')[0] not in ('None',) and lo <= int(s.split('@')[0]) <= hi for s in sh):
        print('%08x p%s = %-22s -> %s' % (va, idx, src, ' '.join(sh)))

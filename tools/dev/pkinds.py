"""What the program puts into the `{pNN}` inserts of each message: for every call of the string-variable
setter 0x8007cc20(obj, index, ptr), the source of ptr (the getter called just before, or a constant string
address) and the messages shown next (0x8007de38 = block 26, 0x8007dea4 / 0x8007df18 = the current block).
usage: .venv/bin/python tools/dev/pkinds.py [message number]      (all three images)
"""
import sys
from mips import Image, jals, s16

SETP = 0x8007cc20
SHOW = {0x8007de38: 'c', 0x8007dea4: 'm', 0x8007df18: 'M', 0x80142408: 'v'}  # c = block 26; v = MAPPOINT helper:
#   message a1 + politeness variant
MONEY = 0x80139900      # MAPPOINT: formats an amount (0x80142740) and stores it as p0
KIND = {0x8005df44: 'family', 0x8005e034: 'given', 0x8005e124: 'person', 0x80056264: 'castle',
        0x8005cab4: 'clan', 0x8005cabc: 'clan', 0x800585f0: 'province', 0x8005b040: 'item',
        0x8005b9d0: 'command', 0x8005ec20: 'rank', 0x80060b24: 'building',
        0x80056394: 'castle (2)', 0x8008e7b8: 'class word', 0x80058e58: 'region', 0x80054610: 'category/relation',
        0x80142260: "lord's family", 0x80142294: "lord's given", 0x80142740: 'money string'}
# class word = 浪人 ... 娘 (table 0x800b7fc8); region = 東北 ... 九州 (0x800b80e0); category / relation = 武具 芸術品
# 書物 南蛮物 なし 同盟 服従 支配 絶交 険悪 敵視 普通 (0x800b8040)


def jal(w):
    return (w & 0x03FFFFFF) << 2 | 0x80000000 if w >> 26 == 3 else None


def source(img, va):
    """Where $a2 of the setter call at va comes from."""
    lui = {}
    last = None
    for a in range(va - 4 * 24, va + 8, 4):
        if a == va:
            continue
        w = img.word(a)
        op, rs, rt, rd, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31, w & 0xFFFF
        if jal(w):
            last = ('call', jal(w))
        elif op == 0x0F:
            lui[rt] = imm << 16
        elif op in (0x09, 0x0D) and rs in lui and rt == 6:
            src = ('str', (lui[rs] + (s16(imm) if op == 9 else imm)) & 0xFFFFFFFF)
            last = ('a2', src)
        elif op == 0x09 and rs == 28 and rt == 6:
            last = ('a2', ('gp', s16(imm)))
        elif op == 0 and (w & 0x3F) == 0x21 and rd == 6:
            if rs == 2 and last and last[0] == 'call':
                last = ('a2', ('call', last[1]))
            else:
                last = ('a2', ('reg', rs))
    return last[1] if last and last[0] == 'a2' else ('?', 0)


def shows(img, va, n=80):
    out = []
    for a in range(va + 8, va + 4 * n, 4):
        t = jal(img.word(a))
        if t in SHOW:
            num = None
            for b in (a + 4, a - 4, a - 8, a - 12):
                w = img.word(b)
                if w >> 16 == 0x2405:
                    num = w & 0xFFFF; break
            out.append('%s%s' % (SHOW[t], num if num is not None else '?'))
        if img.word(a) == 0x03E00008:
            break
    return out


if __name__ == '__main__':
    want = sys.argv[1] if len(sys.argv) > 1 else None
    for name in ('jp', 'jp:MAPPOINT.BIN', 'jp:BATTLE.BIN'):
        img = Image(name)
        for va in jals(img, SETP):
            idx = None
            for b in (va + 4, va - 4, va - 8, va - 12, va - 16):
                w = img.word(b)
                if w >> 16 == 0x2405:
                    idx = w & 0xFFFF; break
                if w == 0x00002821:
                    idx = 0; break
            kind, v = source(img, va)
            if kind == 'call':
                src = KIND.get(v, 'fn %08x' % v)
            elif kind == 'str':
                src = 'str %08x' % v
            else:
                src = '%s %s' % (kind, v)
            sh = shows(img, va)
            if want is None or any(s[1:] == want for s in sh):
                print('%-8s %08x p%s = %-16s -> %s' % (name[3:11] or 'EXE', va, idx, src, ' '.join(sh[:6])))
        if 'MAPPOINT' in name:
            for va in jals(img, MONEY):
                sh = shows(img, va)
                if want is None or any(s[1:] == want for s in sh):
                    print('%-8s %08x p0 = %-16s -> %s' % ('MAPPOINT', va, 'money string', ' '.join(sh[:6])))

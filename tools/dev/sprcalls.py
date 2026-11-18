"""Constant arguments of the sprite calls f(id, u, v, x; y, w, h) in a code range, with the address of
each constant (for tools/gfx.py). Unoptimised code: `addiu v0, zero, imm; sw v0, N(sp)` and
`addiu aN, zero, imm` before the jal.

usage: sprcalls.py <img> lo hi target [target ...]
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mips


def scan(im, lo, hi, targets, back=24):
    out = []
    for va in range(lo, hi, 4):
        w = im.word(va)
        if w >> 26 != 3 or ((w & 0x3ffffff) << 2 | 0x80000000) not in targets:
            continue
        args, last = {}, None
        for a in range(va - 4, va - 4 * back, -4):
            x = im.word(a)
            op, rs, rt, imm = x >> 26, x >> 21 & 31, x >> 16 & 31, x & 0xffff
            if op == 3:
                break
            if op == 0x2b and rs == 29 and rt == 2:            # sw v0, N(sp)
                last = imm
            elif op == 9 and rs == 0:                          # addiu r, zero, imm
                v = imm - 0x10000 if imm & 0x8000 else imm
                if rt == 2 and last is not None:
                    args.setdefault('sp%x' % last, (v, a)); last = None
                elif 4 <= rt <= 7:
                    args.setdefault('a%d' % (rt - 4), (v, a))
            elif x and not (op == 0x2b and rs == 29):
                last = None
        out.append((va, (w & 0x3ffffff) << 2 | 0x80000000, args))
    return out


if __name__ == '__main__':
    im = mips.Image(sys.argv[1])
    lo, hi = int(sys.argv[2], 0), int(sys.argv[3], 0)
    for va, t, args in scan(im, lo, hi, {int(v, 0) for v in sys.argv[4:]}):
        print('%08x %08x ' % (va, t) + '  '.join('%s=%d@%08x' % (k, v[0], v[1]) for k, v in sorted(args.items())))

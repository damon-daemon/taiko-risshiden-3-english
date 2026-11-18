"""List callers of a function with the constant arguments set just before the call (li/addiu $aN, $zero, imm).
usage: .venv/bin/python tools/dev/callargs.py jp 0x80081d3c [a0-value-filter]
"""
import sys
from mips import Image, jals, s16

def consts(img, va, back=12):
    """$a0-$a3 constants loaded in the `back` instructions before the jal at va (and its delay slot)."""
    out = {}
    for a in list(range(va - 4 * back, va, 4)) + [va + 4]:
        w = img.word(a)
        op, rs, rt, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        if 4 <= rt <= 7 and rs == 0 and op in (0x09, 0x0D):
            out[rt - 4] = s16(imm) if op == 0x09 else imm
        elif op == 0 and (w & 0x3F) == 0x21 and 4 <= ((w >> 11) & 31) <= 7:   # move: unknown value
            out.pop(((w >> 11) & 31) - 4, None)
        elif op == 3:                                                       # an earlier call
            out.clear()
    return out

if __name__ == '__main__':
    img, target = Image(sys.argv[1]), int(sys.argv[2], 0)
    want = int(sys.argv[3], 0) if len(sys.argv) > 3 else None
    for va in jals(img, target):
        c = consts(img, va)
        if want is None or c.get(0) == want:
            print('%08x  %s' % (va, ' '.join('a%d=%#x' % kv for kv in sorted(c.items()))))

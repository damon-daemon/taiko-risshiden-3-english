"""Find lui/ori or lui/addiu constants (unoptimised code builds addresses as lui $v0 + ori $aN, $v0).
usage: .venv/bin/python tools/dev/luis.py jp 0x80179000 [0x80177000 ...]
"""
import sys
from mips import Image, s16
img = Image(sys.argv[1]); want = {int(x, 0) for x in sys.argv[2:]}
for va in range(img.base, img.end - 7, 4):
    w = img.word(va)
    if w >> 26 != 0x0F: continue
    hi = (w & 0xFFFF) << 16
    for k in (4, 8, 12):
        n = img.word(va + k) if va + k < img.end - 3 else 0
        op, imm = n >> 26, n & 0xFFFF
        if op == 0x0D and (hi | imm) in want or op == 0x09 and ((hi + s16(imm)) & 0xFFFFFFFF) in want:
            print('%08x -> %08x' % (va, hi | imm if op == 0x0D else (hi + s16(imm)) & 0xFFFFFFFF)); break

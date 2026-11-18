"""List the text / box drawing calls of a code range with their constant arguments and where each
constant is set (for tools/layout.py: column positions of list screens).

  0x8007b580(x, y, str, colour)       string at pixel x, y
  0x8007b614(x, y, fmt, value)        formatted number / string
  0x80082250(a0, x8, y8, w8, ...)     column box: x and width in 8-px cells
  0x80081ef0(a0, x, y, w8, ...)       window frame
  0x8007b6e4(x, y, w, h)              clear rectangle
  0x80082af8(x, y, w, h, pulse)       cursor bar

usage: drawcalls.py <img> lo hi      img: jp | jp:BATTLE.BIN | jp:MAPPOINT.BIN
Each line: call address, function, then a0-a3 as `value@address` (constant: `addiu rX, zero, imm`
at that address), `+value@address` (added to a computed value), or `?`; strings are shown.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mips

GP = 0x800d6f54
FUNCS = {0x8007b580: 'str', 0x8007b614: 'fmt', 0x80082250: 'box', 0x80081ef0: 'frame', 0x8007a848: 'ink',
         0x8007b6a8: 'str?', 0x8007ad28: 'putc', 0x8007b6e4: 'clear', 0x80082af8: 'bar'}


def string(imgs, va):
    for im in imgs:
        if im.base <= va < im.end:
            o = va - im.base + im.foff
            e = im.data.find(b'\0', o)
            try:
                return im.data[o:e].decode('cp932')
            except UnicodeDecodeError:
                return None
    return None


def english():
    try:
        import progstr
        return progstr.load_tl()
    except Exception:
        return {}


def calls(img, lo, hi, extra=()):
    funcs = dict(FUNCS)
    funcs.update({f: 'f%x' % f for f in extra})
    for va in range(lo, hi, 4):
        w = img.word(va)
        if w >> 26 != 3:
            continue
        f = 0x80000000 | (w & 0x3FFFFFF) << 2
        if f not in funcs:
            continue
        args = {}
        lui = {}
        # walk back to the previous jal / function start: last writer of a0-a3
        p = va - 4
        seq = []
        while p >= lo - 0x100 and img.word(p) >> 26 != 3 and img.word(p) != 0x03e00008:
            seq.append(p)
            p -= 4
        for p in reversed(seq):
            v = img.word(p)
            op, rs, rt, imm = v >> 26, (v >> 21) & 31, (v >> 16) & 31, v & 0xFFFF
            if op == 0x0F:
                lui[rt] = imm << 16
            if op in (0x09, 0x0D) and 4 <= rt <= 7:
                s = mips.s16(imm) if op == 9 else imm
                if rs == 0:
                    args[rt] = ('%d' % s, p, None)
                elif rs == 28:
                    args[rt] = ('gp', p, GP + s)
                elif rs in lui and rs == rt:
                    args[rt] = ('lui', p, (lui[rs] + s) & 0xFFFFFFFF)
                else:
                    args[rt] = ('+%d' % s, p, None)
            elif op == 0 and (v >> 11) & 31 in (4, 5, 6, 7) and v != 0:
                args[(v >> 11) & 31] = ('?', p, None)
            elif 0x20 <= op <= 0x26 and 4 <= rt <= 7:
                args[rt] = ('?', p, None)
        yield va, funcs[f], [args.get(r, ('?', 0, None)) for r in (4, 5, 6, 7)]


def main():
    name, lo, hi = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
    extra = [int(x, 16) for x in sys.argv[4:]]
    img = mips.Image(name)
    imgs = [img] if ':' not in name else [img, mips.Image(name.split(':')[0])]
    tl = english()
    tag = 'PROG' if ':' not in name else name.split(':')[1].split('.')[0]
    for va, f, args in calls(img, lo, hi, extra):
        out = []
        for kind, at, addr in args:
            if addr is not None:
                s = string(imgs, addr)
                en = tl.get('%s:%08x' % (tag, addr)) or tl.get('PROG:%08x' % addr)
                out.append('%08x "%s"%s' % (addr, s, ' = "%s"' % en if en else ''))
            else:
                out.append('%s@%x' % (kind, at) if at else kind)
        print('%08x %-5s %s' % (va, f, '  '.join(out)))


if __name__ == '__main__':
    main()

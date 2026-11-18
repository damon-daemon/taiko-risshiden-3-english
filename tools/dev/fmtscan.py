"""List the sprintf / strcpy / strcat calls that write to a stack buffer, with the room the buffer
has (distance to the next stack offset the function uses, or the frame end) and the string.

usage: fmtscan.py <img> [max room]     img: jp | jp:BATTLE.BIN | jp:MAPPOINT.BIN
Functions: sprintf 0x8007b670(buf, fmt, ...), strcpy 0x800868b4, strcat 0x80086a3c, strncpy 0x8008695c.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mips, drawcalls

FUNCS = {0x8007b670: 'sprintf', 0x800868b4: 'strcpy', 0x80086a3c: 'strcat', 0x8008695c: 'strncpy'}


def frames(img, lo, hi):
    """-> [(start, end, frame size, sorted stack offsets used)]"""
    out, start = [], None
    for va in range(lo, hi, 4):
        w = img.word(va)
        if w >> 16 == 0x27bd and w & 0x8000:
            if start is not None:
                out.append((start, va, size, sorted(offs)))
            start, size, offs = va, 0x10000 - (w & 0xFFFF), set()
        elif start is not None and (w >> 21) & 31 == 29 and (w >> 26 == 9 or 0x20 <= w >> 26 <= 0x2b) and (w >> 16) & 31 != 29:
            offs.add(w & 0xFFFF)
    if start is not None:
        out.append((start, hi, size, sorted(offs)))
    return out


def main():
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1 << 30
    img = mips.Image(name)
    imgs = [img] if ':' not in name else [img, mips.Image(name.split(':')[0])]
    tl = drawcalls.english()
    tag = 'PROG' if ':' not in name else name.split(':')[1].split('.')[0]
    lo = img.base + (0 if ':' not in name else 0x40)
    hi = 0x800afcc0 if ':' not in name else img.base + int.from_bytes(img.data[12:16], 'little')
    for start, end, size, offs in frames(img, lo, hi):
        for va, f, args in drawcalls.calls(img, start, end, FUNCS):
            kind, at, _ = args[0]
            if not kind.startswith('+') or not at or (img.word(at) >> 21) & 31 != 29:
                continue
            off = int(kind)
            room = min([o for o in offs if o > off] + [size]) - off
            if room > limit:
                continue
            k2, at2, addr = args[1]
            s = ''
            if addr is not None:
                en = tl.get('%s:%08x' % (tag, addr)) or tl.get('PROG:%08x' % addr)
                s = '%08x "%s"%s' % (addr, drawcalls.string(imgs, addr), ' = "%s"' % en if en else '')
            print('%08x %-7s sp+%#x room %3d  (func %08x)  %s' % (va, FUNCS[img.word(va) & 0x3FFFFFF and (0x80000000 | (img.word(va) & 0x3FFFFFF) << 2)], off, room, start, s))


if __name__ == '__main__':
    main()

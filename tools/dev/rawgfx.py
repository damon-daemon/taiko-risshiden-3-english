"""Show a raw paletted piece of a headerless graphics file (RGRP / WGRP / KEEP / BG .DAT).

usage: .venv/bin/python tools/dev/rawgfx.py FILE PAL_OFF PIX_OFF W H OUT.png [bpp=8] [scale=1] [x0 y0 w h]
The palette is 16 / 256 u16 at PAL_OFF; pixels are W x H at PIX_OFF (rows of W px). The optional
rectangle crops the picture before scaling.
"""
import struct, sys
from PIL import Image


def pal(d, off, n):
    out = []
    for v in struct.unpack_from('<%dH' % n, d, off):
        out.append(((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3))
    return out


def image(d, po, xo, w, h, bpp=8):
    p = pal(d, po, 1 << bpp)
    if bpp == 8:
        idx = d[xo:xo + w * h]
    else:
        idx = [(b >> s) & 15 for b in d[xo:xo + w * h // 2] for s in (0, 4)]
    im = Image.new('RGB', (w, h))
    im.putdata([p[i] for i in idx])
    return im


if __name__ == '__main__':
    a = sys.argv[1:]
    d = open(a[0], 'rb').read()
    po, xo, w, h = (int(v, 0) for v in a[1:5])
    bpp = int(a[6]) if len(a) > 6 else 8
    s = int(a[7]) if len(a) > 7 else 1
    im = image(d, po, xo, w, h, bpp)
    if len(a) > 8:
        x0, y0, cw, ch = (int(v, 0) for v in a[8:12])
        im = im.crop((x0, y0, x0 + cw, y0 + ch))
    if s > 1:
        im = im.resize((im.width * s, im.height * s), 0)
    im.save(a[5])

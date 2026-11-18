"""English text -> the bytes the patched game draws with our font (vwf.py).

The game's message interpreter and its putchar use lowercase ASCII letters as control codes
(n = newline, z = clear ...), so English lowercase letters are stored as 0xA1-0xBA (single
bytes, not Shift-JIS lead bytes) everywhere: script, names, program strings. The draw routine
maps them back. Macron vowels use the ASCII codes pixfont.MACRONS gives them.
"""
import pixfont

LOWER = 0xA1                              # 'a'
FOLD = {ord(k): v for k, v in pixfont.MACRONS.items()}
FOLD.update({0x2019: "'", 0x2018: "'", 0x201C: '"', 0x201D: '"', 0x2014: '-', 0x2013: '-', 0x2026: '...'})


def enc(s):
    out = bytearray()
    for ch in s.translate(FOLD):
        c = ord(ch)
        if 0x61 <= c <= 0x7A:
            out.append(c - 0x61 + LOWER)
        elif 0x20 <= c < 0x7F:
            out.append(c)
        else:
            raise ValueError('no glyph for %r in %r' % (ch, s))
    return bytes(out)


def width(s):
    g = pixfont.glyphs()
    return sum(g[ch][1] for ch in s.translate(FOLD))

"""Message window: wider text area for English (SLPM_862.68).

The window's text area is 240 px (20 full-width characters) from x = 0x18, inside a frame that has room up to
x = 296. The width is a constant at five places: margins of the normal window (0x8007c700) and of the
indented variant (0x8007c6d8: left 0x28, top 0x88, used when gp-0x6524 is set by 0x80077550..., a screen not
seen yet), 0x8007c76c, and the clear rectangles at 0x8007c8b0 / 0x8007ca44. WIDTH = 272 was tested in the
emulator (new-game messages). The wait icon sits at x >= 276 on the third line: tl.py wraps that line to
ICON_WIDTH.
"""
import struct

EXE_BASE, EXE_OFF = 0x80010000, 0x800
WIDTH = 272
ICON_WIDTH = 248                  # window rows 3-4 of a page that waits for a button (tl.render)
LINES, MAX_LINES = 3, 4           # the Japanese uses 3 lines; the area (height 0x40) holds 4
SITES = (0x8007c6d8, 0x8007c700, 0x8007c76c, 0x8007c8b0, 0x8007ca44)


def patch(exe):
    for va in SITES:
        o = va - EXE_BASE + EXE_OFF
        assert exe[o:o + 2] == b'\xf0\x00', hex(va)
        struct.pack_into('<H', exe, o, WIDTH)

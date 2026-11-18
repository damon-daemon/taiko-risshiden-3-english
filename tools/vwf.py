"""Variable-width English text: our proportional font (pixfont.py) and a new draw routine.

Font: 96 glyphs (ASCII 0x20-0x7F; the macron vowels sit on unused codes, pixfont.MACRONS),
8x12 cells, one byte per row, appended to DATA/FONT.DAT (the file is loaded whole at 0x8015F000,
room up to 0x8016F000): 96 advance bytes at FONT_AT, then 96 x 12 rows.

Program (SLPM_862.68):
- draw 0x8007a9d8(x, y, code) rewritten in place (the original is unoptimised, the new one is
  half the size): Shift-JIS codes and the 8x8 digit mode work as before; any other single byte
  is drawn from our font at any x (1-pixel steps: the 3 VRAM words under the glyph are read
  back, merged and written again) and the routine now returns the advance.
  Bytes 0xA1-0xBA are the lowercase letters (text.py).
- both putchar routines (0x8007ad28, 0x8007b17c): the single-byte path uses that advance
  (it was 6 pixels) and wraps on the real width.
"""
import struct
import asm, pixfont

EXE_BASE, EXE_OFF = 0x80010000, 0x800
FONT_RAM = 0x8015F000
FONT_END = 0x8016F000
NGLYPH = 96

DRAW, DRAW_END = 0x8007a9d8, 0x8007ad28        # draw one glyph (in-place rewrite)
PUT1, PUT1_END = 0x8007af98, 0x8007b0e4        # putchar: single-byte path .. common exit
PUT2, PUT2_END = 0x8007b3b4, 0x8007b4c4        # second putchar: the same
MENU_STRLEN = 0x8008ce58                       # menu box 0x8008ccfc: jal strlen (longest row) -> mwidth
MENU_ROWLEN = 0x8008bb64                       # row draw 0x8008ba..: centred rows (minimum-width menus) used
                                               # strlen x 6 > box -> negative x ("Shimotsuke" at the screen edge)
FIGSP = 0x7F                                   # figure space: blank, as wide as a digit
NUMPAD = 0x80079704                            # number formatter 0x800794c4: `li v0, ' '` = the pad of "%4d"
SJIS_GLYPH, EXPAND, BLIT = 0x80078d9c, 0x80078864, 0x80078980
FONT_PTR, SYM8, ADD_CC = 0x80078d44, 0x800786b8, 0x8007a958
MEMSET, MEMCPY = 0x8008f4ec, 0x8008fdcc
STORE_IMAGE, DRAW_SYNC, LOAD_IMAGE = 0x80097024, 0x8008565c, 0x800856c4
# $gp-relative text state
G_X, G_Y, G_LEFT, G_RIGHT = -0x6520, -0x651c, -0x6518, -0x7528
G_INK, G_PAPER, G_MODE8, G_Y8 = -0x6514, -0x6513, -0x6508, -0x6504
G_PAGE_X, G_PAGE_Y = -0x7530, -0x752c


def font_blob():
    g = pixfont.glyphs()
    adv, rows = bytearray(NGLYPH), bytearray(NGLYPH * 12)
    for i in range(NGLYPH):
        cell, a = g.get(chr(0x20 + i), g['?'])
        if 0x20 + i == FIGSP:
            cell, a = bytes(12), g['0'][1]
        adv[i] = a
        rows[i * 12:i * 12 + 12] = cell
    return bytes(adv + rows)


def font_file(clean):
    """FONT.DAT with our font appended -> (bytes, RAM address of the advance table)."""
    at = (len(clean) + 3) & ~3
    out = clean.ljust(at, b'\0') + font_blob()
    assert FONT_RAM + len(out) <= FONT_END, 'FONT.DAT too big for its buffer'
    return out, FONT_RAM + at


def _index(reg, table_hi_reg, w):
    """reg = byte -> glyph index; table_hi_reg = hi(w)."""
    return [('sltiu', 'at', reg, 0xa1), ('bnez', 'at', '.i1'), ('nop',),
            ('addiu', reg, reg, -0x40),
            '.i1:', ('addiu', reg, reg, -0x20), ('sltiu', 'at', reg, NGLYPH), ('bnez', 'at', '.i2'),
            ('lui', table_hi_reg, asm.hi(w)), ('addiu', reg, 'zero', ord('?') - 0x20), '.i2:']


def _rename(lines, tag):
    f = lambda x: x.replace('.i', '.%s' % tag) if isinstance(x, str) and x.startswith('.i') else x
    return [f(l) if isinstance(l, str) else tuple(f(x) for x in l) for l in lines]


def draw_code(w):
    """The new draw routine + width(byte); w = RAM address of the advance table."""
    L = [
        ('addiu', 'sp', 'sp', -0x88), ('sw', 'ra', 0x24, 'sp'), ('sw', 's0', 0x18, 'sp'),
        ('sw', 's1', 0x1c, 'sp'), ('sw', 's2', 0x20, 'sp'),
        ('addu', 's0', 'a0', 'zero'), ('addu', 's1', 'a1', 'zero'),
        ('sltiu', 'at', 'a2', 0x100), ('bnez', 'at', 'single'), ('addu', 's2', 'a2', 'zero'),
        # Shift-JIS: 12x12
        ('jal', SJIS_GLYPH), ('andi', 'a0', 's2', 0xffff),
        # after our 1-px glyphs the pen may be odd: the 12-px blit only knows even x (it would start at the
        # word below and erase the end of the letter before it), so round up
        ('addiu', 's0', 's0', 1), ('srl', 's0', 's0', 1), ('sll', 's0', 's0', 1),
        ('addu', 'a0', 'v0', 'zero'), ('addiu', 'a1', 'sp', 0x28), ('jal', EXPAND), ('addiu', 'a2', 'zero', 0x12),
        ('addiu', 'a3', 'zero', 12), ('b', 'blit'), ('addiu', 's2', 'zero', 12),
        'single:',
        ('lw', 'v0', G_MODE8, 'gp'), ('nop',), ('beqz', 'v0', 'vwf'), ('nop',),
        # 8x8 mode: digits and a few symbols (font 2), as before
        ('lw', 'v0', G_Y8, 'gp'), ('addiu', 'at', 'zero', 0x20), ('addu', 's1', 's1', 'v0'),
        ('beq', 's2', 'at', 'sp8'), ('addiu', 'at', 'zero', FIGSP), ('bne', 's2', 'at', 'g8'), ('nop',),
        'sp8:',
        ('addiu', 'a0', 'sp', 0x28), ('addu', 'a1', 'zero', 'zero'), ('jal', MEMSET), ('addiu', 'a2', 'zero', 0x20),
        ('b', 'tail8'), ('nop',),
        'g8:',
        ('addiu', 'v0', 's2', -0x30), ('sltiu', 'at', 'v0', 10), ('bnez', 'at', 'have8'), ('nop',),
        ('jal', SYM8), ('andi', 'a0', 's2', 0xff), ('addiu', 'v0', 'v0', 10),
        'have8:',
        ('sll', 's2', 'v0', 5), ('jal', FONT_PTR), ('addiu', 'a0', 'zero', 2),
        ('addu', 'a1', 'v0', 's2'), ('addiu', 'a0', 'sp', 0x28), ('jal', MEMCPY), ('addiu', 'a2', 'zero', 0x20),
        ('addiu', 'a0', 'sp', 0x28), ('jal', ADD_CC), ('addiu', 'a1', 'zero', 0x20),
        'tail8:',
        ('addiu', 'a3', 'zero', 8), ('addiu', 's2', 'zero', 8),
        'blit:',                                       # a3 = width, s2 = height = advance
        ('sw', 's2', 0x10, 'sp'), ('addiu', 'a0', 'sp', 0x28), ('andi', 'a1', 's0', 0xffff),
        ('jal', BLIT), ('andi', 'a2', 's1', 0xffff),
        ('b', 'ret'), ('addu', 'v0', 's2', 'zero'),
        'vwf:',
    ] + _rename(_index('s2', 't0', w), 'a') + [
        ('addiu', 't0', 't0', asm.lo(w)), ('addu', 'v0', 't0', 's2'), ('lbu', 't1', 0, 'v0'),
        ('sll', 'v0', 's2', 1), ('addu', 'v0', 'v0', 's2'), ('sll', 'v0', 'v0', 2), ('addu', 'v0', 'v0', 't0'),
        ('addiu', 's2', 'v0', NGLYPH),                 # glyph rows
        ('sw', 't1', 0x14, 'sp'),                      # advance
        ('srl', 'v0', 's0', 2), ('sltiu', 'at', 's1', 229), ('beqz', 'at', 'done'), ('andi', 't4', 's0', 3),
        # x 312-319: the 3 words would cross the 320-px edge (the glyph was dropped: "Chief Retaine"): use
        # the last 3 words (x 308-319) and cut the columns past the edge
        ('sltiu', 'at', 'v0', 78), ('bnez', 'at', 'xok'), ('sltiu', 'at', 'v0', 80),
        ('beqz', 'at', 'done'), ('addiu', 't4', 's0', -308),
        ('addiu', 'v0', 'zero', 77), ('addiu', 'v1', 'zero', 12), ('subu', 'v1', 'v1', 't4'),
        ('sltu', 'at', 'v1', 't1'), ('beqz', 'at', 'xok'), ('nop',), ('addu', 't1', 'v1', 'zero'),
        'xok:',
        ('sw', 't4', 0x70, 'sp'), ('sw', 't1', 0x74, 'sp'),
        ('lw', 'v1', G_PAGE_X, 'gp'), ('lw', 'a0', G_PAGE_Y, 'gp'),
        ('addu', 'v0', 'v0', 'v1'), ('sh', 'v0', 0x78, 'sp'), ('addu', 'a0', 'a0', 's1'), ('sh', 'a0', 0x7a, 'sp'),
        ('addiu', 'v0', 'zero', 3), ('sh', 'v0', 0x7c, 'sp'), ('addiu', 'v0', 'zero', 12), ('sh', 'v0', 0x7e, 'sp'),
        ('addiu', 'a0', 'sp', 0x78), ('jal', STORE_IMAGE), ('addiu', 'a1', 'sp', 0x28),
        ('jal', DRAW_SYNC), ('nop',),
        ('lw', 't1', 0x74, 'sp'), ('lbu', 't2', G_INK, 'gp'), ('lbu', 't3', G_PAPER, 'gp'),
        ('lw', 't4', 0x70, 'sp'), ('addiu', 't5', 'sp', 0x28), ('addiu', 't6', 'zero', 12),
        'row:',
        ('lbu', 't7', 0, 's2'), ('addu', 't8', 'zero', 'zero'),
        'col:',
        ('sltu', 'at', 't8', 't1'), ('beqz', 'at', 'nextrow'), ('addu', 'v0', 't4', 't8'),
        ('srl', 'v1', 'v0', 1), ('addu', 'v1', 'v1', 't5'), ('andi', 'v0', 'v0', 1), ('sll', 'v0', 'v0', 2),
        ('andi', 'a0', 't7', 0x80), ('addu', 'a1', 't3', 'zero'), ('beqz', 'a0', 'paper'), ('sll', 't7', 't7', 1),
        ('addu', 'a1', 't2', 'zero'),
        'paper:',
        ('sllv', 'a1', 'a1', 'v0'), ('addiu', 'a2', 'zero', 0xf), ('sllv', 'a2', 'a2', 'v0'),
        ('nor', 'a2', 'a2', 'zero'), ('lbu', 'a3', 0, 'v1'), ('nop',),
        ('and', 'a3', 'a3', 'a2'), ('or', 'a3', 'a3', 'a1'), ('sb', 'a3', 0, 'v1'),
        ('b', 'col'), ('addiu', 't8', 't8', 1),
        'nextrow:',
        ('addiu', 's2', 's2', 1), ('addiu', 't6', 't6', -1), ('bnez', 't6', 'row'), ('addiu', 't5', 't5', 6),
        ('lhu', 'a1', 0x78, 'sp'), ('lhu', 'a2', 0x7a, 'sp'), ('addiu', 'v0', 'zero', 12), ('sw', 'v0', 0x10, 'sp'),
        ('addiu', 'a0', 'sp', 0x28), ('jal', LOAD_IMAGE), ('addiu', 'a3', 'zero', 3),
        'done:',
        ('lw', 'v0', 0x14, 'sp'),
        'ret:',
        ('lw', 'ra', 0x24, 'sp'), ('lw', 's2', 0x20, 'sp'), ('lw', 's1', 0x1c, 'sp'), ('lw', 's0', 0x18, 'sp'),
        ('jr', 'ra'), ('addiu', 'sp', 'sp', 0x88),
        'width:',                                      # a0 = byte -> v0 = advance
        ('lw', 'v0', G_MODE8, 'gp'), ('andi', 'a0', 'a0', 0xff), ('bnez', 'v0', 'w8'),
    ] + _rename(_index('a0', 'v0', w), 'b') + [
        ('addu', 'v0', 'v0', 'a0'), ('lbu', 'v0', asm.lo(w), 'v0'), ('jr', 'ra'), ('nop',),
        'w8:',
        ('jr', 'ra'), ('addiu', 'v0', 'zero', 8),
        'mwidth:',                                     # a0 = string -> v0 = its width in 6-px cells, rounded up
        ('addu', 't7', 'ra', 'zero'), ('addu', 't8', 'a0', 'zero'),      # (the menu box 0x8008ccfc sized a box
        ('beqz', 'a0', 'm_end'), ('addu', 't9', 'zero', 'zero'),         # by strlen x 6: "Armaments" was cut)
        'm_loop:',
        ('lbu', 'a0', 0, 't8'), ('nop',), ('beqz', 'a0', 'm_end'), ('addiu', 'v0', 'a0', -0x81),
        ('sltiu', 'at', 'v0', 0x1f), ('bnez', 'at', 'm_sjis'), ('sltiu', 'at', 'a0', 0xe0),
        ('beqz', 'at', 'm_sjis'), ('nop',),
        ('jal', 'width'), ('addiu', 't8', 't8', 1), ('b', 'm_loop'), ('addu', 't9', 't9', 'v0'),
        'm_sjis:',
        ('addiu', 't8', 't8', 2), ('b', 'm_loop'), ('addiu', 't9', 't9', 12),
        'm_end:',
        ('addiu', 't9', 't9', 5), ('addiu', 'at', 'zero', 6), ('divu', 't9', 'at'), ('mflo', 'v0'),
        ('jr', 't7'), ('nop',),
    ]
    return L


def _put(exe, addr, end, lines):
    code = asm.assemble(addr, lines)
    assert len(code) <= end - addr, 'patch at %08x: %d bytes over' % (addr, len(code) - (end - addr))
    o = addr - EXE_BASE + EXE_OFF
    exe[o:o + end - addr] = code.ljust(end - addr, b'\0')
    return (end - addr - len(code))


def patch(exe, w):
    """exe: bytearray of SLPM_862.68; w = RAM address of the advance table (font_file)."""
    L = draw_code(w)
    lab = asm.labels(DRAW, L)
    free = _put(exe, DRAW, DRAW_END, L)
    o = NUMPAD - EXE_BASE + EXE_OFF
    assert exe[o:o + 4] == bytes.fromhex('20000224'), 'number pad site'
    exe[o] = FIGSP          # right-aligned numbers: pad with a digit-wide blank (the space is 3 px, a digit 6)
    _put(exe, MENU_STRLEN, MENU_STRLEN + 4, [('jal', lab['mwidth'])])
    _put(exe, MENU_ROWLEN, MENU_ROWLEN + 4, [('jal', lab['mwidth'])])
    _put(exe, PUT1, PUT1_END, [
        ('andi', 'v0', 's0', 0xff), ('sltiu', 'at', 'v0', 0x20), ('bnez', 'at', PUT1_END), ('nop',),
        ('jal', lab['width']), ('addu', 'a0', 's0', 'zero'),
        ('lw', 'v1', G_X, 'gp'), ('lw', 'a0', G_RIGHT, 'gp'), ('addu', 'v0', 'v1', 'v0'),
        ('sltu', 'at', 'a0', 'v0'), ('beqz', 'at', 'nw'), ('nop',),
        ('lw', 'v0', G_LEFT, 'gp'), ('lw', 'v1', G_Y, 'gp'), ('sw', 'v0', G_X, 'gp'),
        ('addiu', 'v1', 'v1', 0x10), ('sw', 'v1', G_Y, 'gp'),
        'nw:',
        ('lw', 'a0', G_X, 'gp'), ('lw', 'a1', G_Y, 'gp'), ('jal', DRAW), ('andi', 'a2', 's0', 0xff),
        ('lw', 'v1', G_X, 'gp'), ('nop',), ('addu', 'v1', 'v1', 'v0'), ('b', PUT1_END), ('sw', 'v1', G_X, 'gp'),
    ])
    _put(exe, PUT2, PUT2_END, [
        ('andi', 'v0', 's0', 0xff), ('sltiu', 'at', 'v0', 0x20), ('bnez', 'at', PUT2_END), ('nop',),
        ('lw', 'a0', G_X, 'gp'), ('lw', 'a1', G_Y, 'gp'), ('jal', DRAW), ('andi', 'a2', 's0', 0xff),
        ('lw', 'v1', G_X, 'gp'), ('nop',), ('addu', 'v1', 'v1', 'v0'), ('b', PUT2_END), ('sw', 'v1', G_X, 'gp'),
    ])
    return free

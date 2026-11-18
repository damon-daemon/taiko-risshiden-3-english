"""English name entry (player names at a new game and in the rename event, castle naming).

The game's screen 0x80077554(buf, max, kind, cancel): a kana grid of 10 groups x 5 cells (cell =
group * 5 + i; label pointers at 0x800b45b0; groups 0-4 are the rows of the left block, 5-9 of the
right block, so the screen shows 5 rows of 10 cells) and the buttons OK (cell 0x32) / Back (0x33) /
Cancel (0x34, when `cancel`) on the right. Circle on a cell called 0x800768ec(cell, buf, max, len)
-> new length: a candidate window (kana variants and the kanji read that way; 2 bytes per pick).
Wrappers: 0x80078548 family (kind 0), 0x8007857c given (1), 0x800785b0 castle (2, with Cancel).

English: the grid holds letters and Circle appends the cell's letter at once (no candidate window).
Upper case at the start and after a space, lower case otherwise; the `Aa` cell switches the case of
the last letter. Back and Cross delete one letter. Limits: family 12, given 9 (the packed fields of
player.py), castle 8 (the record field). The name line is drawn with the proportional font, so the
cursor mark is placed from the real width.

All new code and data replace the candidate window function (AREA; dead once its only call is ours):
  pick    0x800768ec(cell, buf, max, len) -> v0 = length, v1 = 1 (the caller's "redraw the name" flag)
  cell    draw a grid label centred in its cell (x offset = the byte before the string)
  pwidth  pixel width of a string
  UP / LO 50 bytes each: upper / lower code per cell (0 = empty cell, 1 = the Aa cell)
  the label strings
Also patched: the new-game caller 0x80076234 (frame 0x30 -> 0x40: family 20 bytes at sp+0x1c, given
16 bytes at sp+0x30; it kept the given name in 8 bytes). The rename event (MAPPOINT 0x80125410) has
32 bytes and castle naming a static buffer (0x80150f4c, 9 bytes): both fit as they are.
"""
import os, struct, sys

sys.path.insert(0, os.path.dirname(__file__))
import asm, player, text, vwf

EXE_BASE, EXE_OFF = 0x80010000, 0x800
AREA = (0x800768ec, 0x8007743c)             # the candidate window function
SPARE = 0x800772e0                          # AREA from here on belongs to layout.py (FITNAME, FITPAGE)
CELLS = 0x800b45b0                          # 50 label pointers
PUTS = 0x8007b580                           # puts(x, y, str, colour)
WIDTH = asm.labels(vwf.DRAW, vwf.draw_code(0))['width']      # a0 = byte -> v0 = advance (keeps t7-t9)
FAMILY, GIVEN, CASTLE = player.FAMILY_N, player.GIVEN_N, 8
NAME_X = 0x58                               # the name line (was 0x40: "Family" did not fit before it)
NAME_W = 0x78                               # cleared width of the name line
BTN_W = 0x26                                # cursor box on the buttons (was 0x1a)
TOGGLE = 1


def _letters(s):
    return [(c, c, c.lower()) for c in s]


# rows of 10 cells: (label, upper, lower) or None
GRID = [
    _letters('ABCDEFGHIJ'),
    _letters('KLMNOPQRST'),
    _letters('UVWXYZ') + [('Ō', 'Ō', 'ō'), ('Ū', 'Ū', 'ū'), ("'", "'", "'"), ('-', '-', '-')],
    [None] * 10,
    [('Aa', TOGGLE, TOGGLE), None, ('Space', ' ', ' ')] + [None] * 7,
]


def _code(c):
    return c if isinstance(c, int) else text.enc(c)[0]


def _cell(r, c):
    return (r + (5 if c >= 5 else 0)) * 5 + c % 5


def tables():
    up, lo_ = bytearray(50), bytearray(50)
    for r, row in enumerate(GRID):
        for c, cell in enumerate(row):
            if cell:
                up[_cell(r, c)], lo_[_cell(r, c)] = _code(cell[1]), _code(cell[2])
    return bytes(up), bytes(lo_)


def listing():
    hi, lo = asm.hi, asm.lo
    return [
        'pick:',                                # a0 = cell, a1 = buf, a2 = max, a3 = len
        ('lui', 't0', 'UPHI'), ('addiu', 't0', 't0', 'UPLO'),
        ('addu', 't1', 't0', 'a0'), ('lbu', 't2', 0, 't1'), ('lbu', 't3', 50, 't1'),
        ('addu', 'v0', 'a3', 'zero'),
        ('beqz', 't2', 'ret'), ('addiu', 'v1', 'zero', 1),
        ('addu', 't7', 'a1', 'a3'),
        ('addiu', 't4', 'zero', TOGGLE),
        ('beq', 't2', 't4', 'toggle'), ('nop',),
        ('sltu', 't4', 'a3', 'a2'), ('beqz', 't4', 'ret'), ('nop',),
        ('beqz', 'a3', 'store'), ('nop',),      # first letter: upper case
        ('lbu', 't4', -1, 't7'), ('addiu', 't5', 'zero', 0x20), ('nop',),
        ('beq', 't4', 't5', 'store'), ('nop',), # after a space: upper case
        ('addu', 't2', 't3', 'zero'),
        'store:',
        ('sb', 't2', 0, 't7'), ('sb', 'zero', 1, 't7'), ('addiu', 'v0', 'a3', 1),
        'ret:',
        ('jr', 'ra'), ('nop',),
        'toggle:',                              # the last letter
        ('beqz', 'a3', 'ret'), ('nop',),
        ('lbu', 't4', -1, 't7'), ('addiu', 't1', 't0', 49),
        'tloop:',
        ('lbu', 't2', 0, 't1'), ('lbu', 't3', 50, 't1'), ('nop',),
        ('beq', 't2', 't3', 'tnext'), ('nop',),
        ('beq', 't4', 't2', 'tset'), ('addu', 't5', 't3', 'zero'),
        ('beq', 't4', 't3', 'tset'), ('addu', 't5', 't2', 'zero'),
        'tnext:',
        ('bne', 't1', 't0', 'tloop'), ('addiu', 't1', 't1', -1),
        ('jr', 'ra'), ('nop',),
        'tset:',
        ('jr', 'ra'), ('sb', 't5', -1, 't7'),

        'cell:',                                # puts with the x offset stored before the string
        ('lbu', 't0', -1, 'a2'), ('nop',),
        ('j', PUTS), ('addu', 'a0', 'a0', 't0'),

        'pwidth:',                              # a0 = string -> v0 = pixels
        ('addu', 't7', 'ra', 'zero'), ('addu', 't8', 'a0', 'zero'), ('addu', 't9', 'zero', 'zero'),
        'wloop:',
        ('lbu', 'a0', 0, 't8'), ('nop',), ('beqz', 'a0', 'wend'), ('nop',),
        ('jal', WIDTH), ('addiu', 't8', 't8', 1), ('b', 'wloop'), ('addu', 't9', 't9', 'v0'),
        'wend:',
        ('jr', 't7'), ('addu', 'v0', 't9', 'zero'),
        'UP:',
    ]


def blob():
    """-> (bytes at AREA[0], labels, [label string address per cell])"""
    lines = listing()
    L = asm.labels(AREA[0], lines)
    up = L['UP']
    res = [tuple((asm.hi(up) if x == 'UPHI' else asm.lo(up) if x == 'UPLO' else x) for x in ln)
           if isinstance(ln, tuple) else ln for ln in lines]
    out = bytearray(asm.assemble(AREA[0], res) + b''.join(tables()))
    out += bytes([0, 0])                    # the empty label (offset byte, NUL)
    cells = [AREA[0] + len(out) - 1] * 50
    for r, row in enumerate(GRID):
        for c, cell in enumerate(row):
            if cell:
                w = text.width(cell[0])
                out += bytes([(12 - w) // 2 if w <= 12 else 0])
                cells[_cell(r, c)] = AREA[0] + len(out)
                out += text.enc(cell[0]) + b'\0'
    assert AREA[0] + len(out) <= SPARE
    return bytes(out), L, cells


def _sites(L):
    """(address, clean first word or None, replacement lines)"""
    name = lambda a, x: (a, 0x24040040, [('addiu', 'a0', 'zero', x)])
    return [
        (0x800776a4, 0x0c01ed60, [('jal', L['cell'])]),                    # grid labels
        name(0x8007774c, NAME_X),
        # cursor mark under the name: x = len * 6 + 0x40 -> real width
        (0x80077800, 0x8fa30050, [('lw', 'a0', 0xa0, 'sp'), ('jal', L['pwidth']), ('nop',), ('nop',), ('nop',),
                                  ('addiu', 'v0', 'v0', NAME_X)]),
        (0x80078350, 0x8fa30050, [('lw', 'a0', 0xa0, 'sp'), ('jal', L['pwidth']), ('nop',), ('nop',), ('nop',),
                                  ('addiu', 'v0', 'v0', NAME_X - 1)]),
        # Circle on a cell: pick, then redraw the name line
        (0x8007823c, 0x8fa600a4, [('lw', 'a2', 0xa4, 'sp'), ('lw', 'a1', 0xa0, 'sp'), ('lw', 'a3', 0x50, 'sp'),
                                  ('jal', L['pick']), ('addu', 'a0', 's0', 'zero'),
                                  ('sw', 'v0', 0x50, 'sp'), ('sw', 'v1', 0x60, 'sp')]),
        # Back / Cross removed two bytes: the second step goes
        (0x80078190, 0x8fa20050, [('nop',)] * 8),
        (0x800782b4, 0x8fa20050, [('nop',)] * 8),
        # redraw of the name line
        name(0x80078320, NAME_X),
        (0x80078328, 0x24060030, [('addiu', 'a2', 'zero', NAME_W)]),
        name(0x80078338, NAME_X),
        # cursor box on the buttons
        (0x80078044, 0x2402001a, [('addiu', 'v0', 'zero', BTN_W)]),
        (0x800783d0, 0x2402001a, [('addiu', 'v0', 'zero', BTN_W)]),
        # limits
        (0x80078558, 0x24050007, [('addiu', 'a1', 'zero', FAMILY)]),
        (0x8007858c, 0x24050007, [('addiu', 'a1', 'zero', GIVEN)]),
        (0x800785c0, 0x24050009, [('addiu', 'a1', 'zero', CASTLE)]),
        # the new-game caller: bigger frame, the given name at sp+0x30
        (0x80076234, 0x27bdffd0, [('addiu', 'sp', 'sp', -0x40)]),
        (0x800762d4, 0x27bd0030, [('addiu', 'sp', 'sp', 0x40)]),
        (0x80076280, 0x27a40028, [('addiu', 'a0', 'sp', 0x30)]),
        (0x8007629c, 0x27a40028, [('addiu', 'a0', 'sp', 0x30)]),
        (0x800762b4, 0x27a40028, [('addiu', 'a0', 'sp', 0x30)]),
    ]


def patch(exe):
    """exe: bytearray of SLPM_862.68, after every other patch. -> bytes free in AREA"""
    o = lambda va: va - EXE_BASE + EXE_OFF
    w = lambda va: struct.unpack_from('<I', exe, o(va))[0]
    jal = 0x0c000000 | AREA[0] >> 2 & 0x3ffffff
    calls = [EXE_BASE + i - EXE_OFF for i in range(EXE_OFF, len(exe) - 3, 4)
             if struct.unpack_from('<I', exe, i)[0] == jal]
    assert calls == [0x8007824c], [hex(x) for x in calls]
    code, L, cells = blob()
    for va, old, new in _sites(L):
        assert w(va) == old, 'name entry site %08x: %08x' % (va, w(va))
        b = asm.assemble(va, new)
        exe[o(va):o(va) + len(b)] = b
    exe[o(AREA[0]):o(SPARE)] = code.ljust(SPARE - AREA[0], b'\0')
    for i, p in enumerate(cells):
        assert EXE_BASE <= w(CELLS + 4 * i) < 0x800d7000
        struct.pack_into('<I', exe, o(CELLS + 4 * i), p)
    return SPARE - AREA[0] - len(code)


if __name__ == '__main__':
    code, L, cells = blob()
    print('%d of %d bytes; %s' % (len(code), AREA[1] - AREA[0], ', '.join('%s %#x' % kv for kv in L.items())))
    up, lo_ = tables()
    for r in range(5):
        print(' '.join('%02x/%02x' % (up[_cell(r, c)], lo_[_cell(r, c)]) for c in range(10)))

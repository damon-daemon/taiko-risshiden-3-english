"""Runtime word wrap for message-window pages with inserts (SLPM_862.68).

tl.py wraps at build time with worst-case insert widths, so lines broke early after a name ("Then I assign
Hire Ashigaru to / Kazumasu."). The message interpreter 0x8007d778(obj, buf, which) is rewritten in place
(the original is 0x6c0 bytes of unoptimised code; same grammar, msgfile.py) and gains:

- mode bytes at the start of a page (bytes below 0x20 draw nothing anywhere else): SOFT = every space of the
  page is a soft space, SOFT_WAIT = the same on a page that waits for a button (window rows y >= ICON_Y end
  ICON px earlier: the wait icon). `z` (clear) ends the mode; `j` keeps it (a page cut over two strings).
- PLURAL (byte 3, tl.py `{s}`): the next byte is skipped when the last number insert printed "1"
  ("{b00} day{s}" -> "1 day"). It reads NUM, so it must stand in the word right after its number (the
  look-ahead formats the numbers of the following word into NUM too). Works in every mode.
- soft space: the width of the next word is measured from the source (glyph advances; an insert = its string
  up to its first space, fetched with the same getters as the print) and the space becomes a newline when
  x + space + word passes the right limit.
- inserts (a / e / p / b) are printed by an own loop that asks the same question at each space inside the
  insert ("Takigawa / Kazumasu" instead of a break inside a word); this is on in every mode.

The look-ahead calls the name getters, which rotate through buffers that the caller's `p` strings may live
in: the rotation counters (names.G_ROT, the 8 counter bytes at tables.BUFS) are saved before and restored
after, so the real print reuses the same slots. Numbers are formatted into NUM (static).
"""
import asm, msgpack, names, pixfont, tables, vwf, window

INTERP, INTERP_END = 0x8007d778, 0x8007de38
SOFT, SOFT_WAIT, PLURAL = 1, 2, 3
ICON_Y, ICON = 0xc4, window.WIDTH - window.ICON_WIDTH
NUM = 0x8016EFE0                  # 32 bytes in the FONT.DAT buffer tail, after player.BUF_END
PUTCHAR, SYNC, CLEAR, WAIT, AUTO, WAIT2, PAUSE = (0x8007ad28, 0x80085694, 0x8007c9e8, 0x8007cc60, 0x8005939c,
                                                  0x8007ce34, 0x80085ddc)
FACE, NAMEBOX, PLAYER_ID, SUB_C, SUB_D, COPY, COND = (0x8007ca90, 0x8007cf5c, 0x800541ec, 0x8007d00c, 0x8008b0d0,
                                                      0x80086b48, 0x8008d68c)
SPRINTF, CASTLE, G_FMT, G_STATE = 0x8007b670, 0x80056394, -0x751c, -0x6512
OBJ_SLOTS, OBJ_NUMS, OBJ_STRS, OBJ_FLAG = 0x1c4, 0x1d8, 0x1ec, 0x204


def code(width):
    """width = address of vwf's width(byte) routine."""
    hi, lo = asm.hi, asm.lo
    u16 = lambda reg, base, off: [('lbu', 't0', off, base), ('lbu', 't1', off + 1, base), ('sll', 't0', 't0', 8),
                                  ('or', reg, 't0', 't1')]
    rot = [(o, 'gp') for o in names.G_ROT] + [(0, 't3'), (4, 't3')]
    return [
        # ---- interpreter. s0 = source, s1 = its end, s2 = obj, s3 = mode, s4 = Shift-JIS / ESC pending, s5 = temp
        ('addiu', 'sp', 'sp', -0x38), ('sw', 'ra', 0x34, 'sp'), ('sw', 's5', 0x30, 'sp'), ('sw', 's4', 0x2c, 'sp'),
        ('sw', 's3', 0x28, 'sp'), ('sw', 's2', 0x24, 'sp'), ('sw', 's1', 0x20, 'sp'), ('sw', 's0', 0x1c, 'sp'),
        ('sw', 'a1', 0x14, 'sp'), ('sw', 'a2', 0x18, 'sp'),
        ('addu', 's2', 'a0', 'zero'), ('addu', 's0', 'a1', 'zero'), ('addu', 's3', 'zero', 'zero'),
        ('lw', 'v0', OBJ_FLAG, 's2'), ('addu', 's4', 'zero', 'zero'),
        ('beqz', 'v0', 'loop'), ('addiu', 's1', 's0', 200),
        ('jal', SYNC), ('addu', 'a0', 'zero', 'zero'),
        'loop:',
        ('sltu', 'at', 's0', 's1'), ('beqz', 'at', 'end'), ('nop',),
        ('lbu', 'a0', 0, 's0'), ('nop',),
        ('beqz', 'a0', 'end'), ('addiu', 'v0', 'a0', -0x61),
        ('bnez', 's4', 'lit'), ('sltiu', 'at', 'a0', 4),
        ('beqz', 'at', 'nomode'), ('sltiu', 'at', 'v0', 26),
        ('addiu', 'at', 'zero', PLURAL), ('beq', 'a0', 'at', 'plural'), ('addiu', 's0', 's0', 1),
        ('b', 'loop'), ('addu', 's3', 'a0', 'zero'),
        'plural:',                                   # NUM == "1": skip the next byte
        ('lui', 't0', hi(NUM)), ('lbu', 't1', lo(NUM), 't0'), ('lbu', 't2', lo(NUM) + 1, 't0'),
        ('xori', 't1', 't1', ord('1')), ('or', 't1', 't1', 't2'), ('sltiu', 't1', 't1', 1),
        ('b', 'loop'), ('addu', 's0', 's0', 't1'),
        'nomode:',
        ('bnez', 'at', 'code'), ('addiu', 'at', 'zero', 0x20),
        ('bne', 'a0', 'at', 'lit'), ('nop',),
        ('beqz', 's3', 'lit'), ('nop',),
        ('addu', 'a0', 'zero', 'zero'), ('jal', 'measure'), ('addiu', 'a1', 's0', 1),
        ('jal', 'brk'), ('addu', 'a0', 'v0', 'zero'),
        'lit:',
        ('jal', PUTCHAR), ('addiu', 's0', 's0', 1),
        ('b', 'loop'), ('addu', 's4', 'v0', 'zero'),
        'code:',
        ('addiu', 'at', 'zero', ord('n')), ('beq', 'a0', 'at', 'lit'), ('addiu', 'at', 'zero', ord('z')),
        ('bne', 'a0', 'at', 'c_g'), ('addiu', 'at', 'zero', ord('g')),
        ('addu', 's3', 'zero', 'zero'), ('jal', CLEAR), ('addu', 'a0', 's2', 'zero'),
        ('b', 'loop'), ('addiu', 's0', 's0', 1),
        'c_g:',
        ('bne', 'a0', 'at', 'c_v'), ('addiu', 'at', 'zero', ord('v')),
        ('jal', WAIT), ('addu', 'a0', 's2', 'zero'),
        'sync0:',
        ('addiu', 's0', 's0', 1), ('jal', SYNC), ('addu', 'a0', 'zero', 'zero'),
        ('b', 'loop'), ('nop',),
        'c_v:',
        ('bne', 'a0', 'at', 'c_w'), ('addiu', 'at', 'zero', ord('w')),
        ('jal', AUTO), ('addiu', 's0', 's0', 1),
        ('beqz', 'v0', 'v_auto'), ('addu', 'a0', 's2', 'zero'),
        ('jal', WAIT), ('nop',), ('b', 'loop'), ('nop',),
        'v_auto:',
        ('jal', WAIT2), ('nop',), ('b', 'loop'), ('nop',),
        'c_w:',
        ('bne', 'a0', 'at', 'c_f'), ('addiu', 'at', 'zero', ord('f')),
        ('jal', SYNC), ('addiu', 'a0', 'zero', 1),
        ('jal', PAUSE), ('addiu', 'a0', 'zero', 0x14),
        ('b', 'sync0'), ('nop',),
        'c_f:',
        ('bne', 'a0', 'at', 'c_s'), ('addiu', 'at', 'zero', ord('s')),
    ] + u16('a1', 's0', 1) + [
        ('jal', FACE), ('addu', 'a0', 's2', 'zero'),
        ('b', 'loop'), ('addiu', 's0', 's0', 3),
        'c_s:',
        ('bne', 'a0', 'at', 'c_c'), ('addiu', 'at', 'zero', ord('c')),
    ] + u16('s5', 's0', 1) + [
        ('addiu', 'v0', 's5', -800), ('sltiu', 'at', 'v0', 5), ('beqz', 'at', 's_me'), ('sll', 'v0', 'v0', 2),
        ('addu', 'v0', 'v0', 's2'), ('lw', 's5', OBJ_SLOTS, 'v0'), ('b', 's_face'), ('nop',),
        's_me:',
        ('addiu', 'at', 'zero', 999), ('bne', 's5', 'at', 's_box'), ('nop',),
        ('jal', PLAYER_ID), ('addu', 'a0', 'zero', 'zero'),
        ('addu', 's5', 'v0', 'zero'),
        's_face:',
        ('addu', 'a0', 's2', 'zero'), ('jal', FACE), ('addu', 'a1', 's5', 'zero'),
        's_box:',
        ('addu', 'a0', 's2', 'zero'), ('jal', NAMEBOX), ('addu', 'a1', 's5', 'zero'),
        ('b', 'loop'), ('addiu', 's0', 's0', 3),
        'c_c:',
        ('bne', 'a0', 'at', 'c_d'), ('addiu', 'at', 'zero', ord('d')),
        ('lbu', 'a1', 1, 's0'), ('jal', SUB_C), ('addu', 'a0', 's2', 'zero'),
        ('b', 'loop'), ('addiu', 's0', 's0', 2),
        'c_d:',
        ('bne', 'a0', 'at', 'c_j'), ('addiu', 'at', 'zero', ord('j')),
        ('lbu', 'a0', 1, 's0'), ('jal', SUB_D), ('nop',),
        ('b', 'loop'), ('addiu', 's0', 's0', 2),
        'c_j:',
        ('bne', 'a0', 'at', 'c_y'), ('addiu', 'at', 'zero', ord('y')),
    ] + u16('a1', 's0', 1) + [
        ('lw', 'v0', 0x18, 'sp'), ('addu', 'a0', 's2', 'zero'),
        ('bnez', 'v0', 'j_cur'), ('nop',),
        ('jal', msgpack.LOOKUP26), ('nop',), ('b', 'j_copy'), ('nop',),
        'j_cur:',
        ('jal', msgpack.LOOKUP), ('nop',),
        'j_copy:',
        ('lw', 'a1', 0x14, 'sp'), ('addu', 'a0', 'v0', 'zero'), ('jal', COPY), ('addiu', 'a2', 'zero', 200),
        ('lw', 's0', 0x14, 'sp'), ('nop',), ('b', 'sync0'), ('addiu', 's0', 's0', -1),
        'c_y:',
        ('bne', 'a0', 'at', 'c_ins'), ('nop',),
        ('jal', COND), ('nop',),
        ('beqz', 'v0', 'y_n'), ('addiu', 't2', 's0', 4),
        ('addiu', 't2', 's0', 2),
        'y_n:',
    ] + u16('a1', 't2', 0) + [
        ('jal', msgpack.LOOKUP), ('addu', 'a0', 's2', 'zero'),
        ('lw', 'a1', 0x14, 'sp'), ('addu', 'a0', 'v0', 'zero'), ('jal', COPY), ('addiu', 'a2', 'zero', 200),
        ('lw', 's0', 0x14, 'sp'), ('b', 'loop'), ('nop',),
        'c_ins:',
        ('addiu', 'at', 'zero', ord('a')), ('beq', 'a0', 'at', 'ins'), ('addiu', 'at', 'zero', ord('b')),
        ('beq', 'a0', 'at', 'ins'), ('addiu', 'at', 'zero', ord('e')),
        ('beq', 'a0', 'at', 'ins'), ('addiu', 'at', 'zero', ord('p')),
        ('bne', 'a0', 'at', 'lit'), ('nop',),
        'ins:',
        ('jal', 'resolve'), ('addu', 'a0', 's0', 'zero'),
        ('addu', 's0', 's0', 'v1'), ('sb', 'zero', G_STATE, 'gp'), ('addu', 's5', 'v0', 'zero'),
        'i_loop:',
        ('lbu', 'a0', 0, 's5'), ('addiu', 'at', 'zero', 0x20),
        ('beqz', 'a0', 'loop'), ('addiu', 's5', 's5', 1),
        ('bne', 'a0', 'at', 'i_put'), ('nop',),
        ('addu', 'a0', 's5', 'zero'), ('jal', 'measure'), ('addu', 'a1', 's0', 'zero'),
        ('jal', 'brk'), ('addu', 'a0', 'v0', 'zero'),
        'i_put:',
        ('jal', PUTCHAR), ('nop',),
        ('b', 'i_loop'), ('nop',),
        'end:',
        ('lw', 'v0', OBJ_FLAG, 's2'), ('nop',), ('beqz', 'v0', 'ret'), ('nop',),
        ('jal', SYNC), ('addiu', 'a0', 'zero', 1),
        'ret:',
        ('lw', 'ra', 0x34, 'sp'), ('lw', 's5', 0x30, 'sp'), ('lw', 's4', 0x2c, 'sp'), ('lw', 's3', 0x28, 'sp'),
        ('lw', 's2', 0x24, 'sp'), ('lw', 's1', 0x20, 'sp'), ('lw', 's0', 0x1c, 'sp'),
        ('jr', 'ra'), ('addiu', 'sp', 'sp', 0x38),

        # ---- brk(a0 = width of the next word; s3 = mode) -> a0 = ' ' or 'n'
        'brk:',
        ('lw', 't0', vwf.G_X, 'gp'), ('lw', 't1', vwf.G_RIGHT, 'gp'), ('lw', 't2', vwf.G_Y, 'gp'),
        ('addiu', 'at', 'zero', SOFT_WAIT), ('bne', 's3', 'at', 'b_cmp'), ('addu', 't0', 't0', 'a0'),
        ('sltiu', 'at', 't2', ICON_Y), ('bnez', 'at', 'b_cmp'), ('nop',),
        ('addiu', 't1', 't1', -ICON),
        'b_cmp:',
        ('addiu', 't0', 't0', pixfont.glyphs()[' '][1]), ('sltu', 'at', 't1', 't0'),
        ('beqz', 'at', 'b_out'), ('addiu', 'a0', 'zero', 0x20),
        ('addiu', 'a0', 'zero', ord('n')),
        'b_out:',
        ('jr', 'ra'), ('nop',),

        # ---- chw(a0 = byte) -> v0 = advance, v1 = 1 when it is a Shift-JIS lead byte (12 px, 2 bytes)
        'chw:',
        ('addiu', 'v0', 'a0', -0x81), ('sltiu', 'at', 'v0', 0x1f), ('bnez', 'at', 'w_sjis'), ('sltiu', 'at', 'a0', 0xe0),
        ('beqz', 'at', 'w_sjis'), ('nop',),
        ('j', width), ('addu', 'v1', 'zero', 'zero'),
        'w_sjis:',
        ('addiu', 'v1', 'zero', 1), ('jr', 'ra'), ('addiu', 'v0', 'zero', 12),

        # ---- resolve(a0 = source at an insert code; s2 = obj) -> v0 = its string, v1 = bytes of the code
        'resolve:',
        ('addiu', 'sp', 'sp', -0x18), ('sw', 'ra', 0x14, 'sp'), ('sw', 's0', 0x10, 'sp'),
        ('lbu', 'v0', 0, 'a0'), ('lbu', 's0', 1, 'a0'), ('addiu', 'at', 'zero', ord('p')),
        ('sll', 't2', 's0', 2), ('bne', 'v0', 'at', 'r_b'), ('addu', 't2', 't2', 's2'),
        ('lw', 'v0', OBJ_STRS, 't2'), ('b', 'r_out'), ('addiu', 'v1', 'zero', 2),
        'r_b:',
        ('addiu', 'at', 'zero', ord('b')), ('bne', 'v0', 'at', 'r_ae'), ('nop',),
        ('lw', 'a2', OBJ_NUMS, 't2'), ('lui', 'a0', hi(NUM)), ('addiu', 'a0', 'a0', lo(NUM)),
        ('jal', SPRINTF), ('addiu', 'a1', 'gp', G_FMT),
        ('lui', 'v0', hi(NUM)), ('addiu', 'v0', 'v0', lo(NUM)), ('b', 'r_out'), ('addiu', 'v1', 'zero', 2),
        'r_ae:',
    ] + u16('a0', 'a0', 2) + [
        ('addiu', 'at', 'zero', ord('e')), ('bne', 'v0', 'at', 'r_a'), ('xori', 'a1', 's0', ord('s')),
        ('jal', CASTLE), ('sltu', 'a1', 'zero', 'a1'),
        ('b', 'r_out'), ('addiu', 'v1', 'zero', 4),
        'r_a:',
        ('addiu', 'at', 'zero', 999), ('bne', 'a0', 'at', 'r_kind'), ('nop',),
        ('jal', PLAYER_ID), ('addu', 'a0', 'zero', 'zero'),
        ('addu', 'a0', 'v0', 'zero'),
        'r_kind:',
        ('addiu', 'at', 'zero', ord('s')), ('bne', 's0', 'at', 'r_m'), ('addiu', 'at', 'zero', ord('m')),
        ('jal', names.FAMILY), ('nop',), ('b', 'r_out'), ('addiu', 'v1', 'zero', 4),
        'r_m:',
        ('bne', 's0', 'at', 'r_full'), ('nop',),
        ('jal', names.GIVEN), ('nop',), ('b', 'r_out'), ('addiu', 'v1', 'zero', 4),
        'r_full:',
        ('jal', names.FULL), ('nop',), ('addiu', 'v1', 'zero', 4),
        'r_out:',
        ('lw', 'ra', 0x14, 'sp'), ('lw', 's0', 0x10, 'sp'), ('jr', 'ra'), ('addiu', 'sp', 'sp', 0x18),

        # ---- measure(a0 = rest of an insert string or 0, a1 = source after it; s2 = obj) -> v0 = px up to
        #      the next space / page code
        'measure:',
        ('addiu', 'sp', 'sp', -0x38), ('sw', 'ra', 0x34, 'sp'), ('sw', 's0', 0x30, 'sp'), ('sw', 's1', 0x2c, 'sp'),
        ('sw', 's3', 0x28, 'sp'), ('lui', 't3', hi(tables.BUFS)), ('addiu', 't3', 't3', lo(tables.BUFS)),
    ] + [x for i, (o, base) in enumerate(rot) for x in (('lw', 't0', o, base), ('nop',), ('sw', 't0', 0x10 + 4 * i, 'sp'))] + [
        ('addu', 's0', 'a0', 'zero'), ('addu', 's1', 'a1', 'zero'),
        ('beqz', 's0', 'm_src'), ('addu', 's3', 'zero', 'zero'),
        'm_str:',
        ('lbu', 'a0', 0, 's0'), ('addiu', 'at', 'zero', 0x20),
        ('beqz', 'a0', 'm_src'), ('nop',),
        ('beq', 'a0', 'at', 'm_done'), ('nop',),
        ('jal', 'chw'), ('addiu', 's0', 's0', 1),
        ('addu', 's0', 's0', 'v1'), ('b', 'm_str'), ('addu', 's3', 's3', 'v0'),
        'm_src:',
        ('lbu', 'a0', 0, 's1'), ('nop',),
        ('addiu', 'v0', 'a0', -0x61), ('sltiu', 'at', 'v0', 26), ('beqz', 'at', 'm_lit'), ('sltiu', 'at', 'a0', 0x21),
        ('addiu', 'at', 'zero', ord('a')), ('beq', 'a0', 'at', 'm_ins'), ('addiu', 'at', 'zero', ord('e')),
        ('beq', 'a0', 'at', 'm_ins'), ('addiu', 'at', 'zero', ord('p')),
        ('beq', 'a0', 'at', 'm_ins'), ('addiu', 'at', 'zero', ord('b')),
        ('beq', 'a0', 'at', 'm_ins'), ('addiu', 'at', 'zero', ord('w')),
        ('beq', 'a0', 'at', 'm_src'), ('addiu', 's1', 's1', 1),              # pause: no width
        ('addiu', 'at', 'zero', ord('c')), ('beq', 'a0', 'at', 'm_src'), ('addiu', 's1', 's1', 1),
        ('addiu', 'at', 'zero', ord('d')), ('beq', 'a0', 'at', 'm_src'), ('nop',),
        ('b', 'm_done'), ('nop',),
        'm_ins:',
        ('jal', 'resolve'), ('addu', 'a0', 's1', 'zero'),
        ('addu', 's1', 's1', 'v1'), ('b', 'm_str'), ('addu', 's0', 'v0', 'zero'),
        'm_lit:',
        ('addiu', 't0', 'zero', PLURAL), ('bne', 'a0', 't0', 'm_l2'), ('nop',),
        ('b', 'm_src'), ('addiu', 's1', 's1', 1),    # the mark has no width (its letter is counted)
        'm_l2:',
        ('bnez', 'at', 'm_done'), ('nop',),
        ('jal', 'chw'), ('addiu', 's1', 's1', 1),
        ('addu', 's1', 's1', 'v1'), ('b', 'm_src'), ('addu', 's3', 's3', 'v0'),
        'm_done:',
        ('lui', 't3', hi(tables.BUFS)), ('addiu', 't3', 't3', lo(tables.BUFS)),
    ] + [x for i, (o, base) in enumerate(rot) for x in (('lw', 't0', 0x10 + 4 * i, 'sp'), ('nop',), ('sw', 't0', o, base))] + [
        ('addu', 'v0', 's3', 'zero'),
        ('lw', 'ra', 0x34, 'sp'), ('lw', 's0', 0x30, 'sp'), ('lw', 's1', 0x2c, 'sp'), ('lw', 's3', 0x28, 'sp'),
        ('jr', 'ra'), ('addiu', 'sp', 'sp', 0x38),
    ]


def patch(exe, w):
    """exe: bytearray of SLPM_862.68 (after vwf / msgpack); w = advance table address (vwf.font_file).
    -> bytes free behind the new interpreter."""
    width = asm.labels(vwf.DRAW, vwf.draw_code(w))['width']
    c = asm.assemble(INTERP, code(width))
    room = INTERP_END - INTERP
    assert len(c) <= room, 'interpreter: %d bytes over' % (len(c) - room)
    o = INTERP - vwf.EXE_BASE + vwf.EXE_OFF
    exe[o:o + room] = c.ljust(room, b'\0')
    return room - len(c)


def verify(exe, w):
    """nothing else (progstr repoints, layout) may have written into the new interpreter"""
    c = asm.assemble(INTERP, code(asm.labels(vwf.DRAW, vwf.draw_code(w))['width']))
    o = INTERP - vwf.EXE_BASE + vwf.EXE_OFF
    assert bytes(exe[o:o + len(c)]) == c, 'the interpreter was patched by another tool'

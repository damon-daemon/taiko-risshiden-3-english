"""Player names: 6-bit packed English inside the game's own (saved) name fields.

The player record (gp-0x64cc, 0x60 bytes, saved whole) has no free bytes, so the four name
fields keep their place and size and hold packed text instead of Shift-JIS:
  +0x15 given[7]  +0x1c family[9]   (player 1: Hideyoshi)
  +0x25 given2[7] +0x2c family2[9]  (player 2: Hidenaga)
6 bits per letter, most significant bit first, code 0 = end: given = 9 letters, family = 12.
ALPHABET gives the codes (A-Z a-z, the macron vowels, space ' - .).

The game reads and writes the fields only through ten accessors at 0x80060bc4-0x80060eb3.
`patch()` replaces that block with: getters that unpack into static buffers (BUF: tail of the
FONT.DAT buffer, after names.py's), setters that pack an English string (unknown bytes are
dropped), the full name as "Family Given", the code table and the English name strings
(tl/names_player.json, keyed by the address of the Japanese string). Every `jal` to an old
entry point is retargeted (EXE and overlays; `patch_overlay`). Also patched:
  - save-slot summary (0x800888ac): copies the 16 packed bytes instead of two strncpy;
    the load / save menu line (0x8008805c; System Memory 0x80089de4) unpacks them ("%s%s" with an empty second part);
  - `addiu rX, gp, string` + jal + nop sites of the default names -> lui / jal / addiu (the
    English strings are longer than the 8-byte slots of the Japanese ones);
  - the rename pointer tables at 0x800b3a84-0x800b3ab3.
The name entry screens (0x80078548 / 0x8007857c) are tools/nameentry.py.
"""
import json, os, struct, sys

sys.path.insert(0, os.path.dirname(__file__))
import asm, names, text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = os.path.join(ROOT, 'tl', 'names_player.json')
EXE_BASE, EXE_OFF = 0x80010000, 0x800
OVL_BASE, OVL_OFF = 0x800EE000, 0       # the whole file (MWo1 header included) loads at OVL_BASE
BLOCK, BLOCK_END = 0x80060bc4, 0x80060eb4
G_REC = -0x64cc
GIVEN_N, FAMILY_N = 9, 12
ALPHABET = ('\0ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' + 'ōūŌŪ' + " '-.").ljust(64, '\0')
# old entry point -> label
OLD = {0x80060bc4: 'fam1', 0x80060c00: 'setfam1', 0x80060c4c: 'giv1', 0x80060c80: 'setgiv1', 0x80060ccc: 'full1',
       0x80060d3c: 'fam2', 0x80060d78: 'setfam2', 0x80060dc4: 'giv2', 0x80060df8: 'setgiv2', 0x80060e44: 'full2'}
BUF = names.BUF + 5 * sum(names.SLOT) + 2            # 0x8016EF10
BUFS = {k: BUF + o for k, o in (('fam1', 0), ('giv1', 16), ('full1', 32), ('fam2', 56), ('giv2', 72),
                                ('full2', 88), ('sum', 112))}
BUF_END = BUF + 136
MEMCPY, PRINTF = 0x8008f4dc, 0x8007b5c8
SUMMARY, SUMMARY_END = 0x800888ac, 0x80088918        # slot summary: two getter + strncpy pairs
SUM_TABLE = 0x800e642c
MENU, MENU_END = 0x8008805c, 0x8008807c              # printf("%s%s", family, given) of a slot
MENU_FMT = -0x74e0
MENU_RAM, MENU_RAM_END = 0x80089de4, 0x80089df8      # the same for the System Memory slot
# `addiu reg, gp, imm` sites (image, address) -> key of the string in tl/names_player.json
GP_SITES = {
    ('exe', 0x8007503c): 'empty', ('exe', 0x80075048): '0x800cf924', ('exe', 0x80075054): 'empty',
    ('exe', 0x80075060): '0x800cf92c', ('exe', 0x80075080): '0x800cf914', ('exe', 0x8007508c): '0x800cf91c',
    ('exe', 0x80076274): '0x800cf914', ('exe', 0x80076284): '0x800cf91c',
    ('MAPPOINT.BIN', 0x80125698): '0x800d04d0', ('MAPPOINT.BIN', 0x801256a4): '0x800d04d8',
    ('MAPPOINT.BIN', 0x801256b0): '0x800d04d0', ('MAPPOINT.BIN', 0x801256bc): '0x800d04e0',
    # Ganmaku's rename (0x80125590): strcmp(default given name, hero's) picks the "Hideyoshi" branch (5 @128)
    ('MAPPOINT.BIN', 0x801255b8): '0x800d04c8',
}
TABLES = (0x800b3a84, 0x800b3ab4)                    # rename tables: 12 pointers


def strings():
    return json.load(open(TL))


def pack(s, n):
    """English name -> the packed field (n letters: 9 -> 7 bytes, 12 -> 9 bytes)."""
    if len(s) > n:
        raise ValueError('player name %r: more than %d letters' % (s, n))
    bits = 0
    for ch in s.ljust(n, '\0'):
        c = ALPHABET.index(ch)
        if ch != '\0' and not c:
            raise ValueError('player name %r: %r not in the alphabet' % (s, ch))
        bits = bits << 6 | c
    size = (n * 6 + 7) // 8
    return (bits << (size * 8 - n * 6)).to_bytes(size, 'big')


def unpack(b, n):
    bits = int.from_bytes(b, 'big') >> (len(b) * 8 - n * 6)
    s = ''.join(ALPHABET[bits >> (6 * (n - 1 - i)) & 63] for i in range(n))
    return s.split('\0')[0]


def listing():
    hi, lo = asm.hi, asm.lo
    L = []

    def getter(name, off, n):
        return [name + ':', ('lw', 'v0', G_REC, 'gp'), ('lui', 'a0', hi(BUFS[name])),
                ('addiu', 'a0', 'a0', lo(BUFS[name])), ('addiu', 'a2', 'zero', n), ('j', 'unpack'),
                ('addiu', 'a1', 'v0', off)]

    def setter(name, off, n):
        return [name + ':', ('lw', 'v0', G_REC, 'gp'), ('addu', 'a1', 'a0', 'zero'), ('addiu', 'a2', 'zero', n),
                ('j', 'pack'), ('addiu', 'a0', 'v0', off)]

    def full(name, off):
        return [name + ':', ('lw', 'a0', G_REC, 'gp'), ('lui', 'a1', hi(BUFS[name])),
                ('addiu', 'a1', 'a1', lo(BUFS[name])), ('j', 'fullname'), ('addiu', 'a0', 'a0', off)]

    for p, o in (('1', 0x15), ('2', 0x25)):
        L += getter('fam' + p, o + 7, FAMILY_N) + setter('setfam' + p, o + 7, FAMILY_N)
        L += getter('giv' + p, o, GIVEN_N) + setter('setgiv' + p, o, GIVEN_N) + full('full' + p, o)
    L += [
        'fullsum:',                            # a0 = packed given[7] family[9] -> v0 = a1 = "Family Given", v1 = its end
        ('lui', 'a1', hi(BUFS['sum'])), ('addiu', 'a1', 'a1', lo(BUFS['sum'])),
        'fullname:',                           # a0 = packed pair, a1 = buffer
        ('addiu', 'sp', 'sp', -0x10), ('sw', 'ra', 0xc, 'sp'), ('sw', 's0', 8, 'sp'), ('sw', 's1', 4, 'sp'),
        ('addu', 's0', 'a0', 'zero'), ('addu', 's1', 'a1', 'zero'), ('addu', 'a0', 'a1', 'zero'),
        ('addiu', 'a1', 's0', 7), ('jal', 'unpack'), ('addiu', 'a2', 'zero', FAMILY_N),
        ('beq', 'v1', 's1', 'n1'), ('addu', 'a0', 'v1', 'zero'),      # no family: no space
        ('addiu', 't0', 'zero', 0x20), ('sb', 't0', 0, 'a0'), ('addiu', 'a0', 'a0', 1),
        'n1:',
        ('addu', 'a1', 's0', 'zero'), ('jal', 'unpack'), ('addiu', 'a2', 'zero', GIVEN_N),
        ('addu', 'v0', 's1', 'zero'), ('addu', 'a1', 's1', 'zero'),
        ('lw', 'ra', 0xc, 'sp'), ('lw', 's0', 8, 'sp'), ('lw', 's1', 4, 'sp'), ('jr', 'ra'),
        ('addiu', 'sp', 'sp', 0x10),
        'unpack:',                             # a0 = buffer, a1 = field, a2 = letters -> v0 = buffer, v1 = its NUL (leaf)
        ('addu', 'v0', 'a0', 'zero'), ('addu', 't0', 'zero', 'zero'), ('addu', 't1', 'zero', 'zero'),
        'u1:',
        ('sltiu', 'at', 't1', 6), ('beqz', 'at', 'u2'), ('lbu', 't2', 0, 'a1'),
        ('sll', 't0', 't0', 8), ('or', 't0', 't0', 't2'), ('addiu', 'a1', 'a1', 1), ('addiu', 't1', 't1', 8),
        'u2:',
        ('addiu', 't1', 't1', -6), ('srlv', 't2', 't0', 't1'), ('andi', 't2', 't2', 63), ('beqz', 't2', 'u3'),
        ('lui', 't3', 0),                      # hi(table): filled in below
        ('addu', 't3', 't3', 't2'), ('lbu', 't3', 0, 't3'), ('addiu', 'a2', 'a2', -1), ('sb', 't3', 0, 'a0'),
        ('bnez', 'a2', 'u1'), ('addiu', 'a0', 'a0', 1),
        'u3:',
        ('sb', 'zero', 0, 'a0'), ('jr', 'ra'), ('addu', 'v1', 'a0', 'zero'),
        'pack:',                               # a0 = field, a1 = string, a2 = letters -> v0 = letters stored (leaf)
        ('addu', 't0', 'zero', 'zero'), ('addu', 't1', 'zero', 'zero'), ('addu', 'v0', 'zero', 'zero'),
        'p1:',
        ('lbu', 't2', 0, 'a1'), ('addu', 't4', 'zero', 'zero'), ('beqz', 't2', 'p4'),
        ('lui', 't3', 0),                      # hi(table)
        ('addiu', 'a1', 'a1', 1), ('addiu', 't4', 'zero', 63),
        'p2:',
        ('addu', 't5', 't3', 't4'), ('lbu', 't5', 0, 't5'), ('nop',), ('beq', 't5', 't2', 'p3'), ('nop',),
        ('addiu', 't4', 't4', -1), ('bnez', 't4', 'p2'), ('nop',),
        ('b', 'p1'), ('nop',),                 # no code for this byte: dropped
        'p3:',
        ('addiu', 'v0', 'v0', 1),
        'p4:',
        ('sll', 't0', 't0', 6), ('or', 't0', 't0', 't4'), ('addiu', 't1', 't1', 6),
        ('sltiu', 'at', 't1', 8), ('bnez', 'at', 'p5'), ('addiu', 't5', 't1', -8),
        ('srlv', 't6', 't0', 't5'), ('sb', 't6', 0, 'a0'), ('addiu', 'a0', 'a0', 1), ('addu', 't1', 't5', 'zero'),
        'p5:',
        ('addiu', 'a2', 'a2', -1), ('bnez', 'a2', 'p1'), ('nop',),
        ('beqz', 't1', 'p6'), ('addiu', 't5', 'zero', 8),
        ('subu', 't5', 't5', 't1'), ('sllv', 't0', 't0', 't5'), ('sb', 't0', 0, 'a0'),
        'p6:',
        ('jr', 'ra'), ('nop',),
        'table:',
    ]
    table = asm.labels(BLOCK, L)['table']
    for i, ln in enumerate(L):
        if ln == ('lui', 't3', 0):
            L[i] = ('lui', 't3', hi(table))
        elif ln in (('lbu', 't3', 0, 't3'), ('lbu', 't5', 0, 't5')):
            L[i] = ln[:2] + (lo(table),) + ln[3:]
    return L


def build():
    """-> (block bytes, {label: address}, {string key: address})"""
    L = listing()
    lab = asm.labels(BLOCK, L)
    out = bytearray(asm.assemble(BLOCK, L))
    out += bytes([0]) + text.enc(ALPHABET[1:].rstrip('\0')).ljust(63, b'\0')
    where, seen = {}, {}
    for key, s in strings().items():
        if s not in seen:
            seen[s] = BLOCK + len(out)
            out += text.enc(s) + b'\0'
        where[key] = seen[s]
    where['empty'] = BLOCK + len(out) - 1
    if len(out) > BLOCK_END - BLOCK:
        raise ValueError('player block: %d bytes over' % (len(out) - (BLOCK_END - BLOCK)))
    return bytes(out).ljust(BLOCK_END - BLOCK, b'\0'), lab, where


def _retarget(data, lab):
    n = 0
    jal = {0x0C000000 | (old >> 2) & 0x3FFFFFF: 0x0C000000 | (lab[name] >> 2) & 0x3FFFFFF for old, name in OLD.items()}
    for i in range(0, len(data) - 3, 4):
        w = struct.unpack_from('<I', data, i)[0]
        if w in jal:
            struct.pack_into('<I', data, i, jal[w])
            n += 1
    for old in OLD:
        assert struct.pack('<I', old) not in data, 'pointer to accessor %08x' % old
    return n


def _gp_sites(data, image, base, off, where):
    for (img, addr), key in GP_SITES.items():
        if img != image:
            continue
        o = addr - base + off
        w, j, nop = struct.unpack_from('<3I', data, o)
        if j >> 26 != 3:                       # addiu; one other instruction; jal; nop -> lui; addiu; jal; other
            x, j, nop = struct.unpack_from('<3I', data, o + 4)
            assert x == 0x00402821 and j >> 26 == 3 and nop == 0, 'gp site %08x' % addr     # move a1, v0
            reg = [k for k, v in asm.R.items() if v == (w >> 16) & 31][0]
            code = asm.assemble(addr, [('lui', reg, asm.hi(where[key])), ('addiu', reg, reg, asm.lo(where[key]))])
            data[o:o + 16] = code + struct.pack('<2I', j, x)
            continue
        assert w >> 26 == 9 and (w >> 21) & 31 == 28 and j >> 26 == 3 and nop == 0, 'gp site %08x' % addr
        reg = [k for k, v in asm.R.items() if v == (w >> 16) & 31][0]
        code = asm.assemble(addr, [('lui', reg, asm.hi(where[key])), ('nop',), ('addiu', reg, reg, asm.lo(where[key]))])
        data[o:o + 4] = code[:4]
        data[o + 4:o + 8] = struct.pack('<I', j)
        data[o + 8:o + 12] = code[8:]


def patch(exe):
    """exe: bytearray of SLPM_862.68 (after names.patch). -> bytes free in the block"""
    block, lab, where = build()
    assert names.BUF + 5 * sum(names.SLOT) <= BUF and BUF_END <= 0x8016F000
    o = BLOCK - EXE_BASE + EXE_OFF
    exe[o:o + len(block)] = bytes(len(block))
    n = _retarget(exe, lab)
    assert n == 20, 'accessor calls in the EXE: %d' % n
    exe[o:o + len(block)] = block
    _gp_sites(exe, 'exe', EXE_BASE, EXE_OFF, where)
    # rename tables
    for a in range(*TABLES, 4):
        p = a - EXE_BASE + EXE_OFF
        struct.pack_into('<I', exe, p, where['0x%08x' % struct.unpack_from('<I', exe, p)[0]])
    # slot summary: s1 = slot * 0x16, 0x24(sp) = &summary, 16 packed bytes copied
    L = [
        ('lw', 'a0', 0x2c, 'sp'), ('nop',), ('sll', 'v1', 'a0', 2), ('addu', 'v1', 'v1', 'a0'), ('sll', 'v1', 'v1', 1),
        ('addu', 'v1', 'v1', 'a0'), ('sll', 's1', 'v1', 1), ('lui', 'v1', asm.hi(SUM_TABLE)),
        ('addiu', 'v1', 'v1', asm.lo(SUM_TABLE)), ('addu', 'a0', 'v1', 's1'), ('sw', 'a0', 0x24, 'sp'),
        ('lw', 'a1', G_REC, 'gp'), ('addiu', 'a2', 'zero', 16), ('jal', MEMCPY), ('addiu', 'a1', 'a1', 0x15),
    ]
    _put(exe, SUMMARY, SUMMARY_END, L)
    L = [
        ('lui', 'v0', asm.hi(SUM_TABLE)), ('addiu', 'v0', 'v0', asm.lo(SUM_TABLE)), ('addu', 's2', 'v0', 's0'),
        ('jal', lab['fullsum']), ('addu', 'a0', 's2', 'zero'),
        ('addiu', 'a0', 'gp', MENU_FMT), ('jal', PRINTF), ('addu', 'a2', 'v1', 'zero'),
    ]
    _put(exe, MENU, MENU_END, L)
    # the same line for the System Memory slot (summary at s0 = 0x801a4200)
    L = [
        ('jal', lab['fullsum']), ('addu', 'a0', 's0', 'zero'),
        ('addiu', 'a0', 'gp', MENU_FMT), ('jal', PRINTF), ('addu', 'a2', 'v1', 'zero'),
    ]
    _put(exe, MENU_RAM, MENU_RAM_END, L)
    return BLOCK_END - BLOCK - len(block.rstrip(b'\0')) - 1


def _put(exe, addr, end, L):
    c = asm.assemble(addr, L)
    assert len(c) <= end - addr, '%08x: %d bytes over' % (addr, len(c) - (end - addr))
    o = addr - EXE_BASE + EXE_OFF
    exe[o:o + end - addr] = c.ljust(end - addr, b'\0')


def patch_overlay(name, data):
    """An overlay (BATTLE.BIN / MAPPOINT.BIN) -> the same with its accessor calls and strings
    repointed, or None when nothing changes."""
    _, lab, where = build()
    new = bytearray(data)
    _retarget(new, lab)
    _gp_sites(new, name, OVL_BASE, OVL_OFF, where)
    return bytes(new) if new != data else None


if __name__ == '__main__':
    block, lab, where = build()
    print('block: %d of %d bytes' % (len(block.rstrip(b'\0')) + 1, BLOCK_END - BLOCK))
    for k, v in strings().items():
        print(k, v, '%08x' % where[k])
    for s, n in (('Kinoshita', 12), ('Tōkichirō', 9), ("Emperor Go-Y", 12), ('', 9)):
        assert unpack(pack(s, n), n) == s
        print(repr(s), pack(s, n).hex())

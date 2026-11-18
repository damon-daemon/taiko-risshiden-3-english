"""Small string buffers that English overflows: the clan-name getter and four message functions.

- Clan getter 0x8005cab4(clan) -> "<family>家": strncpy of 8 bytes of the leader's family name
  into three rotating 11-byte buffers at 0x800d9754, then strcat 家 (滅亡 when the clan is gone).
  Rewritten in place: three 20-byte buffers at BUF (the person-name buffers that names.py left
  unused, 0x800d97b8-0x800d984d), whole family name + tl/tables/clans.txt `suffix`.
  Second entry SHORT = the same without the suffix, for list columns under a "Clan" header
  (SHORT_CALLS: the `jal` sites retargeted to it).
- sprintf of `%s家` / `%sの国` / `%s地方` into a 12-byte stack buffer that then becomes a message
  variable (0x8007cc20 keeps the pointer): STACK = {function: (stack offset, [addiu sites])}. Each
  `addiu rX, sp, off` becomes `addiu rX, gp, <static buffer>` (20 bytes each, after the clan
  buffers; the two province / region pairs share one). tools/dev/fmtscan.py lists such buffers.

- BATTLE.BIN name buffers (`patch_battle`): army-name getter 0x80136608 ("%s Army", 5 rotating 11-byte
  buffers at 0x8014ce34) and unit-name helper 0x80139a9c ("%s's unit" / full name, 5 x 21 bytes at
  0x8014ce6c): the index arithmetic is rewritten for 20 / 28-byte slots at BATTLE_BUF (FONT.DAT buffer
  tail, below msgpack.SCRATCH; build.py checks the font ends before it).

tl/tables/clans.txt: `suffix` (" clan"), `fallen` (滅亡). The program strings 0x800cf840 /
0x800cf844 are `-` in tl/progstr (this module owns them).
"""
import os, struct, sys

sys.path.insert(0, os.path.dirname(__file__))
import asm, rectab, text

EXE_BASE, EXE_OFF = 0x80010000, 0x800
GP = 0x800d6f54
CLAN, CLAN_END = 0x8005cab4, 0x8005cbdc
SHORT = CLAN + 8
G_COUNT = -0x657c                         # rotation counter (gp-relative)
BUF, BUF_END = 0x800d97b8, 0x800d984d     # free since names.py moved the person-name buffers
SLOT, NSLOT = 20, 3
VALID, LEADER, IS_PERSON, FAMILY = 0x8005c448, 0x8005c464, 0x800523bc, 0x8005df44
STRCPY, STRCAT = 0x800868b4, 0x80086a3c
# list columns under a "Clan" header: People list, castle list
SHORT_CALLS = [0x80031da4, 0x80030de0, 0x80043180]
STACK = [       # (stack offset, [sites of `addiu rX, sp, offset`], longest English it must hold)
    (0x1c, [0x80013368, 0x80013388, 0x80013424, 0x80013444]),      # "%s clan"
    (0x24, [0x8001f738, 0x8001f758]),                              # "%s Province" (0x8001f5e8)
    (0x24, [0x8001f99c, 0x8001f9bc]),                              # "%s Region"   (0x8001f848)
    (0x30, [0x8006ef7c, 0x8006ef9c]),                              # "%s Province" (0x8006ee44)
    (0x38, [0x8006f18c, 0x8006f1ac]),                              # "%s Region"   (0x8006f048)
]
STACK_BUF = [0, 1, 1, 2, 2]               # which static buffer each entry uses
STATIC = BUF + SLOT * NSLOT


OVL_BASE = 0x800EE000
BATTLE_BUF = 0x8016EC00                   # 5 x 20 (army) + 5 x 28 (unit) = 0xF0 bytes
BATTLE = [      # (first instruction of the index arithmetic, old words to check, slot multiply, buffer)
    (0x80136658, (0x00031080, 0x00431020, 0x00021040, 0x00431820, 0x3c028015, 0x2442ce34, 0x00438021),
     [('sll', 'v0', 'v1', 2), ('addu', 'v0', 'v0', 'v1'), ('sll', 'v1', 'v0', 2)], BATTLE_BUF),              # x 20
    (0x80139af4, (0x000310c0, 0x00431822, 0x00031080, 0x00431822, 0x3c028015, 0x2442ce6c, 0x00438021),
     [('sll', 'v0', 'v1', 3), ('subu', 'v0', 'v0', 'v1'), ('sll', 'v1', 'v0', 2)], BATTLE_BUF + 100),       # x 28
]


def patch_battle(img):
    """img: bytearray of BATTLE.BIN (whole file, loaded at OVL_BASE)."""
    for va, old, mul, buf in BATTLE:
        o = va - OVL_BASE
        assert struct.unpack_from('<7I', img, o) == old, '%08x: not the buffer index code' % va
        c = asm.assemble(va, mul + [('lui', 'v0', asm.hi(buf)), ('addiu', 'v0', 'v0', asm.lo(buf)), ('nop',),
                                    ('addu', 's0', 'v0', 'v1')])
        assert len(c) == 28
        img[o:o + 28] = c
    return img


def code():
    tl = rectab.load('clans')
    L = [
        ('b', 'body'), ('addiu', 't3', 'zero', 1),
        ('addu', 't3', 'zero', 'zero'),                            # SHORT
        'body:',
        ('addiu', 'sp', 'sp', -0x20), ('sw', 'ra', 0x1c, 'sp'), ('sw', 's2', 0x18, 'sp'),
        ('sw', 's1', 0x14, 'sp'), ('sw', 's0', 0x10, 'sp'),
        ('addu', 's1', 't3', 'zero'), ('addu', 's2', 'a0', 'zero'),
        ('lw', 'v1', G_COUNT, 'gp'), ('nop',),
        ('sltiu', 'at', 'v1', NSLOT), ('bnez', 'at', 'c1'), ('nop',),
        ('addu', 'v1', 'zero', 'zero'),
        'c1:',
        ('addiu', 't0', 'v1', 1), ('sltiu', 'at', 't0', NSLOT), ('bnez', 'at', 'c2'),
        ('sll', 'v0', 'v1', 2),
        ('addu', 't0', 'zero', 'zero'),
        'c2:',
        ('sw', 't0', G_COUNT, 'gp'), ('addu', 'v0', 'v0', 'v1'), ('sll', 'v0', 'v0', 2),   # x 20
        ('addiu', 's0', 'gp', BUF - GP), ('addu', 's0', 's0', 'v0'),
        ('jal', VALID), ('addu', 'a0', 's2', 'zero'),
        ('beqz', 'v0', 'fallen'), ('nop',),
        ('jal', LEADER), ('addu', 'a0', 's2', 'zero'),
        ('addu', 's2', 'v0', 'zero'),
        ('jal', IS_PERSON), ('addu', 'a0', 's2', 'zero'),
        ('beqz', 'v0', 'fallen'), ('nop',),
        ('jal', FAMILY), ('addu', 'a0', 's2', 'zero'),
        ('addu', 'a0', 's0', 'zero'),
        ('jal', STRCPY), ('addu', 'a1', 'v0', 'zero'),
        ('beqz', 's1', 'out'), ('addu', 'a0', 's0', 'zero'),
        ('lui', 'a1', 0), ('jal', STRCAT), ('addiu', 'a1', 'a1', 0),          # suffix (fixed up below)
        ('b', 'out'), ('nop',),
        'fallen:',
        ('lui', 'a1', 0), ('addu', 'a0', 's0', 'zero'), ('jal', STRCPY), ('addiu', 'a1', 'a1', 0),
        'out:',
        ('addu', 'v0', 's0', 'zero'), ('lw', 'ra', 0x1c, 'sp'), ('lw', 's2', 0x18, 'sp'),
        ('lw', 's1', 0x14, 'sp'), ('lw', 's0', 0x10, 'sp'), ('jr', 'ra'), ('addiu', 'sp', 'sp', 0x20),
    ]
    assert SLOT == 20 and SLOT * NSLOT + 20 * (max(STACK_BUF) + 1) <= BUF_END - BUF
    n = sum(1 for l in L if isinstance(l, tuple)) * 4
    suffix, fallen = text.enc(tl['suffix']) + b'\0', text.enc(tl['fallen']) + b'\0'
    at = {'suffix': CLAN + n, 'fallen': CLAN + n + len(suffix)}
    if 12 + len(suffix) > SLOT or len(fallen) > SLOT:           # a player family name has 12 letters at most
        raise ValueError('clans.txt: suffix / fallen too long for the %d-byte buffers' % SLOT)
    for key, i in (('suffix', L.index(('lui', 'a1', 0))), ('fallen', len(L) - 1 - L[::-1].index(('lui', 'a1', 0)))):
        j = next(k for k in range(i, len(L)) if L[k] == ('addiu', 'a1', 'a1', 0))
        L[i], L[j] = ('lui', 'a1', asm.hi(at[key])), ('addiu', 'a1', 'a1', asm.lo(at[key]))
    return asm.assemble(CLAN, L) + suffix + fallen


def patch(exe):
    """exe: bytearray of SLPM_862.68. Returns the bytes left in the getter's block."""
    c = code()
    room = CLAN_END - CLAN
    assert len(c) <= room, 'clan getter: %d bytes over' % (len(c) - room)
    o = CLAN - EXE_BASE + EXE_OFF
    exe[o:o + room] = c.ljust(room, b'\0')
    for va in SHORT_CALLS:
        o = va - EXE_BASE + EXE_OFF
        assert struct.unpack_from('<I', exe, o)[0] == 0x0C000000 | CLAN >> 2 & 0x3FFFFFF, '%08x: not a call of the clan getter' % va
        struct.pack_into('<I', exe, o, 0x0C000000 | SHORT >> 2 & 0x3FFFFFF)
    for (off, sites), b in zip(STACK, STACK_BUF):
        for va in sites:
            o = va - EXE_BASE + EXE_OFF
            w = struct.unpack_from('<I', exe, o)[0]
            assert w >> 21 == 0x09 << 5 | 29 and w & 0xFFFF == off, '%08x: not addiu rX, sp, %#x' % (va, off)
            struct.pack_into('<I', exe, o, 0x09 << 26 | 28 << 21 | (w >> 16 & 31) << 16 | (STATIC + 20 * b - GP) & 0xFFFF)
    return room - len(c)


if __name__ == '__main__':
    print(__doc__)

"""Small name tables that sit in the program as fixed-size records (no pointers, so progstr.py
cannot move them): tl/tables/buildings.txt and tl/tables/columns.txt -> the game.

- Building names (town menu: 城 米屋 馬屋 ... 御所): 18 records of 9 bytes at 0x800b6714, dummy
  バグ at 0x800b3690. Getter 0x80060b24(type) (one caller, 0x8004f91c) copied 8 bytes into
  rotating buffers; it is rewritten in place to return a pointer to a packed English string
  (NUL-separated; ids below the split in the old record table, the rest + "Bug" after the new code,
  inside the old function's 160 bytes).
- Column heads of MAPPOINT's people tables: 12 skills (3-byte records at 0x80150b54: one kanji,
  16-px columns) and 4 abilities (5-byte records at 0x80150b78, 32-px columns). English goes in
  place: 2 and 4 letters at most.
- The speaker names of generic people (11-byte records at 0x800b7e5c) belong to names.py
  (tl/names_generic.json).

tl files: key<TAB>English; buildings: record number or `bug`; columns: `skill0`-`skill11`,
`ability0`-`ability3`.

usage: rectab.py check | dump
"""
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
import asm, text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = os.path.join(ROOT, 'tl', 'tables')
EXE_BASE, EXE_OFF = 0x80010000, 0x800
OVL_BASE = 0x800EE000

BUILDINGS, BUILDING_N, BUILDING_REC = 0x800b6714, 18, 9
BUILDING_GET, BUILDING_END = 0x80060b24, 0x80060bc4
COLUMNS = {'skill': (0x80150b54, 12, 3), 'ability': (0x80150b78, 4, 5)}      # MAPPOINT.BIN
# program ranges progstr.py must not scan (records owned here and by names.py)
RECORDS = [(BUILDINGS, BUILDINGS + BUILDING_N * BUILDING_REC), (0x800b7e5c, 0x800b7e5c + 26 * 11)]


def load(name):
    out = {}
    for n, line in enumerate(open(os.path.join(TL, name + '.txt'), encoding='utf-8').read().splitlines(), 1):
        if line.strip() and not line.startswith('#'):
            k, tab, v = line.partition('\t')
            if not tab or k in out:
                raise ValueError('%s.txt line %d: expected a new key<TAB>English' % (name, n))
            out[k] = v
    return out


def buildings():
    tl = load('buildings')
    keys = [str(i) for i in range(BUILDING_N)] + ['bug']
    if sorted(tl) != sorted(keys):
        raise ValueError('buildings.txt: keys must be 0-%d and bug' % (BUILDING_N - 1))
    return [text.enc(tl[k]) + b'\0' for k in keys]


def building_code(split, tail):
    """The getter: a0 = type -> v0 = its string (only v0, v1, a0, at used)."""
    L = [
        ('sltiu', 'at', 'a0', BUILDING_N), ('bnez', 'at', 'inr'), ('nop',),
        ('addiu', 'a0', 'zero', BUILDING_N),               # out of range: the dummy
        'inr:',
        ('sltiu', 'at', 'a0', split), ('lui', 'v0', asm.hi(BUILDINGS)),
        ('bnez', 'at', 'walk'), ('addiu', 'v0', 'v0', asm.lo(BUILDINGS)),
        ('lui', 'v0', asm.hi(tail)), ('addiu', 'v0', 'v0', asm.lo(tail)), ('addiu', 'a0', 'a0', -split),
        'walk:',
        ('beqz', 'a0', 'done'), ('nop',),
        'skip:',
        ('lbu', 'v1', 0, 'v0'), ('addiu', 'v0', 'v0', 1), ('bnez', 'v1', 'skip'), ('nop',),
        ('b', 'walk'), ('addiu', 'a0', 'a0', -1),
        'done:',
        ('jr', 'ra'), ('nop',),
    ]
    return asm.assemble(BUILDING_GET, L)


def patch(exe):
    """exe: bytearray of SLPM_862.68. Returns the free bytes left (both string areas)."""
    names = buildings()
    room = BUILDING_N * BUILDING_REC
    split, used = 0, 0
    while split < len(names) and used + len(names[split]) <= room:
        used += len(names[split])
        split += 1
    split = min(split, BUILDING_N)                         # the dummy lives in the tail
    head, rest = b''.join(names[:split]), b''.join(names[split:])
    n = len(building_code(split, 0))
    tail = BUILDING_GET + n
    code = building_code(split, tail)
    left = BUILDING_END - tail - len(rest)
    if left < 0:
        raise ValueError('building names: %d bytes too long' % -left)
    o = BUILDING_GET - EXE_BASE + EXE_OFF
    exe[o:o + BUILDING_END - BUILDING_GET] = (code + rest).ljust(BUILDING_END - BUILDING_GET, b'\0')
    o = BUILDINGS - EXE_BASE + EXE_OFF
    exe[o:o + room] = head.ljust(room, b'\0')
    return left + room - len(head)


def patch_overlay(name, data):
    """MAPPOINT.BIN -> the same with the English column heads (bytearray in, changed in place)."""
    if name != 'MAPPOINT.BIN':
        return data
    tl = load('columns')
    for kind, (va, n, rec) in COLUMNS.items():
        for i in range(n):
            b = text.enc(tl['%s%d' % (kind, i)])
            if len(b) >= rec:
                raise ValueError('columns.txt %s%d: %d letters at most' % (kind, i, rec - 1))
            o = va - OVL_BASE + i * rec
            assert data[o + rec - 1] == 0
            data[o:o + rec] = b.ljust(rec, b'\0')
    return data


def check():
    import setup, iso
    disc = iso.Disc(setup.CLEAN)
    print('buildings: %d bytes free' % patch(bytearray(disc.file(iso.EXE_NAME))))
    patch_overlay('MAPPOINT.BIN', bytearray(disc.file('MAPPOINT.BIN')))
    tl = load('columns')
    for k, v in tl.items():
        print('  %-9s %-5s %2d px (column %d)' % (k, v, text.width(v), 16 if k.startswith('skill') else 32))
    for k, v in load('buildings').items():
        print('  %-3s %-22s %3d px' % (k, v, text.width(v)))


if __name__ == '__main__':
    if sys.argv[1:] == ['check']:
        check()
    elif sys.argv[1:] == ['dump']:
        for name in ('buildings', 'columns'):
            for k, v in load(name).items():
                print('%s\t%s\t%s' % (name, k, v))
    else:
        print(__doc__)

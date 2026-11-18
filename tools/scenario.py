"""DATA/SCENARIO.DAT reader (layouts from the loader 0x80075250 and the offset tables at 0x800b453c).

File: common part 0-0x5000, then one 0x8000 part per scenario (0x5000, 0xD000; a third slot
at 0x15000 is past the end of the file). Each part is read whole to 0x801D2000 and its
sections are copied to fixed buffers (bump-allocated from 0x80152000 at 0x8008e230, sizes are
constants there and in the loader; only 0x22C bytes are free after the last one).

All records are fixed size with the names in place; bytes after a name's 00 are junk.

usage: scenario.py dump [section] [scenario]     (prints Japanese: for notes only)
"""
import os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'extract', 'DATA', 'SCENARIO.DAT')
SCEN = (0x5000, 0xD000)

# name: (part, offset, record size, count, [(field, offset, room incl. NUL)], RAM buffer gp offset)
SECTIONS = {
    'provinces': ('common', 0x180, 6, 64, [('name', 1, 5)], -0x64f4),
    'commands':  ('common', 0x71c, 14, 40, [('name', 2, 12)], -0x64c8),
    'castles':   ('scen', 0xa8c, 40, 200, [('name', 15, 9)], -0x64ec),
    'persons':   ('scen', 0x3fac, 18, 250, [('family', 2, 9), ('given', 11, 7)], -0x64d8),
    'ranks':     ('scen', 0x6b30, 12, 100, [('name', 1, 11)], -0x64c0),
    'items':     ('scen', 0x7170, 18, 200, [('name', 2, 12)], -0x64b8),
}


def load():
    return open(PATH, 'rb').read()


def base(name, scenario=0):
    part, off = SECTIONS[name][:2]
    return off + (SCEN[scenario] if part == 'scen' else 0)


def cstr(b):
    return b.split(b'\0')[0].decode('cp932', 'replace')


def records(data, name, scenario=0):
    """-> list of (raw record bytes, {field: Japanese string})"""
    _, _, size, count, fields, _ = SECTIONS[name]
    o = base(name, scenario)
    out = []
    for i in range(count):
        r = data[o + i * size:o + (i + 1) * size]
        out.append((r, {f: cstr(r[a:a + n]) for f, a, n in fields}))
    return out


def persons(data, scenario=0):
    """-> [(birth year - 1490, family, given)] for ids 0-249"""
    return [(r[0], f['family'], f['given']) for r, f in records(data, 'persons', scenario)]


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != 'dump':
        sys.exit(__doc__)
    d = load()
    for name in ([sys.argv[2]] if len(sys.argv) > 2 else SECTIONS):
        sc = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        print('== %s (file 0x%x)' % (name, base(name, sc)))
        for i, (r, f) in enumerate(records(d, name, sc)):
            print(i, ' '.join(f.values()), r.hex())

"""Person names: Japanese from SCENARIO.DAT, English from tl/names_persons.json.

Japanese layout (scenario.py 'persons'): 250 x 18 bytes = year of birth - 1490 (u8), 00,
family[9], given[7]. Read-only: copied from the scenario part to the buffer at gp-0x64d8
(0x80156B70, 0x1194 bytes) and never saved. Readers (EXE only): record pointer 0x8005d6bc,
called by family 0x8005df44, given 0x8005e034, full 0x8005e124 (each copies into 5 rotating
static buffers of 9 / 7 / 13 bytes at 0x800d97b8 / 0x800d97e8 / 0x800d980c) and birth byte
0x8005e290. Ids >= 250 (full name only): 11-byte records at 0x800b7e5c in the EXE. Id 0 = the
player and, in scenario 2, id 1: names from the player record instead (see notes/engine.md).

English layout (`table()`, same 0x1194-byte section in both scenario parts): 250 birth bytes,
at INDEX 32 x u16 LE = offset of the pair of id 8k, then 250 x "family\\0given\\0" packed. The
getters (rewritten in place by `patch()`, same entry points) find the pair through the index
and copy into 5 rotating buffers each as before, now 12 / 18 / 24 bytes at BUF (the unused
tail of the FONT.DAT buffer). Full name = family + ' ' + given. Ids 250-275 (generic people,
full name only): tl/names_generic.json packed over the old 11-byte records at 0x800b7e5c.
The player branches (ids 0 and, in scenario 2, 1) are unchanged.

tl/names_persons.json: [{"id": n, "en": [family, given], "s2": [..]}] (s2 = scenario 2 where
it differs). `init` builds it once from TR4's English by kanji (exact pair, then parts) and
NEW below; edit by hand afterwards. script/names_persons.json = the Japanese (not committed).

usage: names.py init | export | check
"""
import collections, json, os, struct, sys

sys.path.insert(0, os.path.dirname(__file__))
import asm, scenario, text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = os.path.join(ROOT, 'tl', 'names_persons.json')
SCRIPT = os.path.join(ROOT, 'script', 'names_persons.json')
TR4 = os.path.expanduser('~/Projects/taiko_risshiden_4_translation')
GENERIC_TL = os.path.join(ROOT, 'tl', 'names_generic.json')
ROOM = 0x1194
INDEX = 0xFC                              # u16 offsets of every 8th pair
EXE_BASE, EXE_OFF = 0x80010000, 0x800
FAMILY, GIVEN, FULL, BIRTH, BLOCK_END = 0x8005df44, 0x8005e034, 0x8005e124, 0x8005e290, 0x8005e2bc
G_TABLE = -0x64d8                         # $gp-relative pointer to the person section
G_ROT = (-0x656c, -0x6564, -0x655c)       # rotation counters: family, given, full
IS_PLAYER2 = 0x8005d750                   # id 1 in scenario 2
PLAYER = {FAMILY: (0x80060bc4, 0x80060d3c), GIVEN: (0x80060c4c, 0x80060dc4), FULL: (0x80060ccc, 0x80060e44)}
DUMMY = 0x800b361c                        # record for ids >= 250 (birth byte)
GENERIC, GENERIC_N, GENERIC_ROOM = 0x800b7e5c, 27, 26 * 11   # 276 = nameless in the Japanese (record past the table)
BUF = 0x8016EE00                          # FONT.DAT buffer tail (file ends well before: vwf.py)
SLOT = (12, 18, 24)                       # buffer sizes: family, given, full

# People TR4 does not have (Hepburn, macrons). Single-name people keep the family part empty.
NEW = {
    ('浅野', '長勝'): ('Asano', 'Nagakatsu'), ('織田', '有楽斎'): ('Oda', 'Urakusai'),
    ('奥村', '永福'): ('Okumura', 'Nagatomi'), ('林', '通勝'): ('Hayashi', 'Michikatsu'),
    ('島', '左近'): ('Shima', 'Sakon'), ('松前', '慶広'): ('Matsumae', 'Yoshihiro'),
    ('結城', '朝勝'): ('Yūki', 'Tomokatsu'), ('柘植', '与一'): ('Tsuge', 'Yoichi'),
    ('長', '綱連'): ('Chō', 'Tsunatsura'), ('本願寺', '光佐'): ('Hongan-ji', 'Kōsa'),
    ('稲田', '大炊助'): ('Inada', 'Ōinosuke'), ('波多野', '宗長'): ('Hatano', 'Munenaga'),
    ('松下', '之綱'): ('Matsushita', 'Yukitsuna'), ('伊丹', '親興'): ('Itami', 'Chikaoki'),
    ('鈴木', '佐大夫'): ('Suzuki', 'Sadayū'), ('堀内', '氏善'): ('Horiuchi', 'Ujiyoshi'),
    ('能島', '武吉'): ('Noshima', 'Takeyoshi'), ('赤松', '則房'): ('Akamatsu', 'Norifusa'),
    ('山名', '尭熙'): ('Yamana', 'Akihiro'), ('山中', '鹿之介'): ('Yamanaka', 'Shikanosuke'),
    ('', '竹阿弥'): ('', 'Chikuami'), ('', 'とも'): ('', 'Tomo'), ('', 'さと'): ('', 'Sato'),
    ('がん', 'まく'): ('', 'Ganmaku'), ('正親町', '天皇'): ('', 'Emperor Ōgimachi'),
    ('', 'おまつ'): ('', 'Omatsu'), ('百地', '丹波'): ('Momochi', 'Tanba'),
    ('国友', '一貫斎'): ('Kunitomo', 'Ikkansai'), ('斎藤', '守直'): ('Saitō', 'Morinao'),
    ('簗田', '政勝'): ('Yanada', 'Masakatsu'),
}


def japanese():
    d = scenario.load()
    return [[p[1:] for p in scenario.persons(d, s)] for s in (0, 1)]


def tr4():
    jp = json.load(open(os.path.join(TR4, 'script', 'names_persons.json')))
    en = {e['id']: e for e in json.load(open(os.path.join(TR4, 'tl', 'names_persons.json')))}
    full, fam, giv = {}, collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    for p in jp:
        e = en[p['id']]
        for s, (f, g) in p['jp'].items():
            E = e.get(s, e['en'])
            full[(f, g)] = tuple(E)
            if f:
                fam[f][E[0]] += 1
            if g:
                giv[g][E[1]] += 1
    return full, fam, giv


def init():
    if os.path.exists(TL):
        sys.exit('%s exists: edit it by hand (delete it to rebuild)' % TL)
    full, fam, giv = tr4()
    how = collections.Counter()

    def english(k):
        if k in full:
            how['tr4'] += 1
            return list(full[k])
        if k in NEW:
            how['new'] += 1
            f = NEW[k][0]
            if k[0] in fam and f and fam[k[0]].most_common(1)[0][0] != f:
                print('family differs from TR4:', k, f, fam[k[0]].most_common(1)[0][0])
            return list(NEW[k])
        how['parts'] += 1
        print('by parts:', k)
        return [fam[k[0]].most_common(1)[0][0] if k[0] else '', giv[k[1]].most_common(1)[0][0] if k[1] else '']

    s1, s2 = japanese()
    out = []
    for i in range(len(s1)):
        e = {'id': i, 'en': english(s1[i])}
        if s2[i] != s1[i]:
            e['s2'] = english(s2[i])
        out.append(e)
    with open(TL, 'w') as f:
        f.write('[\n' + ',\n'.join(json.dumps(e, ensure_ascii=False) for e in out) + '\n]\n')
    print(dict(how))


def export():
    s1, s2 = japanese()
    out = [{'id': i, 'jp': list(s1[i]), **({'s2': list(s2[i])} if s2[i] != s1[i] else {})} for i in range(len(s1))]
    os.makedirs(os.path.dirname(SCRIPT), exist_ok=True)
    with open(SCRIPT, 'w') as f:
        f.write('[\n' + ',\n'.join(json.dumps(e, ensure_ascii=False) for e in out) + '\n]\n')


def english(scen=0):
    """-> [(family, given)] for ids 0-249"""
    key = 's%d' % (scen + 1)
    return [tuple(e.get(key, e['en'])) for e in json.load(open(TL))]


def table(scen=0):
    """The English person section (ROOM bytes): birth bytes, then packed name pairs."""
    d = scenario.load()
    out = bytearray(p[0] for p in scenario.persons(d, scen)).ljust(INDEX + 64, b'\0')
    for i, (f, g) in enumerate(english(scen)):
        if len(f) >= SLOT[0] or len(g) >= SLOT[1] or len(f) + len(g) + 1 >= SLOT[2]:
            raise ValueError('person %d: name too long for the buffers: %s %s' % (i, f, g))
        if i % 8 == 0:
            struct.pack_into('<H', out, INDEX + i // 4, len(out))
        out += text.enc(f) + b'\0' + text.enc(g) + b'\0'
    if len(out) > ROOM:
        raise ValueError('person names: %d bytes, room %d' % (len(out), ROOM))
    return bytes(out) + bytes(ROOM - len(out))


def generic():
    names = json.load(open(GENERIC_TL))
    assert len(names) == GENERIC_N
    out = b''.join(text.enc(n) + b'\0' for n in names)
    if len(out) > GENERIC_ROOM or max(map(len, names)) >= SLOT[2]:
        raise ValueError('generic names: %d bytes, room %d' % (len(out), GENERIC_ROOM))
    return out.ljust(GENERIC_ROOM, b'\0')


def patch_scenario(data):
    """SCENARIO.DAT -> the same with the English person section in both scenario parts."""
    data = bytearray(data)
    for s in (0, 1):
        o = scenario.base('persons', s)
        data[o:o + ROOM] = table(s)
    return bytes(data)


def code_find():
    return [
        'find:',                               # a0 = id -> v0 = "family\0given\0" (leaf; keeps a0)
        ('sltiu', 'at', 'a0', 250), ('lw', 't0', G_TABLE, 'gp'), ('bnez', 'at', 'f1'), ('srl', 't1', 'a0', 3),
        ('jr', 'ra'), ('addiu', 'v0', 't0', ROOM - 2),
        'f1:',
        ('sll', 't1', 't1', 1), ('addu', 't1', 't1', 't0'), ('lhu', 'v0', INDEX, 't1'), ('andi', 't2', 'a0', 7),
        ('addu', 'v0', 'v0', 't0'), ('sll', 't2', 't2', 1),
        'skip:',                               # (also entered from `given`: skip t2 strings at v0)
        ('beqz', 't2', 'f3'), ('nop',),
        'f2:',
        ('lbu', 't1', 0, 'v0'), ('addiu', 'v0', 'v0', 1), ('bnez', 't1', 'f2'), ('nop',),
        ('b', 'skip'), ('addiu', 't2', 't2', -1),
        'f3:',
        ('jr', 'ra'), ('nop',),
    ]


def code():
    """-> {address: listing} for the four entry points (find after `family`, copy after `given`)."""
    hi, lo = asm.hi, asm.lo

    def entry(addr, kind, body):
        p0, p1 = PLAYER[addr]
        return [
            ('addiu', 'sp', 'sp', -0x18), ('sw', 'ra', 0x14, 'sp'), ('sw', 's0', 0x10, 'sp'),
            ('beqz', 'a0', 'p0'), ('addu', 's0', 'a0', 'zero'),
            ('jal', IS_PLAYER2), ('nop',), ('bnez', 'v0', 'p1'), ('nop',),
        ] + body + [
            ('lui', 'a0', hi(BUF)), ('addiu', 'a0', 'a0', lo(BUF) + sum(5 * n for n in SLOT[:kind])),
            ('addiu', 'a1', 'zero', SLOT[kind]), ('jal', 'copy'), ('addiu', 'a2', 'gp', G_ROT[kind]),
        ]

    out = [
        ('lw', 'ra', 0x14, 'sp'), ('lw', 's0', 0x10, 'sp'), ('jr', 'ra'), ('addiu', 'sp', 'sp', 0x18),
        'p0:', ('jal', 0), ('nop',), ('b', 'out'), ('nop',),
        'p1:', ('jal', 0), ('nop',), ('b', 'out'), ('nop',),
    ]

    def leave(addr):
        o = list(out)
        o[o.index('p0:') + 1] = ('jal', PLAYER[addr][0])
        o[o.index('p1:') + 1] = ('jal', PLAYER[addr][1])
        return ['out:'] + o

    find = [('jal', 'find'), ('addu', 'a0', 's0', 'zero')]
    family = entry(FAMILY, 0, find + [('addu', 'a3', 'v0', 'zero')]) + leave(FAMILY) + code_find()
    copy = [
        'copy:',                               # a0 = buffers, a1 = slot size, a2 = &counter, a3 = string
        ('lw', 't0', 0, 'a2'), ('nop',),       # -> v0 = slot, a0 = after its NUL, a3 = after the string's NUL
        ('mult', 't0', 'a1'), ('addiu', 't0', 't0', 1), ('sltiu', 'at', 't0', 5), ('bnez', 'at', 'c1'), ('mflo', 't1'),
        ('addu', 't0', 'zero', 'zero'),
        'c1:',
        ('sw', 't0', 0, 'a2'), ('addu', 'a0', 'a0', 't1'), ('addu', 'v0', 'a0', 'zero'),
        'c2:',
        ('lbu', 't1', 0, 'a3'), ('addiu', 'a3', 'a3', 1), ('sb', 't1', 0, 'a0'), ('bnez', 't1', 'c2'),
        ('addiu', 'a0', 'a0', 1),
        ('jr', 'ra'), ('nop',),
    ]
    given = (entry(GIVEN, 1, find + [('jal', 'skip'), ('addiu', 't2', 'zero', 1),
                                        ('addu', 'a3', 'v0', 'zero')]) + leave(GIVEN) + copy)
    full = (entry(FULL, 2, [
        ('sltiu', 'at', 's0', 250), ('bnez', 'at', 'person'), ('addiu', 't2', 's0', -250),
        ('sltiu', 'at', 't2', GENERIC_N), ('bnez', 'at', 'gen'), ('lui', 'v0', hi(GENERIC)),
        ('addu', 't2', 'zero', 'zero'),        # unknown id: the first generic name
        'gen:',
        ('jal', 'skip'), ('addiu', 'v0', 'v0', lo(GENERIC)),
        ('b', 'have'), ('addiu', 's0', 'zero', -1),
        'person:',
        ('jal', 'find'), ('addu', 'a0', 's0', 'zero'),
        'have:',
        ('addu', 'a3', 'v0', 'zero'),
    ]) + [
        ('bltz', 's0', 'out'), ('addiu', 'a0', 'a0', -1),      # generic: one string
        ('lbu', 't1', 0, 'a3'), ('beq', 'a0', 'v0', 'g2'),     # empty family: no space
        ('addiu', 't0', 'zero', 0x20), ('beqz', 't1', 'out'), ('nop',),
        ('sb', 't0', 0, 'a0'), ('addiu', 'a0', 'a0', 1),
        'g2:',
        ('lbu', 't1', 0, 'a3'), ('addiu', 'a3', 'a3', 1), ('sb', 't1', 0, 'a0'), ('bnez', 't1', 'g2'),
        ('addiu', 'a0', 'a0', 1),
    ] + leave(FULL))
    birth = [                                  # (no load in the jr delay slot: the caller adds to v0 at once;
        ('sltiu', 'at', 'a0', 250), ('lw', 'v0', G_TABLE, 'gp'),      # no t registers: the age function keeps
        ('bnez', 'at', 'ok'), ('lui', 'at', hi(DUMMY)),               # the year in t0 across this call)
        ('b', 'load'), ('addiu', 'v0', 'at', lo(DUMMY)),
        'ok:',
        ('addu', 'v0', 'v0', 'a0'),
        'load:',
        ('lbu', 'v0', 0, 'v0'), ('jr', 'ra'), ('nop',),
    ]
    lab = {k: v for k, v in asm.labels(FAMILY, family).items() if k in ('find', 'skip')}
    lab['copy'] = asm.labels(GIVEN, given)['copy']
    fix = lambda L: [tuple(lab.get(x, x) if isinstance(x, str) and x in lab and i else x for i, x in enumerate(l))
                     if isinstance(l, tuple) else l for l in L]
    family = family[:family.index('find:')]
    out = {FAMILY: fix(family) + code_find(), GIVEN: fix(given[:given.index('copy:')]) + copy, FULL: fix(full),
           BIRTH: birth}
    return out


def patch(exe):
    """exe: bytearray of SLPM_862.68 -> the getters rewritten, generic names in English."""
    ends = {FAMILY: GIVEN, GIVEN: FULL, FULL: BIRTH, BIRTH: BLOCK_END}
    free = 0
    for addr, L in code().items():
        c = asm.assemble(addr, L)
        room = ends[addr] - addr
        assert len(c) <= room, 'getter %08x: %d bytes over' % (addr, len(c) - room)
        o = addr - EXE_BASE + EXE_OFF
        exe[o:o + room] = c.ljust(room, b'\0')
        free += room - len(c)
    o = GENERIC - EXE_BASE + EXE_OFF
    exe[o:o + GENERIC_ROOM] = generic()
    return free


def check():
    for s in (0, 1):
        names = english(s)
        used = INDEX + 64 + sum(len(f) + len(g) + 2 for f, g in names)
        w = [(text.width((f + ' ' + g).strip()), f, g) for f, g in names]
        table(s)
        print('scenario %d: %d of %d bytes; widest full %s, family %d px, given %d px' % (
            s + 1, used, ROOM, max(w), max(text.width(f) for f, g in names), max(text.width(g) for f, g in names)))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd not in ('init', 'export', 'check'):
        sys.exit(__doc__)
    globals()[cmd]()

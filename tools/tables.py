"""Table names (castles, provinces, items, commands, court ranks): tl/tables/*.txt -> the game.

Japanese (scenario.py): fixed records in SCENARIO.DAT with the name in place, copied to arena
buffers. Each table has one record-pointer function and one name getter that copies the name
into rotating static buffers (callers may keep or extend the result):
  castles    0x80056264(id, suffix) (says 空き城 for a vacant castle) and 0x80056394(id, suffix);
             suffix != 0 appends 城 / 寺 / の町 / 館 by castle type (0x800556dc)
  provinces  0x800585f0(id)    items 0x8005b040(id)    commands 0x8005b9d0(id)    ranks 0x8005ec20(id)
Castle records are saved and their names change in play: events rename castles (strings at
RENAMES: 岐阜 長浜 安土 大坂 京都二条, setter 0x80056494) and the player names a castle he builds
(MAPPOINT 0x800fd2ec-0x800fd3dc). Scenario 2 starts with four of the renamed castles.

English: the records keep their Japanese names (saves stay compatible both ways) and the getters
are rewritten in place (same entry points) to read a blob of English names:
- blob (`blob()`): u16 offsets of every string (castles + dummy, provinces + dummy, items + dummy,
  commands + dummy, ranks + dummy, 4 suffixes, vacant), u16 hash of each castle's default Japanese
  name, the renames as (hash, offset) pairs ending with 0, then the strings (text.enc).
  It is appended to SCENARIO.DAT at BLOB_OFF and read once at boot (the FONT.DAT load at
  0x80083018 calls `boot`) to BLOB_RAM = 0x80187000: the top 0x2000 bytes of the current
  MESSAGE block buffer (0x80179000 + 0x10000; packed blocks are capped at msgfile.ROOM and the loader
  reads only the block's size). NOT the gap below the stack (0x801FC000, used until session 23):
  MAPPOINT 0x8010e004 has a 0x4058-byte frame and the stack reaches ~0x801FB700. Limit BLOB_ROOM.
- castle getter: hash of the record's name == the castle's default hash -> English by id; else a
  rename with that hash -> its English; else the record's own bytes (a name the player entered).
- rotating buffers: BUFS = 0x8015EDD4 (the 0x22C bytes after the arena, before FONT.DAT).

tl/tables/<table>.txt: key<TAB>English; keys = record number, `bug` (the dummy record, バグ),
castles also `vacant`, `suffix0`-`suffix3`, `@address` (rename string in the EXE).
`init` builds them once from TR4's English by kanji and NEW below; edit by hand afterwards.

usage: tables.py init | check | dump
"""
import glob, json, os, struct, sys

sys.path.insert(0, os.path.dirname(__file__))
import asm, scenario, text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = os.path.join(ROOT, 'tl', 'tables')
TR4 = os.path.expanduser('~/Projects/taiko_risshiden_4_translation')
EXE_BASE, EXE_OFF = 0x80010000, 0x800

BLOB_OFF, BLOB_RAM, BLOB_ROOM = 0x16000, 0x80187000, 0x2000
SCENARIO_FILE, FONT_FILE, FONT_RAM = 11, 5, 0x8015F000
LOAD_FILE, LOAD_PART = 0x80081e2c, 0x80081d3c
FONT_LOAD = 0x80083018                    # 5 instructions: a0 = 5, a1 = 0x8015F000, jal LOAD_FILE
BUFS, BUFS_END = 0x8015EDD4, 0x8015F000
REC, CASTLE_TYPE, VACANT = 0x80055520, 0x800556dc, 0x80055678
CASTLE_A, CASTLE_B, CASTLE_END = 0x80056264, 0x80056394, 0x80056494
SUFFIX_CODE = 0x8005b040 + 12              # the castle getters' tail, after the item getter
RENAMES = (0x800cf878, 0x800cf880, 0x800cf888, 0x800cf890, 0x800b3a64)
# kind: (table, getter, end of its code, buffer slot size, slots)
KINDS = [
    ('castles', CASTLE_A, None, 28, 5),
    ('provinces', 0x800585f0, 0x80058690, 12, 4),
    ('items', 0x8005b040, 0x8005b0e8, 24, 3),
    ('commands', 0x8005b9d0, 0x8005ba78, 20, 3),
    ('ranks', 0x8005ec20, 0x8005ecc8, 16, 3),
    ('castles', CASTLE_B, None, 28, 5),       # the second castle getter: its own buffers
    ('vacant', None, None, 0, 0),             # one string, in the first castle getter's buffers
]
TABLES = ('castles', 'provinces', 'items', 'commands', 'ranks')
RAW_COMMAND, RAW_COMMAND_END = 0x8005ba78, 0x8005baa4   # second command getter (see patch)
SUFFIX_MAX = 8                            # " Castle" + NUL

# Names TR4 does not have (Hepburn, macrons; castle names without a suffix)
NEW = {
    'provinces': {
        '出羽': 'Dewa', '信濃': 'Shinano', '上総': 'Kazusa', '安房': 'Awa', '相模': 'Sagami', '伊豆': 'Izu',
        '若狭': 'Wakasa', '近江': 'Ōmi', '伊勢': 'Ise', '志摩': 'Shima', '河内': 'Kawachi', '大和': 'Yamato',
        '和泉': 'Izumi', '但馬': 'Tajima', '因幡': 'Inaba', '周防': 'Suō', '長門': 'Nagato', '淡路': 'Awaji',
        '阿波': 'Awa',
    },
    'commands': {
        '墨俣築城': 'Build Sunomata', '相場調査': 'Check Prices', '馬相場調査': 'Horse Prices',
        '城情報収集': 'Scout Castle', '武者修業': 'Warrior Training', '兵糧購入': 'Buy Rice',
        '軍馬購入': 'Buy Horses', '鉄砲購入': 'Buy Guns', '大筒購入': 'Buy Cannon', '商業発展': 'Commerce',
        '改修': 'Repairs', '築城': 'Build Castle', '検地': 'Land Survey', '大名調査': 'Scout Daimyō',
        '？？': '??', '使者': 'Envoy', '朝廷工作': 'Court Lobbying', '人材勧誘': 'Recruit',
        '足軽雇用': 'Hire Ashigaru', '城守備': 'Guard Castle', '地方攻略': 'Take Region',
        '米買い占め': 'Corner Rice', '城主調略': 'Win Over Lord', '半兵衛勧誘': 'Recruit Hanbei',
        '三人衆調略': 'Win Over Trio', '予約２': 'Reserved 2', '予約３': 'Reserved 3', '予約４': 'Reserved 4',
    },
    'ranks': {'権少納言': 'V.Shōnagon'},
    'items': {
        '十訓抄': 'Jikkinshō', '庭訓往来': 'Teikin Ōrai', '更級日記': 'Sarashina Diary',
        '十六夜日記': 'Izayoi Diary', '落窪物語': 'Tale of Ochikubo', '宇津保物語': 'Tale of Utsubo',
        '無銘脇差': 'Plain Wakizashi', '白糸素懸威': 'White Sugake', '紅糸威小腹巻': 'Red Haramaki',
        '松嶋の壷': 'Matsushima Jar', '三日月茶壷': 'Mikazuki Jar', '松屋肩衝': 'Matsuya Caddy',
        '勢高肩衝': 'Seitaka Caddy', '珠光文琳': 'Jukō Caddy', '唐物橋姫': 'Hashihime', '丹波茶壷': 'Tanba Jar',
        '喫茶養生記': 'Kissa Yōjōki', '赤絵茶入': 'Akae Caddy', '大鏡': 'Ōkagami', '秋冬山水図': 'Autumn & Winter',
        '論語': 'Analects', '置時計': 'Table Clock', 'ビードロ壷': 'Glass Jar', 'ルソン壷': 'Luzon Jar',
        '金の十字架': 'Gold Cross', '絹織物': 'Silk Cloth', '銀の十字架': 'Silver Cross', '羅紗布': 'Woollen Cloth',
        '火薬': 'Gunpowder', 'タバコ': 'Tobacco', '綿織物': 'Cotton Cloth', '麻布': 'Hemp Cloth',
        '翡翠の宝石箱': 'Jade Jewel Box', '琥珀': 'Amber', '石見銀': 'Iwami Silver', '後撰和歌集': 'Gosen Wakashū',
        '壮腎丹': 'Sōjintan', '吾妻鏡': 'Azuma Kagami', '西馬丹': 'Seibatan',
    },
    'castles': {
        '浪岡': 'Namioka', '高水寺': 'Kōsuiji', '寺池': 'Teraike', '三春': 'Miharu', '大館': 'Ōdate', '小峰': 'Komine',
        '横手': 'Yokote', '尾浦': 'Oura', '石動': 'Isurugi', '平井': 'Hirai', '小山': 'Oyama', '岩槻': 'Iwatsuki',
        '滝山': 'Takiyama', '津久井': 'Tsukui', '下田': 'Shimoda', '深沢': 'Fukasawa', '掛川': 'Kakegawa',
        '福水': 'Fukumizu', '小松': 'Komatsu', '丸岡': 'Maruoka', '府中': 'Fuchū', '後瀬山': 'Nochiseyama',
        '高浜': 'Takahama', '横山': 'Yokoyama', '長光寺': 'Chōkōji', '郡上八幡': 'Gujō-Hachiman', '犬山': 'Inuyama',
        '野田': 'Noda', '津山': 'Tsuyama', '峯': 'Mine', '伊勢亀山': 'Ise-Kameyama', '京都': 'Kyōto',
        '勝竜寺': 'Shōryūji', '高屋': 'Takaya', '多聞': 'Tamon', '高取': 'Takatori', '茨木': 'Ibaraki',
        '尼崎': 'Amagasaki', '石山本願': 'Ishiyama Hongan', '花隈': 'Hanakuma', '根来寺': 'Negoro-ji',
        '紀伊太田': 'Kii-Ōta', '田辺': 'Tanabe', '竹田': 'Takeda', '若桜': 'Wakasa', '鹿野': 'Shikano',
        '八橋': 'Yabase', '神西': 'Jinzai', '三本松': 'Sanbonmatsu', '明石': 'Akashi', '龍野': 'Tatsuno',
        '古高山': 'Furutakayama', '左東銀山': 'Satō-Kanayama', '鞍掛山': 'Kurakakeyama',
        '富田若山': 'Tonda-Wakayama', '指月': 'Shizuki', '州本': 'Sumoto', '海部': 'Kaifu', '大洲': 'Ōzu',
        '黒瀬': 'Kurose', '高良': 'Kōra', '日野江': 'Hinoe', '村中': 'Muranaka', '水俣': 'Minamata',
        '門川': 'Kadogawa', '高鍋': 'Takanabe', '肝付': 'Kimotsuki', '垂水': 'Tarumizu', '一宇治': 'Ichiuji',
        # renames
        '岐阜': 'Gifu', '長浜': 'Nagahama', '安土': 'Azuchi', '大坂': 'Ōsaka', '京都二条': 'Kyōto Nijō',
    },
}
EXTRA = {'bug': 'Bug', 'vacant': 'Vacant Castle',
         'suffix0': ' Castle', 'suffix1': '-ji', 'suffix2': ' Town', 'suffix3': ' Manor'}


def japanese(table, scen=0):
    return [f['name'] for r, f in scenario.records(scenario.load(), table, scen)]


def exe_str(addr):
    d = open(os.path.join(ROOT, 'extract', 'SLPM_862.68'), 'rb').read()
    return scenario.cstr(d[addr - EXE_BASE + EXE_OFF:][:16])


def tr4():
    m = {}
    for p in sorted(glob.glob(TR4 + '/script/tables/*.json')):
        n = os.path.basename(p)[:-5]
        jp = {r['id']: r['jp'] for r in json.load(open(p))['rows']}
        for l in open(TR4 + '/tl/tables/%s.txt' % n):
            if not l.startswith('#') and '\t' in l:
                i, e = l.rstrip('\n').split('\t', 1)
                if e and int(i) in jp:
                    m.setdefault(jp[int(i)], e)
    return m


def init():
    m = tr4()
    os.makedirs(TL, exist_ok=True)
    for t in TABLES:
        path = os.path.join(TL, t + '.txt')
        if os.path.exists(path):
            sys.exit('%s exists: edit it by hand (delete it to rebuild)' % path)

        def english(j):
            e = NEW[t].get(j) or m.get(j) or (t == 'castles' and m.get(j + '城'))
            if not e:
                sys.exit('%s: no English for %s' % (t, j))
            return e
        rows = [(str(i), english(j)) for i, j in enumerate(japanese(t))] + [('bug', EXTRA['bug'])]
        if t == 'castles':
            rows += [(k, v) for k, v in EXTRA.items() if k != 'bug']
            rows += [('@%08x' % a, english(exe_str(a))) for a in RENAMES]
        with open(path, 'w') as f:
            f.write('# %s: key<TAB>English (tools/tables.py)\n' % t)
            f.write(''.join('%s\t%s\n' % r for r in rows))
        print(t, len(rows))


def english(table):
    out = {}
    for l in open(os.path.join(TL, table + '.txt')):
        if not l.startswith('#') and '\t' in l:
            k, e = l.rstrip('\n').split('\t', 1)
            out[k] = e
    return out


def have():
    return all(os.path.exists(os.path.join(TL, t + '.txt')) for t in TABLES)


def jhash(b):
    """Hash of a castle's Japanese name field (up to 8 bytes): the getter computes the same."""
    h = 0
    for c in b.split(b'\0')[0][:8]:
        h = (h * 3 + c) & 0xFFFFFFFF
    return h & 0xFFFF


def layout():
    """-> (strings in offset-table order, {kind: (base, count)}, index of the first suffix)"""
    strings, desc = [], {}
    for t in TABLES:
        en = english(t)
        n = scenario.SECTIONS[t][3]
        desc[t] = (len(strings), n)
        strings += [en[str(i)] for i in range(n)] + [en['bug']]
    c = english('castles')
    suffix = len(strings)
    strings += [c['suffix%d' % i] for i in range(4)]
    desc['vacant'] = (len(strings), 1)
    strings.append(c['vacant'])
    return strings, desc, suffix


def blob():
    strings, desc, suffix = layout()
    c = english('castles')
    renames = [(exe_str(a).encode('cp932'), c['@%08x' % a]) for a in RENAMES]
    d = scenario.load()
    default = [bytes(r[15:24]) for r, f in scenario.records(d, 'castles', 0)]
    hashes = [jhash(b) for b in default]
    alt = [jhash(j) for j, e in renames]
    # by id first, so only the renames must differ from each other (and a player's own name from both)
    assert len(set(alt)) == len(alt) and 0 not in alt, 'castle rename hash collision'
    for b in (bytes(r[15:24]) for r, f in scenario.records(d, 'castles', 1)):     # scenario 2 starts renamed
        assert jhash(b) in hashes or jhash(b) in alt, b
    hash_at = 2 * len(strings)
    alt_at = hash_at + 2 * len(hashes)
    pos = alt_at + 4 * len(alt) + 2
    body, offs, seen = bytearray(), [], {}
    for s in strings + [e for j, e in renames]:
        if s not in seen:
            seen[s] = pos + len(body)
            body += text.enc(s) + b'\0'
        offs.append(seen[s])
    out = struct.pack('<%dH' % len(strings), *offs[:len(strings)]) + struct.pack('<%dH' % len(hashes), *hashes)
    out += b''.join(struct.pack('<HH', h, o) for h, o in zip(alt, offs[len(strings):])) + bytes(2) + body
    if len(out) > BLOB_ROOM:
        raise ValueError('table names: %d bytes, room %d' % (len(out), BLOB_ROOM))
    return bytes(out), desc, suffix, hash_at, alt_at


def bufs():
    """-> ({kind index: offset of its buffers from BUFS}, total size); a counter byte per kind first"""
    at, pos = {}, 8
    for k, (t, _, _, size, n) in enumerate(KINDS):
        at[k] = pos if n else at[0]
        pos += size * n
    assert BUFS + pos <= BUFS_END, 'table name buffers: %d bytes' % pos
    return at, pos


def check():
    b, desc, suffix, _, _ = blob()
    strings = layout()[0]
    sufw = max(len(s) for s in strings[suffix:suffix + 4])
    for k, (t, _, _, size, n) in enumerate(KINDS):
        if not n:
            continue
        base, cnt = desc[t]
        names = strings[base:base + cnt + 1] + ([strings[desc['vacant'][0]]] if t == 'castles' else [])
        longest = max(names, key=len)
        need = len(longest) + 1 + (sufw if t == 'castles' else 0)
        widest = max(names, key=text.width)
        print('%-9s %3d names, longest %d (%s), buffer %d, widest %d px (%s)' % (
            t, cnt, len(longest), longest, size, text.width(widest), widest))
        if need > size:
            raise ValueError('%s: %r needs %d bytes, buffer %d' % (t, longest, need, size))
    print('blob %d of %d bytes, buffers %d of %d' % (len(b), BLOB_ROOM, bufs()[1], BUFS_END - BUFS))


def li(reg, value):
    return [('lui', reg, value >> 16), ('ori', reg, reg, value & 0xFFFF)]


def code():
    """-> {address: (listing, end)}"""
    _, desc, suffix, hash_at, alt_at = blob()
    at, _ = bufs()
    hi, lo = asm.hi, asm.lo
    D = 'desc'                                 # resolved after the first pass
    region1 = [
        # castle getter A (a0 = id, a1 = suffix flag): "Vacant Castle" for a vacant castle
        ('addiu', 'sp', 'sp', -0x20), ('sw', 'ra', 0x1c, 'sp'), ('sw', 'a0', 0x10, 'sp'),
        ('jal', VACANT), ('sw', 'a1', 0x14, 'sp'),
        ('lw', 'a0', 0x10, 'sp'), ('lw', 'a1', 0x14, 'sp'), ('lw', 'ra', 0x1c, 'sp'),
        ('beqz', 'v0', 'normal'), ('addiu', 'sp', 'sp', 0x20),
        ('addiu', 'a1', 'zero', 6), ('j', 'tname'), ('addu', 'a0', 'zero', 'zero'),
        'normal:',
        ('j', CASTLE_B + 4), ('addu', 'a2', 'zero', 'zero'),
        # tname(a0 = id, a1 = kind) -> v0 = name in a rotating buffer, a0 = its NUL (leaf)
        'tname:',
        ('lui', 't9', 'DESC_HI'), ('sll', 't0', 'a1', 3), ('addu', 't9', 't9', 't0'),
        ('lhu', 't1', ('DESC_LO', 2), 't9'), ('lhu', 't2', ('DESC_LO', 0), 't9'), ('lui', 't3', BLOB_RAM >> 16),
        ('sltu', 'at', 'a0', 't1'), ('bnez', 'at', 't_ok'), ('ori', 't3', 't3', BLOB_RAM & 0xFFFF),
        ('addu', 'a0', 't1', 'zero'),          # out of range: the dummy entry
        't_ok:',
        ('addu', 't2', 't2', 'a0'), ('sll', 't2', 't2', 1), ('addu', 't2', 't2', 't3'),
        ('lhu', 't2', 0, 't2'), ('nop',), ('addu', 'a3', 't3', 't2'),
        # copyrot(a1 = kind, a3 = string) -> the same results
        'copyrot:',
        ('lui', 't9', 'DESC_HI'), ('sll', 't0', 'a1', 3), ('addu', 't9', 't9', 't0'),
        ('lui', 't4', hi(BUFS)), ('addiu', 't4', 't4', lo(BUFS)), ('addu', 't5', 't4', 'a1'),
        ('lbu', 't0', 0, 't5'), ('lbu', 't6', ('DESC_LO', 7), 't9'), ('lbu', 't7', ('DESC_LO', 6), 't9'),
        ('addiu', 't0', 't0', 1), ('sltu', 'at', 't0', 't6'), ('bnez', 'at', 'c1'),
        ('lhu', 't8', ('DESC_LO', 4), 't9'),
        ('addu', 't0', 'zero', 'zero'),
        'c1:',
        ('sb', 't0', 0, 't5'), ('mult', 't0', 't7'), ('mflo', 't0'), ('addu', 't0', 't0', 't8'),
        ('addu', 'v0', 't4', 't0'), ('addu', 'a0', 'v0', 'zero'),
        'c2:',
        ('lbu', 't1', 0, 'a3'), ('addiu', 'a3', 'a3', 1), ('sb', 't1', 0, 'a0'), ('bnez', 't1', 'c2'),
        ('addiu', 'a0', 'a0', 1),
        ('jr', 'ra'), ('addiu', 'a0', 'a0', -1),
        'desc:',
    ]
    lab = asm.labels(CASTLE_A, region1)
    dhi, dlo = hi(lab['desc']), lo(lab['desc'])

    def fix(L):
        out = []
        for l in L:
            if isinstance(l, tuple):
                l = tuple(dhi if x == 'DESC_HI' else dlo + x[1] if isinstance(x, tuple) else x for x in l)
            out.append(l)
        return out
    region1 = fix(region1)
    table = b''.join(struct.pack('<HHHBB', *desc[t], at[k], size or KINDS[0][3], n or KINDS[0][4])
                     for k, (t, _, _, size, n) in enumerate(KINDS))
    tname, copyrot = lab['tname'], lab['copyrot']
    region2 = [
        # castle getter B (a0 = id, a1 = suffix flag); A jumps to +4 with a2 = 0
        ('addiu', 'a2', 'zero', 5),
        ('addiu', 'sp', 'sp', -0x28), ('sw', 'ra', 0x24, 'sp'), ('sw', 's0', 0x10, 'sp'), ('sw', 's1', 0x14, 'sp'),
        ('sw', 's2', 0x18, 'sp'), ('sw', 's3', 0x1c, 'sp'), ('addu', 's0', 'a0', 'zero'), ('addu', 's1', 'a1', 'zero'),
        ('jal', REC), ('addu', 's2', 'a2', 'zero'),
        ('addiu', 't0', 'v0', 15), ('addu', 'a3', 't0', 'zero'), ('addu', 't1', 'zero', 'zero'),
        ('addiu', 't2', 'zero', 8),
        'h1:',                                 # t1 = hash of the record's name
        ('lbu', 't3', 0, 't0'), ('addiu', 't0', 't0', 1), ('beqz', 't3', 'h2'), ('addiu', 't2', 't2', -1),
        ('sll', 't4', 't1', 1), ('addu', 't1', 't1', 't4'), ('bnez', 't2', 'h1'), ('addu', 't1', 't1', 't3'),
        'h2:',
        ('andi', 't1', 't1', 0xFFFF)] + li('t5', BLOB_RAM) + [
        ('sltiu', 'at', 's0', desc['castles'][1]), ('beqz', 'at', 'alt'), ('sll', 't0', 's0', 1),
        ('addu', 't0', 't0', 't5'), ('lhu', 't0', hash_at, 't0'), ('addu', 'a0', 's0', 'zero'),
        ('beq', 't0', 't1', 'byid'), ('nop',),
        'alt:',
        ('addiu', 't0', 't5', alt_at),
        'a1:',
        ('lhu', 't3', 0, 't0'), ('lhu', 't4', 2, 't0'), ('beqz', 't3', 'raw'), ('addiu', 't0', 't0', 4),
        ('bne', 't3', 't1', 'a1'), ('nop',),
        ('addu', 'a3', 't5', 't4'),
        'raw:',                                # a3 = the record's own name, or the rename's English
        ('jal', copyrot), ('addu', 'a1', 's2', 'zero'),
        ('b', 'tosuf'), ('nop',),
        'byid:',
        ('jal', tname), ('addu', 'a1', 's2', 'zero'),
        'tosuf:',
        ('j', SUFFIX_CODE), ('nop',),
    ]
    tail = [                                   # (in the spare room after the item getter)
        ('addu', 's2', 's1', 'zero'),          # suffix flag: 0 none, 1 always, 2 = all but " Castle" (lists)
        ('lbu', 't0', 0, 'v0'), ('beqz', 's1', 'out'), ('addu', 's3', 'v0', 'zero'),
        ('beqz', 't0', 'out'), ('addu', 's1', 'a0', 'zero'),
        ('jal', CASTLE_TYPE), ('addu', 'a0', 's0', 'zero'),
        ('addiu', 'at', 'zero', 2), ('bne', 's2', 'at', 'suf'), ('nop',),
        ('beqz', 'v0', 'out'), ('nop',),
        'suf:'] + li('t5', BLOB_RAM) + [
        ('sll', 'v0', 'v0', 1), ('addu', 't0', 't5', 'v0'), ('lhu', 't0', 2 * suffix, 't0'), ('nop',),
        ('addu', 'a3', 't5', 't0'),
        's1:',
        ('lbu', 't1', 0, 'a3'), ('addiu', 'a3', 'a3', 1), ('sb', 't1', 0, 's1'), ('bnez', 't1', 's1'),
        ('addiu', 's1', 's1', 1),
        'out:',
        ('addu', 'v0', 's3', 'zero'), ('lw', 'ra', 0x24, 'sp'), ('lw', 's0', 0x10, 'sp'), ('lw', 's1', 0x14, 'sp'),
        ('lw', 's2', 0x18, 'sp'), ('lw', 's3', 0x1c, 'sp'), ('jr', 'ra'), ('addiu', 'sp', 'sp', 0x28),
    ]
    assert alt_at < 0x8000 and 2 * suffix < 0x8000
    out = {CASTLE_A: (region1, CASTLE_B, table), CASTLE_B: (region2, CASTLE_END, b'')}
    for k, (t, getter, end, size, n) in enumerate(KINDS):
        if end:
            L = [('addiu', 'a1', 'zero', k), ('j', tname), ('nop',)]
            if t == 'provinces':               # room here for the boot loader of the blob
                L += ['boot:', ('addiu', 'sp', 'sp', -0x18), ('sw', 'ra', 0x10, 'sp'),
                      ('addiu', 'a0', 'zero', FONT_FILE), ('lui', 'a1', FONT_RAM >> 16),
                      ('jal', LOAD_FILE), ('ori', 'a1', 'a1', FONT_RAM & 0xFFFF),
                      ('addiu', 'a0', 'zero', SCENARIO_FILE)] + li('a1', BLOB_OFF) + li('a2', BLOB_RAM) + [
                      ('jal', LOAD_PART), ('addiu', 'a3', 'zero', BLOB_ROOM),
                      ('lw', 'ra', 0x10, 'sp'), ('nop',), ('jr', 'ra'), ('addiu', 'sp', 'sp', 0x18)]
            if getter == SUFFIX_CODE - 12:     # the end of the castle getters
                L += tail
            out[getter] = (L, end, b'')
    return out


def patch(exe):
    """exe: bytearray of SLPM_862.68 -> English table getters; returns the free bytes."""
    free = 0
    boot = None
    for addr, (L, end, data) in code().items():
        c = asm.assemble(addr, L) + data
        room = end - addr
        assert len(c) <= room, 'table getter %08x: %d bytes over' % (addr, len(c) - room)
        o = addr - EXE_BASE + EXE_OFF
        exe[o:o + room] = c.ljust(room, b'\0')
        free += room - len(c)
        boot = asm.labels(addr, L).get('boot', boot)
    # 0x8005ba78(id) returned record + 2 (the Japanese command name, kept by its caller: the 5-row policy
    # menu at MAPPOINT 0x800fd8f0 holds five pointers at once, so no rotating buffer): point into the blob
    base = blob()[1]['commands'][0]
    c = asm.assemble(RAW_COMMAND, li('t3', BLOB_RAM) + [
        ('addiu', 'a0', 'a0', base), ('sll', 'a0', 'a0', 1), ('addu', 'a0', 'a0', 't3'),
        ('lhu', 'v0', 0, 'a0'), ('jr', 'ra'), ('addu', 'v0', 'v0', 't3')])
    assert len(c) <= RAW_COMMAND_END - RAW_COMMAND
    o = RAW_COMMAND - EXE_BASE + EXE_OFF
    assert exe[o + 16:o + 20] == struct.pack('<I', 0x0c016e55)
    exe[o:o + RAW_COMMAND_END - RAW_COMMAND] = c.ljust(RAW_COMMAND_END - RAW_COMMAND, b'\0')
    o = FONT_LOAD - EXE_BASE + EXE_OFF
    assert exe[o + 12:o + 16] == struct.pack('<I', 0x0c000000 | (LOAD_FILE >> 2) & 0x3FFFFFF)
    exe[o:o + 20] = asm.assemble(FONT_LOAD, [('jal', boot), ('nop',), ('nop',), ('nop',), ('nop',)])
    return free


def patch_scenario(data, extra=()):
    """SCENARIO.DAT -> the same with the blob of English names appended at BLOB_OFF;
    extra = [(va, bytes)] of program strings placed after it (progstr.extra())."""
    assert len(data) <= BLOB_OFF
    b = bytearray(blob()[0].ljust(BLOB_ROOM, b'\0'))
    for va, x in extra:
        o = va - BLOB_RAM
        assert len(blob()[0]) <= o and o + len(x) <= BLOB_ROOM and not any(b[o:o + len(x)]), hex(va)
        b[o:o + len(x)] = x
    return data.ljust(BLOB_OFF, b'\0') + bytes(b)


def dump():
    for t in TABLES:
        en = english(t)
        print('==', t)
        print('  '.join('%s:%s' % kv for kv in en.items()))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd not in ('init', 'check', 'dump'):
        sys.exit(__doc__)
    globals()[cmd]()

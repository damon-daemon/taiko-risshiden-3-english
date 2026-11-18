"""Graphics with text, redrawn in English at build time (our own lettering, tools/pixfont.py).

The graphic files (RGRP / WGRP / KEEP / BG .DAT) have no headers: the program reads raw pieces by
offset and sends them to VRAM. `tools/emu/vram.py STATE find FILE` shows where a file's pieces sit in
VRAM, `tools/dev/rawgfx.py` shows a piece, `tools/dev/sprcalls.py` lists the sprite calls with the
address of every constant.

Person detail (Triangle -> People -> a person; code 0x8003a1f4-0x8003b700)
  RGRP.DAT 0x1e1800: 256-colour palette, 0x1e1a00: 448 x 256 picture at 8 bpp, sent to VRAM (480, 0).
  Left 320 px = the background, right 128 px (VRAM x 640.., "sheet") = sprites cut out by
  0x8003a0c8 / 0x8003a174(id, u, v, x; y, w, h): u in VRAM halfwords (2 px), v in rows.
  A label = background index 8, ink in its own palette index (the colour), shadow 0xf3 right / below.
  Japanese sheet: 12 skill labels 24 x 12 at (24 col, 12 row); 4 ability labels 36 x 12 at y 36 / 48;
  5 + 1 affiliation labels 60 x 12 at (0, 60 + 12 n); diamond 66 x 66 at (60, 60); square 64 x 64 at
  (0, 132); 貫 / 歳 / 死亡 at (64, 132 / 144 / 156); slot strips from y 196. Free (index 0): the rest.
  English sheet (CELLS): the skill names are whole words in 64-px cells, so the skill grid on the
  screen is 3 columns x 4 rows (tools/layout.py 'person detail gfx' + two CODE entries hold every
  constant; the cell positions there must agree with CELLS).

Yes / No buttons (可 / 否; KEEP.DAT, the resident sheet: palettes at 0, 384 x 248 picture at 8 bpp from
  0x1800, VRAM (576, 264))
  24 x 16 buttons at sheet (72, 32) 可, (72, 48) 否, and their pressed versions at x 96. Face = a
  dithered gradient (BTN_FACE colours), 1-px frame. The lettering is replaced, the face rebuilt
  from each row's own colours; nothing moves, so no code changes.

Battle organisation screen (WGRP.DAT, two colour variants (ORG_BLOCKS): 256-colour palette at 0x4d800 /
  0x64800, then a 320 x 240 background, 0x20 bytes, the button strip)
  The labels are painted into the background: ink in a palette index of its own (the commonest in the
  label's rect; it differs between the variants), shadow = the background at half brightness, right
  of and below the ink. They are erased (filled from the pixels around them) and written again in
  English. "Cannon" / "Morale" need 36 px where the Japanese had 32 between the value boxes, so the
  three left boxes lose their empty right 6 px (ORG_TRIM: the lightened pixels are darkened back).
  Buttons: a 128-px-wide strip at 4 bpp after each background (VRAM (480, 0)): five unit buttons 48 x 14
  from y 0, then 兵科 / 兵士数 36 x 14, automatic allocation 84 x 14, done 48 x 14, back 24 x 14.
  Same cells and sizes in English (ORG_BUTTONS), so no code changes.

Battle unit detail (View status -> Unit Info -> Circle; WGRP.DAT palette 0x27000, 320 x 240 at 0x27200)
  Every label is painted into the background: ink = a palette index >= 0xf1, shadow right / below =
  the background at DET_DARK brightness; the value boxes are the background darkened the same way
  (12 rows, corners cut by 1 px). Labels are erased and written in English at the same places; the
  skills are abbreviated (26 px before each icon slot). "Morale" / "Fatigue" need 37 px where the
  Japanese had 27 before the bars, so the bars and their numbers move 10 px right (tools/layout.py
  'battle unit detail gfx') and the number boxes are extended to the right (DET_BOXES).
  The age mark becomes "yr" after the number (no room for "Age" before it: long names end at 218).

Officer detail of the battle organisation screen (unit page -> Up -> Circle; WGRP.DAT palette 0x13800,
  320 x 240 at 0x13a00): same header and skill grid as the unit detail, ability names round the diamond.
  Ink = palette 0x78-0x7c (0x7d = gold lines). Same routine (_detail); "Diplomacy" is "Diplom." (43 px
  between the portrait frame and the diamond). No code changes.

Gambling board (tavern -> Gambling; BG.DAT palette 0x9cc000, 320 x 240 at 0x9cc200)
  Five panels with labels painted in: 賭札 (yellow, index 0xcc) + 枚 after the number box, 出目 (green,
  0xc5), and 持札 (pink, 0xc8 with a few 0xd1) in the player's panel; shadows right / below in dark greys. Erased and
  written as Bet / Roll / Held at the same places; the counter 枚 is dropped (the program draws
  "Dealer" over it in the dealer's panel).

Factions screen portraits (Triangle -> People -> Factions; code 0x8003c4b8..; RGRP.DAT 0x1fe000: 336 x 152 at
  8 bpp, VRAM (480, 0), palette = KEEP.DAT 0x800 (VRAM row 486))
  Seven 84 x 76 portraits, 4 per row: 木下 丹羽 林 佐久間 / 柴田 明智 羽柴 派, each with a vertical tag over
  its top-left corner (cols 0-18, rows 0-53; border 0xec, ink 0xe3, shadow 0x0d; 4-px frame 0xbd).
  The tag is erased (frame back to 0xbd, the picture filled from its neighbours) and a horizontal
  plaque in the same style with the family name sits at the bottom left. No code changes.

usage: python3 tools/gfx.py [preview.png]      (the redrawn sheet, 4x; needs pillow)
"""
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
import pixfont, text

RGRP = 'DATA/RGRP.DAT'
PIX, W, SHEET_X = 0x1e1a00, 448, 320
BG, SHADOW = 8, 0xf3
SKILLS = ['Accounting', 'Building', 'Development', 'Speech', 'Etiquette', 'Tea', 'Martial Arts', 'Riding',
          'Gunnery', 'Ninjutsu', 'Scheming', 'Tactics']


def skill_cell(j):
    """Sheet position of skill label j (the draw loop in layout.CODE computes the same)."""
    return (64, 132 + 12 * j) if j < 5 else (64 * ((j - 5) & 1), 12 * ((j - 5) >> 1))


# (text, x, y, w, old cell the ink colour is taken from (x, y, w), align)
CELLS = [(s, *skill_cell(j), 64, (24 * (j // 3), 12 * (j % 3), 24), 'l') for j, s in enumerate(SKILLS)] + [
    ('Domestic', 64, 36, 44, (0, 36, 36), 'l'), ('Military', 0, 48, 38, (36, 36, 36), 'l'),
    ('Diplomacy', 64, 48, 50, (0, 48, 36), 'l'), ('Charm', 60, 220, 32, (36, 48, 36), 'l'),
    ('Clan', 0, 60, 60, (0, 60, 60), 'l'), ('Castle', 0, 72, 60, (0, 72, 60), 'l'),
    ('Superior', 0, 84, 60, (0, 84, 60), 'l'), ('Faction', 0, 96, 60, (0, 96, 60), 'l'),
    ('Merit', 0, 108, 60, (0, 108, 60), 'l'), ('Stipend', 0, 120, 60, (0, 120, 60), 'l'),
    ('kan', 88, 208, 18, (64, 132, 12), 'l'), ('Age', 106, 208, 20, (64, 144, 12), 'l'),
    ('Dead', 80, 196, 26, (64, 156, 24), 'l'),
]
OLD = [(0, 0, 96, 36), (0, 36, 72, 24), (64, 132, 24, 36)]       # Japanese cells that are not reused: cleared


def _ink(d, x, y, w):
    n = {}
    for j in range(12):
        for v in d[PIX + (y + j) * W + SHEET_X + x:PIX + (y + j) * W + SHEET_X + x + w]:
            if v not in (BG, SHADOW, 0):
                n[v] = n.get(v, 0) + 1
    return max(n, key=n.get)


def sheet(data):
    """RGRP.DAT with the English label sheet."""
    d = bytearray(data)
    G = pixfont.glyphs()
    inks = [_ink(data, *c[4]) for c in CELLS]

    def put(x, y, v):
        d[PIX + y * W + SHEET_X + x] = v

    for x, y, w, h in OLD:
        for j in range(h):
            for i in range(w):
                put(x + i, y + j, 0)
    for (s, x0, y0, w, _, al), ink in zip(CELLS, inks):
        assert x0 % 2 == 0 and x0 + w <= 128, s
        n = text.width(s)
        assert n + 1 <= w, '%s: %d px in a %d px cell' % (s, n + 1, w)
        for j in range(12):
            for i in range(w):
                put(x0 + i, y0 + j, BG)
        pts, x = [], x0
        for ch in s.translate(text.FOLD):
            rows, adv = G[ch]
            pts += [(x + i, y0 + j) for j in range(12) for i in range(8) if rows[j] & (0x80 >> i)]
            x += adv
        for a, b in pts:
            for da, db in ((1, 0), (0, 1), (1, 1)):
                if a + da < x0 + w and b + db < y0 + 12:
                    put(a + da, b + db, SHADOW)
        for a, b in pts:
            put(a, b, ink)
    return bytes(d)


KEEP = 'DATA/KEEP.DAT'
KPIX, KW = 0x1800, 384
# (text, x, y, face colours, ink, shadow, pressed)
BTN_UP = {0x65, 0x69, 0x54, 0x4d, 0x4f, 0x4c, 0x52, 0x56, 0x6a, 0x4e, 0x4a}
BTN_DOWN = {0x57, 0x3c, 0x44, 0x37, 0x42, 0x43, 0x45, 0x3b, 0x41, 0x5a, 0x3f}
BUTTONS = [('Yes', 72, 32, BTN_UP, 0x98, 0x53, 0), ('No', 72, 48, BTN_UP, 0x98, 0x53, 0),
           ('Yes', 96, 32, BTN_DOWN, 0x76, 0x38, 1), ('No', 96, 48, BTN_DOWN, 0x76, 0x38, 1)]


def buttons(data):
    """KEEP.DAT with English Yes / No buttons."""
    d = bytearray(data)
    G = pixfont.glyphs()
    for s, bx, by, face, ink, shadow, down in BUTTONS:
        for j in range(1, 15):                                  # rebuild the face under the old lettering
            o = KPIX + (by + j) * KW + bx
            row = d[o:o + 24]
            ok = [i for i in range(2, 22) if row[i] in face]
            assert len(ok) >= 6, (s, j)
            for i in range(2, 22):
                if row[i] not in face:                          # nearest face pixel of the same dither phase
                    d[o + i] = row[min(ok, key=lambda k: (abs(k - i) + 100 * ((k - i) & 1)))]
        x = bx + 1 + (22 - text.width(s) + 1) // 2 + down
        y = by + 3 + down
        pts = []
        for ch in s:
            rows, adv = G[ch]
            pts += [(x + i, y + j) for j in range(12) for i in range(8) if rows[j] & (0x80 >> i)]
            x += adv
        sh = (-1, -1) if down else (1, 1)                       # raised: shadow below right; pressed: above left
        for a, b in pts:
            d[KPIX + (b + sh[1]) * KW + a + sh[0]] = shadow
        for a, b in pts:
            d[KPIX + b * KW + a] = ink
    return bytes(d)


WGRP = 'DATA/WGRP.DAT'
ORG_BLOCKS, ORG_W = (0x4d800, 0x64800), 320           # palette; picture at + 0x200, strip at + 0x12e20
# (text, old rect x0 y0 x1 y1, ink index in the brown variant, new x, align: l = starts at x, r = ends at x,
# c = centred on x)
ORG_LABELS = [
    ('Rice', (169, 21, 203, 31), 0xfd, 169, 'l'), ('Funds', (169, 36, 203, 46), 0xfb, 169, 'l'),
    ('Fatigue', (169, 52, 203, 62), 0xfd, 169, 'l'),
    ('Cannon', (259, 21, 281, 31), 0xfb, 249, 'l'), ('Drill', (259, 37, 281, 47), 0xfd, 249, 'l'),
    ('Morale', (258, 52, 280, 62), 0xfb, 249, 'l'),
    ('Unassigned', (214, 73, 250, 83), 0xed, 232, 'c'), ('Total', (267, 73, 301, 83), 0xed, 284, 'c'),
    ('Troops', (177, 89, 210, 99), 0xd0, 211, 'r'), ('Horses', (178, 105, 209, 115), 0xe4, 211, 'r'),
    ('Guns', (178, 121, 209, 131), 0xd0, 211, 'r'),
]
ORG_TRIM = [(247, 254, 18, 34), (247, 254, 34, 50), (247, 254, 50, 66)]     # x0, x1, y0, y1: box pixels -> background
ORG_BTN_W = 128
# (text, y, width, face, (ink colours), shadow, new ink)
ORG_BUTTONS = [('Unit %d' % (n + 1), 14 * n, 48, 3, (0xc,), 5, 0xc) for n in range(5)] + [
    ('Type', 70, 36, 3, (0xc,), 5, 0xc), ('Men', 84, 36, 3, (0xc,), 5, 0xc),
    ('Auto-assign', 98, 84, 4, (0xa, 9), 6, 0xa), ('End', 112, 48, 4, (0xa, 9), 6, 0xa),
    ('Back', 126, 24, 4, (0xd, 0xb), 6, 0xd),
]


def _pts(s, x, y):
    G = pixfont.glyphs()
    pts = []
    for ch in s.translate(text.FOLD):
        rows, adv = G[ch]
        pts += [(x + i, y + j) for j in range(12) for i in range(8) if rows[j] & (0x80 >> i)]
        x += adv
    return pts


def organisation(data):
    """WGRP.DAT with the English battle organisation backgrounds and buttons."""
    d = bytearray(data)
    for pal in ORG_BLOCKS:
        _organisation(d, data, pal, pal + 0x200, pal + 0x12e20)
    return bytes(d)


def _organisation(d, data, ORG_PAL, ORG_PIX, ORG_BTN):
    import struct
    pal = [(v & 31, v >> 5 & 31, v >> 10 & 31) for v in struct.unpack_from('<256H', data, ORG_PAL)]

    def at(x, y):
        return ORG_PIX + y * ORG_W + x

    # 1. erase the Japanese labels: ink and shadow pixels are filled from their surroundings
    hole, inks = set(), []
    for s, (x0, y0, x1, y1), ink, _, _ in ORG_LABELS:
        n = {}
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                n[d[at(x, y)]] = n.get(d[at(x, y)], 0) + 1
        ink = max(n, key=n.get) if ORG_PAL != ORG_BLOCKS[-1] else ink
        assert n.get(ink, 0) > 60, s
        inks.append(ink)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if d[at(x, y)] == ink:                          # the shadow is right of / below the ink
                    hole |= {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}
    plain = [i for i in range(256) if i not in inks and max(pal[i]) - min(pal[i]) <= 10]   # background colours
    while hole:
        done = {}
        for x, y in hole:
            c = [(x + a, y + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (x + a, y + b) not in hole]
            if c:
                done[x, y] = d[at(*c[(x * 7 + y * 13) % len(c)])]
        assert done
        for (x, y), v in done.items():
            d[at(x, y)] = v
        hole -= set(done)

    # 2. the left value boxes end 6 px earlier: lightened pixels back to the background's level
    def lum(i):
        return sum(pal[i])
    for x0, x1, y0, y1 in ORG_TRIM:
        for y in range(y0, y1):
            ref = (lum(d[at(x1 + 1, y)]) + lum(d[at(x1 + 2, y)])) / 2
            if lum(d[at(x0 - 3, y)]) - ref < 6:
                continue                                        # not a box row
            below, above = lum(d[at(x0 - 3, y + 1)]) - lum(d[at(x1 + 2, y + 1)]) >= 6, \
                lum(d[at(x0 - 3, y - 1)]) - lum(d[at(x1 + 2, y - 1)]) >= 6
            for x in range(x0 + (below and above), x1 + 1):     # rounded: corner rows end 1 px earlier
                r, g, b = pal[d[at(x, y)]]
                if r + g + b - ref < 6:
                    continue
                t = (r - 4, g - 4, b - 4)
                d[at(x, y)] = min(plain, key=lambda i: sum((p - q) ** 2 for p, q in zip(pal[i], t)))

    # 3. English labels
    def half(i):
        t = [c / 2 for c in pal[i]]
        return min(plain, key=lambda k: sum((p - q) ** 2 for p, q in zip(pal[k], t)))

    for (s, (x0, y0, x1, y1), _, x, al), ink in zip(ORG_LABELS, inks):
        n = text.width(s)
        x = x if al == 'l' else x - n if al == 'r' else x - n // 2
        pts = set(_pts(s, x, y0))
        for q in {(a + da, b + db) for a, b in pts for da, db in ((1, 0), (0, 1), (1, 1))} - pts:
            d[at(*q)] = half(d[at(*q)])
        for a, b in pts:
            d[at(a, b)] = ink

    # 4. buttons (4 bpp strip)
    def get(x, y):
        return d[ORG_BTN + y * (ORG_BTN_W // 2) + x // 2] >> (4 * (x & 1)) & 15

    def put(x, y, v):
        o = ORG_BTN + y * (ORG_BTN_W // 2) + x // 2
        d[o] = d[o] & (0xf0 >> (4 * (x & 1))) | v << (4 * (x & 1))

    for s, by, w, face, old, shadow, ink in ORG_BUTTONS:
        assert sum(get(x, by + 6) in old for x in range(w)) > 3, s
        for y in range(by + 1, by + 13):
            for x in range(1, w - 1):
                if get(x, y) in old or get(x, y) == shadow:
                    put(x, y, face)
        n = text.width(s)
        assert n <= w - 2, s
        pts = _pts(s, max(2, (w - n + 1) // 2), by + 2)
        for a, b in pts:
            for da, db in ((1, 0), (0, 1), (1, 1)):
                if a + da < w - 1:
                    put(a + da, b + db, shadow)
        for a, b in pts:
            put(a, b, ink)


DET_PAL, DET_PIX, DET_DARK = 0x27000, 0x27200, 0.7
# (text, old rect x0 y0 x1 y1, x, align (l = starts at x, r = ends before x), cell top)
DET_LABELS = [
    ('yr', (233, 19, 248, 31), 235, 'l', 20),
    ('Type', (162, 44, 188, 57), 164, 'l', 44), ('Men', (162, 60, 188, 73), 164, 'l', 60),
    ('Drill', (162, 76, 188, 89), 164, 'l', 76), ('Morale', (162, 92, 188, 105), 164, 'l', 92),
    ('Fatigue', (162, 108, 188, 121), 164, 'l', 108),
    ('Domestic', (174, 128, 211, 141), 213, 'r', 128), ('Diplomacy', (174, 144, 211, 157), 213, 'r', 144),
    ('Military', (238, 128, 275, 141), 275, 'r', 128), ('Charm', (238, 144, 275, 157), 275, 'r', 144),
] + [(s, (22 + 68 * (j // 3), 164 + 16 * (j % 3), 48 + 68 * (j // 3), 177 + 16 * (j % 3)),
      24 + 68 * (j // 3), 'l', 164 + 16 * (j % 3))
     for j, s in enumerate(['Acct', 'Build', 'Dev', 'Talk', 'Etiq', 'Tea', 'Arms', 'Ride', 'Guns', 'Ninja', 'Plot', 'Tact'])]
# value boxes extended to the right: (first new x, last new x, top row, bottom row)
DET_BOXES = [(229, 244, 44, 55), (307, 312, 60, 71), (295, 304, 76, 87), (295, 304, 92, 103), (295, 304, 108, 119)]


def _detail(data, DET_PAL, DET_PIX, DET_LABELS, DET_BOXES, isink, nplain):
    """A 320 x 240 detail background with its labels (DET_LABELS format) erased and written in English."""
    import struct
    d = bytearray(data)
    pal = [(v & 31, v >> 5 & 31, v >> 10 & 31) for v in struct.unpack_from('<256H', data, DET_PAL)]
    plain = [i for i in range(nplain) if max(pal[i]) - min(pal[i]) <= 6]

    def at(x, y):
        return DET_PIX + y * 320 + x

    def dark(i):
        t = [c * DET_DARK for c in pal[i]]
        return min(plain, key=lambda k: sum((p - q) ** 2 for p, q in zip(pal[k], t)))

    hole, inks = set(), []
    for s, (x0, y0, x1, y1), _, _, _ in DET_LABELS:
        n = {}
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if isink(d[at(x, y)]):
                    n[d[at(x, y)]] = n.get(d[at(x, y)], 0) + 1
        ink = max(n, key=n.get)
        assert n[ink] > 40 and len(n) == 1, (s, n)
        inks.append(ink)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if d[at(x, y)] == ink:
                    hole |= {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}
    while hole:
        done = {}
        for x, y in hole:
            c = [(x + a, y + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (x + a, y + b) not in hole]
            if c:
                done[x, y] = d[at(*c[(x * 7 + y * 13) % len(c)])]
        assert done
        for (x, y), v in done.items():
            d[at(x, y)] = v
        hole -= set(done)

    for x0, x1, y0, y1 in DET_BOXES:
        for y in range(y0, y1 + 1):
            edge = y in (y0, y1)
            for x in range(x0 - edge, x1 + 1 - edge):           # the old corner is filled, the new one cut
                d[at(x, y)] = dark(d[at(x, y)])

    for (s, _, x, al, y0), ink in zip(DET_LABELS, inks):
        n = text.width(s)
        pts = set(_pts(s, x if al == 'l' else x - n - 1, y0))
        for q in {(a + da, b + db) for a, b in pts for da, db in ((1, 0), (0, 1), (1, 1))} - pts:
            d[at(*q)] = dark(d[at(*q)])
        for a, b in pts:
            d[at(a, b)] = ink
    return bytes(d)


def unit_detail(data):
    """WGRP.DAT with the English battle unit detail background."""
    return _detail(data, DET_PAL, DET_PIX, DET_LABELS, DET_BOXES, lambda v: v >= 0xf1, 0xf1)


# Officer detail of the battle organisation screen (unit page -> portrait): palette 0x13800, 320 x 240 at
# 0x13a00, one copy. Label inks = palette 0x78-0x7c (0x7d = the gold lines). Same header and skill grid as the
# unit detail; ability names round the diamond ("Diplomacy" is 48 px for the 43 px between the portrait
# frame and the diamond: "Diplom.").
OFF_PAL, OFF_PIX = 0x13800, 0x13a00
OFF_LABELS = [
    ('yr', (233, 19, 248, 31), 235, 'l', 20),
    ('Domestic', (218, 47, 256, 60), 216, 'l', 47), ('Diplom.', (169, 89, 206, 102), 206, 'r', 89),
    ('Military', (270, 89, 310, 102), 273, 'l', 89), ('Charm', (218, 131, 256, 144), 222, 'l', 131),
] + DET_LABELS[10:]


def officer_detail(data):
    """WGRP.DAT with the English officer detail background of the battle organisation screen."""
    return _detail(data, OFF_PAL, OFF_PIX, OFF_LABELS, [], lambda v: 0x78 <= v <= 0x7c, 0x78)


BGF = 'DATA/BG.DAT'
GAM_PAL, GAM_PIX, GAM_INKS, GAM_DARK = 0x9cc000, 0x9cc200, (0xcc, 0xc5, 0xc8, 0xd1), 0.4
GAM_PANELS = [(16, 48, 88, 92), (232, 48, 304, 92), (16, 136, 88, 180), (232, 136, 304, 180), (128, 168, 224, 228)]
# (text, ink, x, cell top)
GAM_LABELS = [(s, i, x + 23, y + 55 + 16 * r) for x, y in ((0, 0), (216, 0), (0, 88), (216, 88))
              for r, (s, i) in enumerate((('Bet', 0xcc), ('Roll', 0xc5)))] + [
    ('Held', 0xc8, 135, 175), ('Bet', 0xcc, 135, 191), ('Roll', 0xc5, 135, 207)]


def gamble(data):
    """BG.DAT with the English gambling board."""
    import struct
    d = bytearray(data)
    pal = [(v & 31, v >> 5 & 31, v >> 10 & 31) for v in struct.unpack_from('<256H', data, GAM_PAL)]
    plain = [i for i in range(256) if max(pal[i]) - min(pal[i]) <= 2]

    def at(x, y):
        return GAM_PIX + y * 320 + x

    def dark(i):
        t = [c * GAM_DARK for c in pal[i]]
        return min(plain, key=lambda k: sum((p - q) ** 2 for p, q in zip(pal[k], t)))

    hole = set()
    for x0, y0, x1, y1 in GAM_PANELS:
        for y in range(y0, y1):
            for x in range(x0, x1):
                if d[at(x, y)] in GAM_INKS:
                    hole |= {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}
    assert len(hole) > 2000, len(hole)
    while hole:
        done = {}
        for x, y in hole:
            c = [(x + a, y + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (x + a, y + b) not in hole]
            if c:
                done[x, y] = d[at(*c[(x * 7 + y * 13) % len(c)])]
        assert done
        for (x, y), v in done.items():
            d[at(x, y)] = v
        hole -= set(done)
    for s, ink, x, y0 in GAM_LABELS:
        pts = set(_pts(s, x, y0))
        for q in {(a + da, b + db) for a, b in pts for da, db in ((1, 0), (0, 1), (1, 1))} - pts:
            d[at(*q)] = dark(d[at(*q)])
        for a, b in pts:
            d[at(a, b)] = ink
    return bytes(d)


FAC_PIX, FAC_W = 0x1fe000, 336
FAC_TAG = (19, 54)                  # the Japanese tag: cols 0-18 (border 17, shadow 18), rows 0-53
FAC_FRAME, FAC_BORDER, FAC_SHADOW, FAC_INK = 0xbd, 0xec, 0x0d, 0xe3
FAC_NAMES = ['Kinoshita', 'Niwa', 'Hayashi', 'Sakuma', 'Shibata', 'Akechi', 'Hashiba']
FAC_Y = 59                          # top of the English plaque (16 rows + 1 shadow row = the portrait's last row)


def factions(data):
    """RGRP.DAT with the English faction portraits (vertical tag -> plaque at the bottom left)."""
    d = bytearray(data)
    tw, th = FAC_TAG
    for p, name in enumerate(FAC_NAMES):
        ox, oy = 84 * (p & 3), 76 * (p >> 2)

        def at(x, y):
            return FAC_PIX + (oy + y) * FAC_W + ox + x
        assert all(d[at(x, 52)] == FAC_BORDER for x in range(3, 16)), p
        fill = [d[at(x, y)] for y in range(2, 51) for x in range(2, 16)
                if d[at(x, y)] not in (FAC_BORDER, FAC_SHADOW, FAC_INK)]
        # 1. erase the tag: the 4-px frame back to its colour, the picture filled from its neighbours
        hole = set()
        for y in range(th):
            for x in range(tw):
                if x < 4 or y < 4:
                    d[at(x, y)] = FAC_FRAME
                else:
                    hole.add((x, y))
        while hole:
            done = {}
            for x, y in hole:
                c = [(x + a, y + b) for a in (-1, 0, 1) for b in (-1, 0, 1)
                     if (a or b) and x + a >= 4 and y + b >= 4 and (x + a, y + b) not in hole]
                if c:
                    done[x, y] = d[at(*c[(x * 7 + y * 13) % len(c)])]
            assert done
            for (x, y), v in done.items():
                d[at(x, y)] = v
            hole -= set(done)
        # 2. plaque: textured fill, 1-px border with cut corners, shadow right / below, name centred
        n = text.width(name)
        w, y0 = n + 10, FAC_Y
        for y in range(16):
            for x in range(w):
                edge = x in (0, w - 1) or y in (0, 15)
                corner = (x in (0, w - 1)) and (y in (0, 15))
                if corner:
                    continue
                d[at(x, y0 + y)] = FAC_BORDER if edge else fill[(x * 7 + y * 13 + p) % len(fill)]
        for y in range(1, 17):
            d[at(w, y0 + y)] = FAC_SHADOW
        for x in range(1, w):
            d[at(x, y0 + 16)] = FAC_SHADOW
        for a, b in _pts(name, 5, y0 + 2):
            d[at(a, b)] = FAC_INK
    return bytes(d)


def patch(files, clean):
    """files: {name: bytes} of the build; clean(name) -> the original file."""
    files[RGRP] = factions(sheet(files.get(RGRP) or clean(RGRP)))
    files[KEEP] = buttons(files.get(KEEP) or clean(KEEP))
    files[WGRP] = officer_detail(unit_detail(organisation(files.get(WGRP) or clean(WGRP))))
    files[BGF] = gamble(files.get(BGF) or clean(BGF))
    return len(CELLS) + len(BUTTONS) + len(ORG_BLOCKS) * (len(ORG_LABELS) + len(ORG_BUTTONS)) + len(DET_LABELS) \
        + len(OFF_LABELS) + len(GAM_LABELS) + len(FAC_NAMES)


if __name__ == '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dev'))
    import rawgfx
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = sheet(open(os.path.join(root, 'extract', RGRP), 'rb').read())
    im = rawgfx.image(d, 0x1e1800, PIX, W, 256).crop((SHEET_X, 0, W, 256))
    im = im.resize((im.width * 4, im.height * 4), 0)
    im.save(sys.argv[1] if len(sys.argv) > 1 else 'build/gfx/detail_sheet_en.png')

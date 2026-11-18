"""Translation helper for DATA/MESSAGE.DAT: show the Japanese as units, check + wrap + insert the English.

Units. A string is cut into pages: [z f s] body [g v j y] (msgfile.py has the codes). A page whose only
ending is a `j` to a string that starts without `z` and has no other referrer continues there (item
descriptions, biographies): the chain is one unit. Only the body is translated; the codes around it stay.
Units with the same Japanese body share one translation: the first one in file order (the canonical unit)
carries it, `show` marks the others `= block.n` and they need no entry (an entry of their own wins).

tl/msgNN.txt (NN = block) holds our English only:

    # comment
    @<n>            page 0 of string n            @<n>.<k>   page k of string n
    English text, over any number of lines (joined with spaces).

  \\n          forced line break
  {s}          plural "s": not printed when the number insert before it is 1 ("{b00} day{s}"); it must
               be in the word right after the number
  \\_          a space that is kept (indent at the start of a line: 3 px each)
  =           (whole entry) keep the Japanese
  {a660000} {p00} {b00} {e..} = inserts (name / string / number); copy them from `show`. {w} pause,
  {c02}..{c09} colour, {d..} as shown. They may move; an insert may be dropped but not invented.
  Japanese `|` in `show` is a line break: do not copy it, English is wrapped by the tool.

Wrap: by pixels with our font (text.py / pixfont.py) and worst-case widths for inserts. Message-window
units (window.py: 272 px, 3 lines a page; 4 when the Japanese has 4) may run over: the tool adds pages (wait for a
button, clear, same speaker) and continues in a new string at the end of the block when a string passes
the interpreter's 200 bytes. Other units (no `z`) must fit their box, shown by `show` as `box 216px x5`
(up to 5 lines, wrapped by the tool) or `box 200px =2` (exactly 2 lines: a choice menu, one option a line,
separated with \\n). `panel()` has the boxes.

usage:
    tl.py show NN [from] [to] [--todo] [--en] [--dups]   Japanese units (with --en: the English under each)
    tl.py dump                     script/msgNN.txt for every block (git-ignored Japanese, for workers)
    tl.py apply NN [batch.txt]     merge a batch into tl/msgNN.txt after checking it
    tl.py check [NN]               check every entry (codes, widths, block sizes)
    tl.py stats                    progress per block
"""
import collections, os, re, struct, sys

sys.path.insert(0, os.path.dirname(__file__))
import msgfile, msgpack, pixfont, softwrap, text, window

ROOT = msgfile.ROOT
TL = os.path.join(ROOT, 'tl')
SCRIPT = os.path.join(ROOT, 'script')

MENU_PX = 200                     # boxes sized to their text (choices, speech bubbles): our own limit


def panel(block, n, jp):
    """-> (width px, lines, exact line count) of a unit without `z`; jp = px of its Japanese lines.
    Boxes set by 0x8007c720 (left, top, width, height): item help 0x8003ce68, help topics 0x8003d310
    (title at y, 3 lines under it, 64 px a topic), biography 0x8003ae44. Rule lists: MAPPOINT 0x8014ead8.
    Everything else is a box sized to its text (0x8007ba80): script choices (one option a line), gambling
    and council speech."""
    if block == 24 and n < 400:
        return 216, 5, False                      # reading + description: the English is description only
    if block == 24 and n >= 520:
        return 240, 3 if n & 1 else 1, False
    if block == 25:
        return 288, 3, False
    if block in (3, 18) and 116 <= n <= 142:
        return 276, 1, False                      # one string a line, 36-cell window
    if block == 0 and (76 <= n <= 95 or 110 <= n <= 114):
        return 52, 2, False                       # council vote bubbles: fixed size, 5 cells x 2 lines ("No
                                                  # objection", 59 px, wrapped inside a word)
    return max(max(jp), MENU_PX), len(jp), len(jp) > 1


STRING_BYTES = msgfile.STRING_MAX - 1
# worst-case widths of inserts, px. a: `names.py check`; e = castle (`tables.py check`: 89 px, + " Castle" 33
# unless the type is `s`); b = number (6 px a digit); p = any string: guessed from the Japanese after it.
VAR_PX = {'a': {0x73: 61, 0x6d: 87}, 'e': {0x73: 89}, 'b': 36}
A_FULL_PX = 114
E_FULL_PX = 89 + 33
P_PX = 122                        # unknown kind: the widest thing a `p` can be (castle + " Castle")
P_AFTER = (('の城', 89), ('城', 89), ('さま', A_FULL_PX), ('様', A_FULL_PX), ('殿', A_FULL_PX), ('どの', A_FULL_PX),
           ('家', 61), ('の国', 54), ('国', 54), ('地方', 54), ('派', 61))
# real widths for the inserts of one English text (wins over the guesses of insert_px): {text: {insert: px}}
EN_PX = {
    # 6 @155 (+ the variant blocks): p02 = gift category (Arms / Art / Books / Sake / Medicine), p03 = drinker
    # fragment of MAPPOINT 0x801504e0.. ("a man who does not drink" is the widest)
    "{p00}{p01}... let me see... He likes {p02}, and he's {p03}.": {b'p\x02': 48, b'p\x03': 124},
    # session 33: lines seen breaking early in play. Mission name (widest command "Warrior Training" 79 px),
    # merit fragment MAPPOINT 0x8014fc64 ("rose by %d" / "did not rise"), days (2 digits), gun stock / price, gift value
    "If I remember rightly, {a6600eb} said Nanban medicine works.": {b'a\x66\x00\xeb': 43},
    "Yes. I have completed the {p00} mission.": {b'p\x00': 80},
    "Mission result reported. {p00}'s merit rose by {b00}. {a660000}'s merit {p01}.": {b'b\x00': 18, b'p\x01': 58},
    "Mission result reported. {p00}'s merit {p01}. {a660000}'s merit rose by {b00}.": {b'b\x00': 18, b'p\x01': 58},
    "Mission result reported. {p00}'s merit rose by {b00}. {a660000}'s merit rose by {b01}.": {b'b\x00': 18, b'b\x01': 18},
    "Days to {p00}: {b00}. Move there?": {b'b\x00': 12},
    "Days to {p00}: {b00}. Return there?": {b'b\x00': 12},
    "{p00}? We have {b01} at {b00} kan each.": {b'p\x00': 40, b'b\x00': 24, b'b\x01': 24},
    "Given this{p00}'s standing, a gift below value {b00} would be rude.": {b'p\x00': 37, b'b\x00': 12},
    "Given this{p00}'s standing, a gift below value {b00} would be rude. But I have nothing worth that much.": {b'p\x00': 37, b'b\x00': 12},
    "Given this{p00}'s standing, a gift below value {b00} would be rude. But I have nothing worth that much now.": {b'p\x00': 37, b'b\x00': 12},
    # session 35: council promotion lines (0 @45-@56, @205-@207). Rank = class word 0x8008e7b8 (widest
    # "Ashigaru Capt." 70 px); @56 p00 / p01 = given names (87 px)
    "There are men eligible for the rank of {p00} here. Whom shall I recommend?": {b'p\x00': 70},
    "My lord!! {p00}{p01} has served splendidly. I consider the rank of {p02} his due.": {b'p\x02': 70},
    "If I may speak, my lord. The service of {p00}{p01} has been truly remarkable. The rank of {p02} befits him.": {b'p\x02': 70},
    "Forgive my presumption, my lord. {p00}{p01} has served so well that I think the rank of {p02} is deserved.": {b'p\x02': 70},
    "{p00} speaks well! {p01}! From now on you hold the rank of {p02}, so serve us well!": {b'p\x00': 87, b'p\x01': 87, b'p\x02': 70},
    "{p00}, I raise you to the rank of {p01} and count on you from now on.": {b'p\x00': 87, b'p\x01': 70},
    "{p00}, your recent service has been splendid. The rank of {p01} is yours for it.": {b'p\x00': 87, b'p\x01': 70},
    "{p00}. From now on, the rank of {p01} is yours.": {b'p\x00': 87, b'p\x01': 70},
}
INSERTS = 'aepb'
FREE = 'wcd'                      # codes the English may add or drop

Page = collections.namedtuple('Page', 'pre body suf')


def ser(toks):
    out = b''
    for k, v in toks:
        out += v.encode('cp932') if k == 't' else b'\x1b' + v if k == 'ESC' else k.encode() + v
    return out


def show_toks(toks):
    return ''.join(v if k == 't' else '|' if k == 'n' else '{%s%s}' % (k, v.hex()) for k, v in toks)


def split_pages(toks):
    pages, cur, state = [], Page([], [], []), 0
    for t in toks:
        k = t[0]
        if state == 0 and k in 'zfs' and k != 't':
            cur.pre.append(t)
        elif k in 'gvjy' and k != 't':
            cur.suf.append(t); state = 2
        elif state == 2 or (state == 1 and k in 'zfs' and k != 't'):
            pages.append(cur); cur = Page([], [], [])
            if k in 'zfs' and k != 't':
                cur.pre.append(t); state = 0
            else:
                cur.body.append(t); state = 1
        else:
            cur.body.append(t); state = 1
    if cur.pre or cur.body or cur.suf or not pages:
        pages.append(cur)
    return pages


class Unit:
    """One translatable page: block, string n, page k; `members` = the strings of its chain."""
    def __init__(self, block, n, k, page):
        self.block, self.n, self.k = block, n, k
        self.pre, self.body, self.suf = list(page.pre), list(page.body), list(page.suf)
        self.tail_n = 0

    @property
    def key(self):
        return (self.n, self.k)

    @property
    def name(self):
        return '%d' % self.n if not self.k else '%d.%d' % (self.n, self.k)

    def has_text(self):
        return any(k == 't' and any(ord(c) > 0x7F for c in v) for k, v in self.body)

    def window(self):
        return any(k == 'z' for k, v in self.pre)

    def jp_lines(self):
        lines = [0]
        for k, v in self.body:
            if k == 'n':
                lines.append(0)
            elif k == 't':
                lines[-1] += sum(12 if ord(c) > 0x7F else 6 for c in v)
            elif k in INSERTS:
                lines[-1] += 36
        return lines

    def box(self):
        """(width px, lines per page, may add pages)"""
        jp = self.jp_lines()
        if self.window():
            return window.WIDTH, min(max(window.LINES, len(jp)), window.MAX_LINES), True
        return panel(self.block, self.n, jp)[:2] + (False,)

    def exact(self):
        """a box where every line is an item (choice menu): the English needs the same number of lines"""
        return not self.window() and panel(self.block, self.n, self.jp_lines())[2]


class Group:
    """A head string with the strings merged into it; units = its pages."""
    def __init__(self, members, units):
        self.members, self.units = members, units


def load_block(b, strs):
    """-> list of Group for a block (file order)."""
    toks = [msgfile.tokens(s)[0] for s in strs]
    pages = [split_pages(t) for t in toks]
    for n, s in enumerate(strs):
        assert s.startswith(b''.join(ser(p.pre) + ser(p.body) + ser(p.suf) for p in pages[n]) + b'\0'), (b, n)
    refs = collections.Counter()
    for t in toks:
        for k, v in t:
            if k == 'j':
                refs[struct.unpack('>H', v)[0]] += 1
            elif k == 'y':
                refs[struct.unpack('>H', v[1:3])[0]] += 1; refs[struct.unpack('>H', v[3:5])[0]] += 1
    merged, groups = set(), []
    for n in range(len(strs)):
        if n in merged:
            continue
        members, units = [n], [Unit(b, n, k, p) for k, p in enumerate(pages[n])]
        while True:
            last = units[-1]
            if len(last.suf) != 1 or last.suf[0][0] != 'j':
                break
            m = struct.unpack('>H', last.suf[0][1])[0]
            if m >= len(strs) or m <= n or m in merged or refs[m] != 1 or pages[m][0].pre:
                break
            first = pages[m][0]
            last.body += first.body; last.suf = list(first.suf)
            units += [Unit(b, n, len(units) + i, p) for i, p in enumerate(pages[m][1:])]
            members.append(m); merged.add(m)
        for u in units:
            while u.body and u.body[-1][0] == 'n':
                u.body.pop(); u.tail_n += 1
        groups.append(Group(members, units))
    return groups


_cache = {}


def game():
    """-> (clean MESSAGE.DAT, [block -> strings], [block -> groups], canonical unit of each body)"""
    if not _cache:
        data = open(msgfile.PATH, 'rb').read()
        strs = [msgfile.strings(blk) for blk in msgfile.blocks(data)]
        groups = [load_block(b, s) for b, s in enumerate(strs)]
        canon = {}
        for gs in groups:
            for g in gs:
                for u in g.units:
                    if u.has_text():
                        canon.setdefault(ser(u.body), u)
        _cache['g'] = (data, strs, groups, canon)
    return _cache['g']


# ---- tl files

def tl_path(b):
    return os.path.join(TL, 'msg%02d.txt' % b)


def parse_tl(textdata, where=''):
    out, key, buf = {}, None, []
    def flush():
        if key is not None:
            out[key] = ' '.join(x.strip() for x in buf if x.strip())
    for i, line in enumerate(textdata.splitlines(), 1):
        if line.startswith('#'):
            continue
        m = re.match(r'@(\d+)(?:\.(\d+))?\s*$', line)
        if m:
            flush(); key, buf = (int(m.group(1)), int(m.group(2) or 0)), []
        elif key is None:
            if line.strip():
                raise ValueError('%s line %d: text before the first @entry' % (where, i))
        else:
            buf.append(line)
    flush()
    return out


_tl = {}


def load_tl(b):
    if b not in _tl:
        p = tl_path(b)
        _tl[b] = parse_tl(open(p, encoding='utf-8').read(), p) if os.path.exists(p) else {}
    return _tl[b]


def save_tl(b, entries):
    os.makedirs(TL, exist_ok=True)
    with open(tl_path(b), 'w', encoding='utf-8') as f:
        for (n, k) in sorted(entries):
            f.write('@%d%s\n%s\n' % (n, '.%d' % k if k else '', entries[(n, k)]))
    _tl[b] = entries


def english(u):
    """-> the English of a unit (own entry, else its canonical unit's), or None."""
    e = load_tl(u.block).get(u.key)
    if e is None:
        c = game()[3].get(ser(u.body))
        if c is not None and c is not u:
            e = load_tl(c.block).get(c.key)
    return e


# ---- English -> bytes

CODE = re.compile(r'(\{[^}]*\}|\\n|\\_|%s)')
PCT_PX = 52          # literal %s (sprintf before the interpreter: 0 @110-@112) = a given name; a second one
                     # right after it is the honorific fragment, which prints nothing


def insert_px(body):
    """-> {insert bytes: worst-case px} for the inserts of a Japanese body (`p` by what follows it)."""
    out = {}
    for i, (k, v) in enumerate(body):
        if k == 'a':
            px = VAR_PX['a'].get(v[0], A_FULL_PX)
        elif k == 'e':
            px = VAR_PX['e'].get(v[0], E_FULL_PX)
        elif k == 'b':
            px = VAR_PX['b']
        elif k == 'p':
            nxt = body[i + 1][1] if i + 1 < len(body) and body[i + 1][0] == 't' else ''
            px = next((w for suffix, w in P_AFTER if nxt.startswith(suffix)), P_PX)
            if i + 1 < len(body) and body[i + 1][0] == 'p':
                px = A_FULL_PX                    # {p00}{p01} = a person + the honorific fragment
            elif i and body[i - 1][0] == 'p':
                px = 0                            # ... which prints nothing (progstr 03_sdata: さま / 殿)
        else:
            continue
        key = k.encode() + v
        out[key] = max(out.get(key, 0), px)
    return out


def atoms(en, widths=None):
    """English -> list of (bytes, px, kind): kind 'c' glyph / code, ' ' space, 'n' forced break."""
    widths = widths or {}
    g, out = pixfont.glyphs(), []
    for part in CODE.split(en):
        if not part:
            continue
        if part == '\\n':
            out.append((b'', 0, 'n'))
        elif part == '\\_':
            out.append((b' ', g[' '][1], 'c'))
        elif part == '%s':                        # kept raw: text.enc would hide the conversion from sprintf
            out.append((b'%s', 0 if out and out[-1][0] == b'%s' else PCT_PX, 'c'))
        elif part == '{s}':                       # plural "s" after a number insert (softwrap.PLURAL)
            out.append((bytes([softwrap.PLURAL]) + text.enc('s'), g['s'][1], 'c'))
        elif part[0] == '{':
            m = re.fullmatch(r'\{([a-z])((?:[0-9a-fA-F]{2})*)\}', part)
            if not m or m.group(1) not in INSERTS + FREE:
                raise ValueError('bad code %s' % part)
            k, arg = m.group(1), bytes.fromhex(m.group(2))
            if len(arg) != msgfile.ARGS[k]:
                raise ValueError('bad code %s' % part)
            px = widths.get(k.encode() + arg)
            if px is None:
                px = insert_px([(k, arg)]).get(k.encode() + arg, 0)
            out.append((k.encode() + arg, px, 'c'))
        else:
            for ch in part.translate(text.FOLD):
                if ch == ' ':
                    out.append((b' ', g[' '][1], ' '))
                else:
                    out.append((text.enc(ch), g[ch][1], 'c'))
    return out


def wrap(en, width, widths=None):
    """-> (lines as bytes, worst overflow px); width = px, or a function of the line number"""
    limit = width if callable(width) else lambda i: width
    lines, cur, curw, word, wordw, widest = [], b'', 0, b'', 0, 0
    sp = pixfont.glyphs()[' '][1]
    def put_word():
        nonlocal cur, curw, word, wordw
        if not word:
            return
        if cur and curw + sp + wordw > limit(len(lines)):
            end_line()
        if cur:
            cur += b' '; curw += sp
        cur += word; curw += wordw; word, wordw = b'', 0
    def end_line():
        nonlocal cur, curw, widest
        widest = max(widest, curw - limit(len(lines))); lines.append(cur); cur, curw = b'', 0
    for b, px, kind in atoms(en, widths):
        if kind == 'c':
            word += b; wordw += px
        else:
            put_word()
            if kind == 'n':
                end_line()
    put_word()
    if cur or not lines:
        end_line()
    return lines, widest


CAPTION = re.compile(r'- .+ -')
CAPTION_ALT = {87: 'Nagahama', 90: 'Azuchi', 127: 'Ōsaka'}     # castles renamed in the story: mean width


def caption(u, en):
    """A scene caption ("- Home -", alone in a window without a speaker) -> the English with every line
    centred in the window; None for anything else. The `\\_` / `\\n` typed before a line are ignored: the
    indent is computed (kept spaces), an empty first line is kept when the Japanese has one."""
    if not u.window() or any(k in 'sf' for k, v in u.pre):
        return None
    lines = [re.sub(r'^(\\_| )+', '', l).strip() for l in en.split('\\n')]
    while lines and not lines[0]:
        lines.pop(0)
    if not lines or not all(lines) or not any(CAPTION.fullmatch(l) for l in lines):
        return None
    castles, widths, sp = None, {}, pixfont.glyphs()[' '][1]
    for k, v in u.body:
        if k == 'e':
            if castles is None:
                import tables
                castles = tables.english('castles')
            i = int.from_bytes(v[1:], 'big')
            if str(i) in castles:
                w = text.width(castles[str(i)])
                if i in CAPTION_ALT:
                    w = (w + text.width(CAPTION_ALT[i])) // 2
                widths[b'e' + v] = w + (0 if v[0] == 0x73 else text.width(castles['suffix0']))
    out = []
    for l in lines:
        w = sum(px for b, px, kind in atoms(l, widths))
        out.append('\\_' * max(0, (window.WIDTH - w) // 2 // sp) + l)
    first = next((k for k, v in u.body if k != 'c'), None)
    return ('\\n' if first == 'n' and len(out) < window.LINES else '') + '\\n'.join(out)


def codes_of(toks):
    return collections.Counter(k.encode() + v for k, v in toks if k in INSERTS)


def render(u, en, problems=None):
    """English of a unit -> list of page payloads (bytes, each complete with its codes) for packing."""
    def bad(msg):
        if problems is not None:
            problems.append('%d.%s: %s' % (u.block, u.name, msg))
    width, nlines, paged = u.box()
    widths = insert_px(u.body)
    widths.update(EN_PX.get(en, {}))
    cap = caption(u, en)
    if cap is not None:
        en, widths = cap, {k: 0 for k in widths}     # centred on the real names: no worst-case wrap
    lines, over = wrap(en, width, widths)
    waits = any(k in 'gv' for k, v in u.suf)
    per = nlines                                     # lines per page
    if paged and (waits or len(lines) > nlines):     # the wait icon covers the end of window rows 3-4;
        row0 = 1 if any(k == 's' for k, v in u.pre) else 0      # a speaker header takes row 1
        def icon(k):
            return lambda i: window.ICON_WIDTH if i % k + row0 >= 2 else width
        lines, over = wrap(en, icon(nlines), widths)
        if len(lines) > nlines and b'\\n' not in en.encode():   # balance the pages: no page of one last word
            k = -(-len(lines) // -(-len(lines) // nlines))
            l2, o2 = wrap(en, icon(k), widths)
            if k < nlines and -(-len(l2) // k) == -(-len(lines) // nlines) and o2 <= max(over, 0):
                lines, over, per = l2, o2, k
    if over > 0:
        bad('a line is %d px too wide for the box (%d px)' % (over, width))
    have = collections.Counter()
    for b, px, kind in atoms(en):
        if kind == 'c' and len(b) > 1:
            have[b] += 1
    want = codes_of(u.body)
    extra = [k for k in have if chr(k[0]) in INSERTS and have[k] > want[k]]
    if extra:
        bad('insert not in the Japanese: %s' % ' '.join('{%s%s}' % (chr(k[0]), k[1:].hex()) for k in extra))
    if not paged and (len(lines) > nlines or (u.exact() and len(lines) != nlines)):
        bad('%d lines, the box has %s%d (%d px)' % (len(lines), 'exactly ' if u.exact() else '', nlines, width))
    pre, suf = ser(u.pre), b'n' * u.tail_n + ser(u.suf)
    if not paged:
        return [(pre, lines, suf)]
    chunks = [lines[i:i + per] for i in range(0, len(lines), per)]
    # a page with inserts gets its line breaks at runtime (softwrap.py): the worst-case wrap above only cuts
    # the pages. Typed breaks, kept spaces, captions and sprintf formats keep the build-time lines.
    soft = cap is None and '\\' not in en and '%' not in en and any(chr(k[0]) in INSERTS for k in have)
    out = []
    for i, c in enumerate(chunks):
        s = suf if i == len(chunks) - 1 else b'g'
        if soft:
            mode = softwrap.SOFT_WAIT if waits or i < len(chunks) - 1 else softwrap.SOFT
            c = Soft([bytes([mode]) + c[0]] + c[1:])
        out.append((pre, c, s))
    return out


class Soft(list):
    """the lines of a page whose breaks are soft spaces (decided in play)"""


def pack(pieces):
    """page payloads -> string payloads (without the `j` links), each short enough for a link + terminator."""
    room = STRING_BYTES - 3
    out, cur = [], b''
    for pre, lines, suf in pieces:
        whole = pre + (b' ' if isinstance(lines, Soft) else b'n').join(lines) + suf
        if len(cur) + len(whole) <= room:
            cur += whole; continue
        if cur:
            out.append(cur); cur = b''
        if len(whole) <= room:
            cur = whole; continue
        part = pre                                   # one page longer than a string: cut at line ends
        for i, ln in enumerate(lines):
            add = ln + (b'n' if i < len(lines) - 1 else suf)
            if len(part) + len(add) > room:
                out.append(part); part = b''
            part += add
        cur = part
    out.append(cur)
    return out


def build_block(b, problems=None):
    """-> the new string list of a block, or None when it has no English."""
    data, strs, groups, canon = game()
    out, changed = [ser(msgfile.tokens(s)[0]) + b'\0' for s in strs[b]], False    # argument bytes may be 00
    for g in groups[b]:
        ens = [english(u) if u.has_text() else None for u in g.units]
        if all(e is None or e == '=' for e in ens):
            continue
        pieces = []
        for u, e in zip(g.units, ens):
            if e is None or e == '=':
                pieces.append((ser(u.pre), [ser(u.body)], b'n' * u.tail_n + ser(u.suf)))
            else:
                try:
                    pieces += render(u, e, problems)
                except ValueError as err:
                    if problems is None:
                        raise
                    problems.append('%d.%s: %s' % (b, u.name, err))
                    pieces.append((ser(u.pre), [ser(u.body)], b'n' * u.tail_n + ser(u.suf)))
        payloads = pack(pieces)
        slots = list(g.members)
        while len(slots) < len(payloads):
            slots.append(len(out)); out.append(b'\0')
        for i, p in enumerate(payloads):
            link = b'j' + struct.pack('>H', slots[i + 1]) if i + 1 < len(payloads) else b''
            out[slots[i]] = p + link + b'\0'
        for s in slots[len(payloads):]:
            out[s] = b'\0'
        changed = True
    return out if changed else None


def build(problems=None):
    """-> the English MESSAGE.DAT, or None when tl/ has no message text."""
    data = game()[0]
    changes = {}
    for b in range(msgfile.NBLOCKS):
        if not os.path.exists(tl_path(b)) and not any(os.path.exists(tl_path(x)) for x in range(msgfile.NBLOCKS)):
            return None
        new = build_block(b, problems)
        if new is not None:
            changes[b] = new
    if not changes:
        return None
    try:
        return msgfile.rebuild(data, changes)
    except ValueError as err:
        if problems is None:
            raise
        problems.append(str(err))
        return None


# ---- commands

def speaker(i):
    """English name of a speaker id (for `show`: who is talking sets the voice of the line)."""
    import json, names
    if 'sp' not in _cache:
        _cache['sp'] = ([' '.join(n) for n in names.english()], json.load(open(names.GENERIC_TL)))
    people, generic = _cache['sp']
    if i < len(people):
        return people[i]
    if i - 250 < len(generic):
        return generic[i - 250]
    return {999: 'the player'}.get(i, 'slot %d (varies)' % (i - 800) if 800 <= i < 805 else '?')


def unit_header(u, canon):
    c = canon.get(ser(u.body))
    flags = []
    sp = [struct.unpack('>H', v)[0] for k, v in u.pre if k == 's']
    if sp:
        flags.append('s%d %s' % (sp[-1], speaker(sp[-1])))
    if not u.window():
        w, n, _ = u.box()
        flags.append('box %dpx %s%d' % (w, '=' if u.exact() else 'x', n))
    if c is not None and c is not u:
        flags.append('= %d.%s' % (c.block, c.name))
    return '@%s%s' % (u.name, '   # ' + ', '.join(flags) if flags else '')


def show(b, lo=0, hi=None, todo=False, en=False, dups=False, out=sys.stdout):
    data, strs, groups, canon = game()
    for g in groups[b]:
        for u in g.units:
            if not u.has_text() or u.n < lo or (hi is not None and u.n > hi):
                continue
            c = canon.get(ser(u.body))
            if c is not u and not dups and u.key not in load_tl(b):
                continue
            e = english(u)
            if todo and e is not None:
                continue
            out.write('%s\n%s\n' % (unit_header(u, canon), show_toks(u.body)))
            if en and e is not None:
                out.write('> %s\n' % e)


def check(only=None):
    problems = []
    data, strs, groups, canon = game()
    for b in range(msgfile.NBLOCKS):
        if only is not None and b != only:
            continue
        known = {u.key for g in groups[b] for u in g.units if u.has_text()}
        for key in load_tl(b):
            if key not in known:
                problems.append('%d.%d%s: no such unit' % (b, key[0], '.%d' % key[1] if key[1] else ''))
        try:
            new = build_block(b, problems)
            if new is not None:
                msgfile.rebuild(data, {b: new}, whole=False)
        except ValueError as err:
            problems.append(str(err))
    return problems


def stats():
    data, strs, groups, canon = game()
    tot = done = 0
    for b in range(msgfile.NBLOCKS):
        units = [u for g in groups[b] for u in g.units if u.has_text()]
        own = [u for u in units if canon[ser(u.body)] is u]
        d = sum(1 for u in units if english(u) is not None)
        new = build_block(b, [])
        raw = sum(len(s) for s in set(new)) + 2 + 2 * len(new) if new else 0
        size = len(msgpack.pack_block(new)) if new else 0
        room = msgfile.LIMIT.get(b, msgfile.ROOM)
        print('block %2d: %5d units, %5d own, %5d done%s' % (
            b, len(units), len(own), d, ', %5d bytes packed to %5d (%2d %% of the room)%s' % (
                raw, size, 100 * size // room, '  TOO BIG' if size > room else '') if new else ''))
        tot += len(units); done += d
    msgpack.save_cache()
    print('total %d units (%d unique), %d done' % (tot, len(canon), done))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    cmd = args[0] if args else 'stats'
    if cmd == 'show':
        b = int(args[1])
        show(b, int(args[2]) if len(args) > 2 else 0, int(args[3]) if len(args) > 3 else None,
             '--todo' in flags, '--en' in flags, '--dups' in flags)
    elif cmd == 'dump':
        os.makedirs(SCRIPT, exist_ok=True)
        for b in range(msgfile.NBLOCKS):
            with open(os.path.join(SCRIPT, 'msg%02d.txt' % b), 'w', encoding='utf-8') as f:
                show(b, dups=True, out=f)
        print('wrote %s/msgNN.txt' % SCRIPT)
    elif cmd == 'apply':
        b = int(args[1])
        import fcntl                       # workers apply to one block in parallel: read-check-write under a lock
        os.makedirs(TL, exist_ok=True)
        lock = open(os.path.join(TL, '.lock%02d' % b), 'w')
        fcntl.flock(lock, fcntl.LOCK_EX)
        entries = dict(load_tl(b))
        if len(args) > 2:
            entries.update(parse_tl(open(args[2], encoding='utf-8').read(), args[2]))
        old = _tl.get(b)
        _tl[b] = entries
        problems = check(b)
        if problems:
            _tl[b] = old
            print('\n'.join(problems)); sys.exit('%d problems: nothing written' % len(problems))
        save_tl(b, entries)
        print('tl/msg%02d.txt: %d entries' % (b, len(entries)))
    elif cmd == 'check':
        problems = check(int(args[1]) if len(args) > 1 else None)
        print('\n'.join(problems) if problems else 'ok')
        sys.exit(1 if problems else 0)
    elif cmd == 'stats':
        stats()
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()

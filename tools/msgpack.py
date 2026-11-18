"""Byte-pair compression of MESSAGE.DAT blocks (the 0x10000-byte block buffer is too small for English).

Packed block:  u16 BE count | 0x8000, count x u16 BE offset, table of 256 x (a, b), packed strings.
  table[c] = (0, 0): byte c is itself; else c stands for the bytes a, b (each looked up again, depth <= DEPTH).
  0xFF = escape: the next byte is itself (bytes that are codes in this block, and 0xFF).
  Strings have no length: the decoder always produces 200 bytes (the interpreter stops at its terminator).
A block without the 0x8000 flag is in the game's own format, so unchanged blocks stay as they are.

Program side (`patch`): the two lookups 0x8007d6a0 (block 26) / 0x8007d70c (current block) are rewritten in
place and expand a packed string into SCRATCH; every caller copies the result at once (0xc8 / 0xc9 bytes:
EXE 0x80067164, 0x8007d470 / 48c, 0x8007db74 / 90, 0x8007de58, 0x8007dec8, 0x8007df38; MAPPOINT 0x80106ee8,
0x80106f9c, 0x8014ee04). The third, inline lookup at 0x8007dd64 (code `y`) now calls the second one. (softwrap.py
rewrites the whole interpreter afterwards and calls LOOKUP itself: the INLINE patch only matters without it.) The
expansion loop sits in the dead part of the first putchar's single-byte path (vwf.PUT1).
"""
import hashlib, os, pickle, struct
from collections import Counter
import asm, msgfile, vwf

LOOKUP26, LOOKUP, LOOKUP_END = 0x8007d6a0, 0x8007d70c, 0x8007d778
INLINE, INLINE_END = 0x8007dd64, 0x8007dd94
DECODE, DECODE_END = 0x8007b040, vwf.PUT1_END
SCRATCH = 0x8016ED00              # 0x100 bytes in the FONT.DAT buffer tail, below names.BUF
OUT = msgfile.STRING_MAX
ESC, DEPTH, RARE = 0xFF, 24, 8    # stack of the decoder: DEPTH + 1 bytes of 0x20
CACHE = os.path.join(msgfile.ROOT, 'build', 'msgpack.cache')


def _train(strs):
    """unique strings -> (table {code: (a, b)}, {string: packed bytes})"""
    plain = Counter(b''.join(strs))
    codes = sorted((c for c in range(256) if c != ESC and plain[c] <= RARE), key=lambda c: plain[c])
    esc = set(codes) | {ESC}
    # one text: symbols < 0x100 = bytes, 0x100 + b = escaped byte, 0x200 = string end
    text = 'Ȁ'.join(''.join(chr(0x100 + c if c in esc else c) for c in s) for s in strs)
    table, depth = {}, Counter()
    for code in codes:
        pairs = Counter(zip(text, text[1:]))
        best = None
        for (a, b), n in pairs.most_common(40):
            if n < 4:
                break
            if ord(a) < 0x100 and ord(b) < 0x100 and (a, b) != ('\0', '\0') \
                    and max(depth[ord(a)], depth[ord(b)]) < DEPTH:      # (0, 0) = "no pair" in the table
                best = (a, b); break
        if best is None:
            break
        a, b = best
        table[code] = (ord(a), ord(b))
        depth[code] = 1 + max(depth[ord(a)], depth[ord(b)])
        text = text.replace(a + b, chr(code))
    packed = {}
    for s, t in zip(strs, text.split('Ȁ')):
        out = bytearray()
        for ch in t:
            c = ord(ch)
            if c >= 0x100:
                out += bytes((ESC, c - 0x100))
            else:
                out.append(c)
        packed[s] = bytes(out)
    return table, packed


def unpack(tab, data, pos, n=OUT):
    """What the game's decoder does: n bytes from data[pos:]; tab = the 512 table bytes."""
    out, stack = bytearray(), []
    while len(out) < n:
        if stack:
            c = stack.pop()
        else:
            c = data[pos] if pos < len(data) else 0; pos += 1
            if c == ESC:
                out.append(data[pos] if pos < len(data) else 0); pos += 1
                continue
        if tab[2 * c] or tab[2 * c + 1]:
            assert len(stack) <= DEPTH
            stack += (tab[2 * c + 1], tab[2 * c])
        else:
            out.append(c)
    return bytes(out)


_cache = None


def pack_block(ss):
    """string list (00-terminated) -> packed block bytes (not padded)."""
    global _cache
    if _cache is None:
        try:
            _cache = pickle.load(open(CACHE, 'rb'))
        except (OSError, EOFError, pickle.PickleError):
            _cache = {}
    key = hashlib.sha1(struct.pack('>I', len(ss)) + b''.join(struct.pack('>H', len(s)) + s for s in ss)).digest()
    if key in _cache:
        return _cache[key]
    uniq = list(dict.fromkeys(ss))
    table, packed = _train(uniq)
    head = 2 + 2 * len(ss) + 512
    seen, body = {}, bytearray()
    for s in uniq:
        seen[s] = head + len(body); body += packed[s]
    tab = b''.join(bytes(table.get(c, (0, 0))) for c in range(256))
    blk = struct.pack('>H%dH' % len(ss), len(ss) | 0x8000, *[seen[s] for s in ss]) + tab + bytes(body)
    for s in uniq:                                   # the game must get every string back
        assert unpack(tab, blk, seen[s])[:len(s)] == s
    _cache[key] = blk
    return blk


def save_cache():
    if _cache:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        pickle.dump(_cache, open(CACHE, 'wb'))


def patch(exe):
    """exe: bytearray of SLPM_862.68, after vwf.patch. -> bytes free in the expansion area."""
    def put(addr, end, lines):
        code = asm.assemble(addr, lines)
        assert len(code) <= end - addr, 'msgpack at %08x: %d bytes over' % (addr, len(code) - (end - addr))
        o = addr - vwf.EXE_BASE + vwf.EXE_OFF
        exe[o:o + end - addr] = code.ljust(end - addr, b'\0')
        return end - addr - len(code)
    o = DECODE - vwf.EXE_BASE + vwf.EXE_OFF
    assert not any(exe[o:o + DECODE_END - DECODE]), 'expansion area in use'
    put(LOOKUP26, LOOKUP, [('lui', 't0', 0x8017), ('j', LOOKUP + 8), ('ori', 't0', 't0', 0x7000)])
    put(LOOKUP, LOOKUP_END, [                        # (obj, n) -> pointer to string n
        ('lui', 't0', 0x8017), ('ori', 't0', 't0', 0x9000),
        ('sll', 'a1', 'a1', 1), ('addu', 't1', 't0', 'a1'),
        ('lbu', 'v0', 2, 't1'), ('lbu', 'v1', 3, 't1'), ('sll', 'v0', 'v0', 8), ('or', 'v0', 'v0', 'v1'),
        ('lbu', 't2', 0, 't0'), ('addu', 'v0', 't0', 'v0'), ('andi', 't4', 't2', 0x80),
        ('beqz', 't4', 'ret'), ('lbu', 't3', 1, 't0'),
        ('andi', 't2', 't2', 0x7f), ('sll', 't2', 't2', 8), ('or', 't2', 't2', 't3'),
        ('sll', 't2', 't2', 1), ('addu', 't2', 't2', 't0'), ('addiu', 't2', 't2', 2),      # t2 = table
        ('lui', 't5', asm.hi(SCRATCH)), ('addiu', 't5', 't5', asm.lo(SCRATCH)), ('addiu', 't6', 't5', OUT),
        ('addiu', 'sp', 'sp', -0x20), ('j', DECODE), ('addiu', 't7', 'sp', 0x20),
        'ret:', ('jr', 'ra'), ('nop',),
    ])
    free = put(DECODE, DECODE_END, [                 # v0 = source, t2 = table, t5 / t6 = out / end, t7 = stack
        ('addu', 't8', 't7', 'zero'),
        'loop:', ('beq', 't7', 't8', 'read'), ('addiu', 'at', 'zero', ESC),
        ('lbu', 't1', 0, 't7'), ('b', 'have'), ('addiu', 't7', 't7', 1),
        'read:', ('lbu', 't1', 0, 'v0'), ('addiu', 'v0', 'v0', 1), ('bne', 't1', 'at', 'have'), ('nop',),
        ('lbu', 't1', 0, 'v0'), ('b', 'emit'), ('addiu', 'v0', 'v0', 1),
        'have:', ('sll', 't3', 't1', 1), ('addu', 't3', 't3', 't2'),
        ('lbu', 't4', 0, 't3'), ('lbu', 't9', 1, 't3'), ('sb', 't4', -2, 't7'), ('or', 'at', 't4', 't9'),
        ('beqz', 'at', 'emit'), ('sb', 't9', -1, 't7'), ('b', 'loop'), ('addiu', 't7', 't7', -2),
        'emit:', ('sb', 't1', 0, 't5'), ('addiu', 't5', 't5', 1), ('bne', 't5', 't6', 'loop'), ('nop',),
        ('addiu', 'sp', 'sp', 0x20), ('jr', 'ra'), ('addiu', 'v0', 't6', -OUT),
    ])
    put(INLINE, INLINE_END, [('jal', LOOKUP), ('addu', 'a1', 's0', 'zero'), ('b', INLINE_END), ('sw', 'v0', 0x28, 'sp')])
    return free

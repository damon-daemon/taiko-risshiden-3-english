"""DATA/MESSAGE.DAT: the script (55 blocks of strings with single-letter control codes).

File:  TOC 55 x (u32 BE offset, u32 BE size), blocks 0x800-aligned.
Block: u16 BE count, count x u16 BE offset (from the block start), strings (00-terminated, but argument bytes
       may be 00: always take lengths from the offset table).
String grammar (interpreter 0x8007d778 in SLPM_862.68; at most 200 bytes are copied and run):
  z clear window   n newline   g wait for button   v wait / auto   w pause 20 frames
  s+u16 speaker (person id; 800-804 = variable slot, 999 = player) and face   f+u16 face only
  a+{s,m,other}+u16 person name (surname / given / full)   e+{s,other}+u16 name from table 0x80056394
  b+u8 number variable   p+u8 string variable   c+u8 (0x8007d00c)   d+u8 (0x8008b0d0)
  j+u16 continue with string N (of the same block)   y+u8+u16+u16 two-way branch to string N1 / N2
  0-9 . and other single bytes: drawn half-width; ESC + letter (+ hex digit): colour; Shift-JIS pairs: 12x12.
  A few strings are printf formats for program code (%s): '%' + letter is kept as text.
All multi-byte arguments are big-endian.

usage: tools/msgfile.py stats|dump [block]
"""
import os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'extract', 'DATA', 'MESSAGE.DAT')
NBLOCKS = 55
ARGS = {'a': 3, 'e': 3, 'b': 1, 'c': 1, 'd': 1, 'p': 1, 'f': 2, 's': 2, 'j': 2, 'y': 5,
        'g': 0, 'n': 0, 'v': 0, 'w': 0, 'z': 0}
ENDS = 'jy'                      # the interpreter replaces its buffer: nothing after these runs


def is_lead(c):
    return 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC


def blocks(data):
    for i in range(NBLOCKS):
        off, size = struct.unpack_from('>II', data, i * 8)
        yield data[off:off + size]


def strings(block):
    n = struct.unpack_from('>H', block, 0)[0]
    offs = list(struct.unpack_from('>%dH' % n, block, 2)) + [None]
    out = []
    for i in range(n):
        end = offs[i + 1] if offs[i + 1] is not None else len(block)
        out.append(block[offs[i]:end])
    return out


STRING_MAX = 200                 # the interpreter copies at most 200 bytes of a string
LIMIT = {26: 0x2000}             # RAM room of a block (block 26 stays loaded at 0x80177000); others ROOM
ROOM = 0xE000                    # current block: 0x10000 buffer at 0x80179000 less its top 0x2000, which holds
                                 # the English name blob (tables.BLOB_RAM); the loader reads the TOC size only


def rebuild(data, changes, whole=True):
    """MESSAGE.DAT with blocks replaced: changes = {block: [string bytes, 00-terminated]} (the list may be
    longer than the original: appended strings are reached with `j`). Changed blocks are written packed
    (msgpack.py: the patched lookups expand them); identical strings share one copy."""
    import msgpack
    out, toc = bytearray(), []
    head = NBLOCKS * 8
    for b, blk in enumerate(blocks(data)):
        if b in changes:
            ss = changes[b]
            for s in ss:
                assert s.endswith(b'\0') and len(s) <= STRING_MAX, (b, s)
            blk = msgpack.pack_block(ss)
            blk = blk.ljust((len(blk) + 0x7FF) & ~0x7FF, b'\0')
        if changes and (whole or b in changes) and len(blk) > LIMIT.get(b, ROOM):   # also an unchanged block: it would
            raise ValueError('block %d: %#x bytes, limit %#x' % (b, len(blk), LIMIT.get(b, ROOM)))  # run into the blob
        toc.append((len(out), len(blk)))
        out += blk
    msgpack.save_cache()
    first = struct.unpack_from('>I', data, 0)[0]
    return b''.join(struct.pack('>II', first + o, n) for o, n in toc) + data[head:first] + bytes(out)


def tokens(raw):
    """-> list of ('t', text) / (code letter, args bytes); stops at the terminator. Raises on a bad parse."""
    out, i, text = [], 0, b''
    def flush():
        nonlocal text
        if text:
            out.append(('t', text.decode('cp932'))); text = b''
    while i < len(raw):
        c = raw[i]
        if c == 0:
            break
        ch = chr(c)
        if is_lead(c) or c == 0x25:                  # Shift-JIS pair; %s / %d of a printf format (program use)
            text += raw[i:i + 2]; i += 2
        elif ch in ARGS:
            flush()
            out.append((ch, raw[i + 1:i + 1 + ARGS[ch]])); i += 1 + ARGS[ch]
            if ch in ENDS:
                break
        elif c == 0x1B:
            flush(); out.append(('ESC', raw[i + 1:i + 3])); i += 3
        else:
            text += raw[i:i + 1]; i += 1
    flush()
    return out, raw[i:]


if __name__ == '__main__':
    from collections import Counter
    data = open(PATH, 'rb').read()
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'stats'
    only = int(sys.argv[2]) if len(sys.argv) > 2 else None
    codes, bad, single, maxlen, tails = Counter(), 0, Counter(), 0, Counter()
    for b, blk in enumerate(blocks(data)):
        if only is not None and b != only:
            continue
        ss = strings(blk)
        for n, raw in enumerate(ss):
            try:
                toks, rest = tokens(raw)
            except Exception as e:
                bad += 1; print('BAD', b, n, e, raw[:40].hex()); continue
            tails[bytes(rest.rstrip(b'\0')[:1])] += 1
            maxlen = max(maxlen, len(raw.rstrip(b'\0')))
            for k, v in toks:
                codes[k] += 1
                if k == 't':
                    single.update(ch for ch in v if ord(ch) < 0x80)
            if cmd == 'dump':
                print('%d.%d\t%s' % (b, n, ''.join(v if k == 't' else '{%s%s}' % (k, v.hex()) for k, v in toks)))
        if cmd == 'stats':
            print('block %2d: %5d strings, %6d bytes' % (b, len(ss), len(blk.rstrip(b'\0'))))
    if cmd == 'stats':
        print('codes', dict(codes)); print('single-byte text chars', dict(single))
        print('bad', bad, 'max string bytes', maxlen, 'leftover after end', dict(tails))

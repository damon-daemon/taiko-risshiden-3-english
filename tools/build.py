"""Build the patched disc image from the clean one and tl/.

Output: build/taiko_risshiden_3_en.bin + .cue and build/taiko_risshiden_3_en.xdelta. With
nothing to insert the image is identical to the clean one (same SHA-1).

usage: python3 tools/build.py [--grow] [clean.bin] [out.bin]
  --grow   test build: MESSAGE.DAT and FONT.DAT get one more (empty) sector, so both move to
           the end of the disc; checks that the game finds moved / resized files
"""
import os, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
import gfx, iso, layout, msgpack, nameentry, names, player, progstr, rectab, setup, softwrap, strbuf, tables, tl, vwf, window

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'build', 'taiko_risshiden_3_en.bin')
PATCH = 'taiko_risshiden_3_en.xdelta'
FIXED = (iso.EXE_NAME, 'SYSTEM.CNF')     # must keep their place


def build_files(disc, recs, grow=False):
    files = {}
    if grow:
        for name in ('DATA/MESSAGE.DAT', 'DATA/FONT.DAT'):
            files[name] = disc.file(name, recs) + bytes(iso.SECTOR)
    problems = []
    message = tl.build(problems)
    if problems:
        sys.exit('\n'.join(problems) + '\n%d text problems (tools/tl.py check)' % len(problems))
    if message is not None:                  # any English at all: our font and draw routine go in
        font, w = vwf.font_file(disc.file('DATA/FONT.DAT', recs))
        exe = bytearray(disc.file(iso.EXE_NAME, recs))
        print('vwf: %d bytes free after the draw routine' % vwf.patch(exe, w))
        window.patch(exe)
        assert vwf.FONT_RAM + len(font) <= strbuf.BATTLE_BUF and strbuf.BATTLE_BUF + 0xF0 <= msgpack.SCRATCH and msgpack.SCRATCH + 0x100 <= names.BUF
        print('message unpacker: %d bytes free' % msgpack.patch(exe))
        print('interpreter (soft wrap): %d bytes free' % softwrap.patch(exe, w))
        print('names: %d bytes free in the getter block' % names.patch(exe))
        print('player names: %d bytes free in the accessor block' % player.patch(exe))
        for name in ('BATTLE.BIN', 'MAPPOINT.BIN'):
            new = player.patch_overlay(name, disc.file(name, recs))
            if new:
                files[name] = new
        print('table names: %d bytes free in the getter blocks' % tables.patch(exe))
        print('building names: %d bytes free' % rectab.patch(exe))
        print('clan names: %d bytes free' % strbuf.patch(exe))
        clean = progstr.disc_files(disc, recs)
        imgs = {'PROG': exe}
        for t in progstr.OVERLAYS:
            imgs[t] = rectab.patch_overlay(progstr.ovl_name(t), bytearray(files.get(progstr.ovl_name(t), clean[t])))
        strbuf.patch_battle(imgs['BATTLE'])
        n, moved, pool = progstr.apply(imgs, clean, progstr.resident(clean['PROG']))
        print('program strings: %d (%d moved), free %s' % (n, moved, pool.room()))
        print('layout: %d constants' % layout.apply(imgs))
        print('name entry: %d bytes free' % nameentry.patch(exe))
        softwrap.verify(exe, w)
        for t in progstr.OVERLAYS:
            if imgs[t] != clean[t]:
                files[progstr.ovl_name(t)] = bytes(imgs[t])
        files['DATA/SCENARIO.DAT'] = tables.patch_scenario(names.patch_scenario(disc.file('DATA/SCENARIO.DAT', recs)), progstr.extra())
        files['DATA/FONT.DAT'] = font
        print('graphics: %d labels redrawn' % gfx.patch(files, lambda n: disc.file(n, recs)))
        files[iso.EXE_NAME] = bytes(exe)
        files['DATA/MESSAGE.DAT'] = message
    return files


def write(clean, out, files):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    moved = iso.write_image(clean, out, files)
    print('rebuilt %s%s' % (out, ' (moved: %s)' % ', '.join(moved) if moved else ''))
    if set(moved) & set(FIXED):
        sys.exit('%s moved on the disc' % ', '.join(set(moved) & set(FIXED)))
    iso.verify(out, files)
    iso.write_cue(out[:-4] + '.cue', out, [])
    patch = os.path.join(os.path.dirname(out), PATCH)
    try:
        subprocess.run(['xdelta3', '-e', '-f', '-9', '-S', 'djw', '-B', str(1 << 28), '-s', clean, out, patch], check=True)
        print('patch %s (%d bytes)' % (patch, os.path.getsize(patch)))
    except FileNotFoundError:
        print('xdelta3 not installed; skipped patch')
    return moved


def main():
    args = sys.argv[1:]
    grow = '--grow' in args
    args = [a for a in args if not a.startswith('--')]
    clean = args[0] if args else setup.CLEAN
    out = args[1] if len(args) > 1 else OUT
    disc = iso.Disc(clean)
    files = build_files(disc, disc.records(), grow)
    write(clean, out, files)
    if not files:
        same = setup.sha1(out) == setup.CLEAN_SHA1
        print('identity build: SHA-1 %s the clean image' % ('matches' if same else 'DIFFERS from'))


if __name__ == '__main__':
    main()

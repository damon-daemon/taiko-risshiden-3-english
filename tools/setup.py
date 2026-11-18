"""Check your own disc image and create the working folder extract/.

extract/ holds the files of the disc (movies and XA sound left out), so it is generated on each
machine and never distributed. Run this once after cloning, then tools/build.py.

usage: python3 tools/setup.py [image.bin]
"""
import hashlib, os, sys

sys.path.insert(0, os.path.dirname(__file__))
import iso

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACT = os.path.join(ROOT, 'extract')
CLEAN = os.path.join(ROOT, 'taiko_risshiden_3.bin')
# Taikou Risshiden III (Japan) (Rev 1): Koei the Best SLPM-86608 / Koei Teiban SLPM-87275
CLEAN_SHA1 = '9c4ead8a3c2c466b657472ae211ba07da60ac220'
SKIP = ('.STR', '.XA', 'DUMMY.DAT')      # Form 2 movies / sound, padding


def sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        while chunk := f.read(1 << 24):
            h.update(chunk)
    return h.hexdigest()


def check_clean(path, want=CLEAN_SHA1):
    digest = sha1(path)
    if digest != want:
        sys.exit('%s: SHA-1 %s does not match the clean Rev 1 dump (%s)' % (path, digest, want))


def extract(disc):
    n = 0
    for name, lba, size in disc.walk():
        if name.endswith(SKIP):
            continue
        p = os.path.join(EXTRACT, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as f:
            f.write(disc.read(lba, size))
        n += 1
    return n


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else CLEAN
    check_clean(path)
    print('extract/: %d files' % extract(iso.Disc(path)))
    print('ready; now run tools/build.py')


if __name__ == '__main__':
    main()

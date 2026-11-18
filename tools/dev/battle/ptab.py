import sys, struct, re
d=open('/home/leto2/Projects/taiko_risshiden_3_translation/extract/BATTLE.BIN','rb').read()
e=open('/home/leto2/Projects/taiko_risshiden_3_translation/extract/SLPM_862.68','rb').read()
en={}
for f in ['04_battle','03_sdata','01_system','02_data','05_mappoint']:
    try:
        for l in open('/home/leto2/Projects/taiko_risshiden_3_translation/tl/progstr/%s.txt'%f):
            m=re.match(r'(\w+):([0-9a-f]+)\t(.*)',l)
            if m: en[int(m.group(2),16)]=m.group(3)
    except FileNotFoundError: pass
def s(a):
    if 0x800ee000<=a<0x800ee000+len(d): o=a-0x800ee000; b=d
    else: o=a-0x80010000+0x800; b=e
    return b[o:o+60].split(b'\0')[0].decode('sjis','replace')
def w(a):
    return struct.unpack('<I', d[a-0x800ee000:a-0x800ee000+4])[0]
a=int(sys.argv[1],16); n=int(sys.argv[2])
for i in range(n):
    p=w(a+4*i)
    print(i, hex(p), s(p), '|', en.get(p,'?'))

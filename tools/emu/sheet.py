"""sheet.py out.png a.png b.png ... : screenshots side by side, 3 per row (for reading several at once)."""
import sys
from PIL import Image
ims = [Image.open(p).convert('RGB') for p in sys.argv[2:]]
w, h = ims[0].size
rows = (len(ims) + 2) // 3
s = Image.new('RGB', (w * min(3, len(ims)), h * rows))
for i, im in enumerate(ims):
    s.paste(im, (w * (i % 3), h * (i // 3)))
s.save(sys.argv[1])

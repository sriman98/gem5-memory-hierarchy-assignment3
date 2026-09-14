#!/usr/bin/env python3
"""crop.py in.png out.png -- trim the empty terminal rows at the bottom of a Terminal.app window capture."""
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert("RGB")
w, h = im.size
bg = im.getpixel((w // 2, h - 8))                       # terminal background colour
px = im.load()
last = h - 1
for y in range(h - 1, 60, -1):                          # keep the title bar (top ~60 px @2x)
    row_has_ink = any(sum(abs(a - b) for a, b in zip(px[x, y], bg)) > 60 for x in range(8, w - 8, 3))
    if row_has_ink:
        last = y; break
im.crop((0, 0, w, min(h, last + 28))).save(sys.argv[2])
print("cropped", sys.argv[2], im.size, "->", (w, min(h, last + 28)))

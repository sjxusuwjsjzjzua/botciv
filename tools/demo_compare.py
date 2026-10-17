"""Step 0's comparison image: the target picture and view A side by side (docs/world5_handoff.md §5.7)."""
import sys
from PIL import Image, ImageDraw

target, shot, out = sys.argv[1:4]
H = 900
a = Image.open(target).convert("RGB"); a = a.resize((round(a.width * H / a.height), H))
b = Image.open(shot).convert("RGB"); b = b.resize((round(b.width * H / b.height), H))
im = Image.new("RGB", (a.width + b.width + 12, H + 40), (250, 245, 235))
im.paste(a, (0, 40)); im.paste(b, (a.width + 12, 40))
d = ImageDraw.Draw(im)
d.text((10, 12), "the target (painted by Gemini)", fill=(60, 45, 30))
d.text((a.width + 22, 12), "view A, rendered live by the demo (three.js, the viewer's kit)", fill=(60, 45, 30))
im.save(out, quality=90)

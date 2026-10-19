# Contact sheets for reviewing the test images: 3 x 2 tiles with id, mode and the Hungarian prompt under each.
import json, os, sys, textwrap
from PIL import Image, ImageDraw, ImageFont
SRC, OUT = sys.argv[1], sys.argv[2]          # SRC = staged gen/out folder (manifest.jsonl + <model>/*.jpg)
os.makedirs(OUT, exist_ok=True)
F = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font = ImageFont.truetype(F, 15); fontb = ImageFont.truetype(F.replace('Sans.ttf', 'Sans-Bold.ttf'), 16)
recs = [json.loads(l) for l in open(os.path.join(SRC, 'manifest.jsonl'), encoding='utf-8')]
models = sorted(set(r['model'] for r in recs), key=lambda m: ['zit', 'juggernaut', 'realvis', 'pony', 'flux'].index(m) if m in ['zit', 'juggernaut', 'realvis', 'pony', 'flux'] else 9)
only = sys.argv[3].split(',') if len(sys.argv) > 3 else None
TW, TH, CAP, COLS, ROWS = 480, 480, 150, 3, 2
for m in models:
    if only and m not in only: continue
    rs = sorted([r for r in recs if r['model'] == m], key=lambda r: (r['id'], r['mode'] != 'tr'))
    for s in range(0, len(rs), COLS * ROWS):
        chunk = rs[s:s + COLS * ROWS]
        sheet = Image.new('RGB', (COLS * TW, ROWS * (TH + CAP)), (16, 18, 22)); d = ImageDraw.Draw(sheet)
        for k, r in enumerate(chunk):
            x, y = (k % COLS) * TW, (k // COLS) * (TH + CAP)
            p = os.path.join(SRC, m, r['id'] + '_' + r['mode'] + '.jpg')
            if os.path.exists(p):
                im = Image.open(p); im.thumbnail((TW - 8, TH - 8)); sheet.paste(im, (x + (TW - im.width) // 2, y + (TH - im.height) // 2))
            d.text((x + 6, y + TH + 2), '%s %s  [%s]' % (r['id'], 'NYERS MAGYAR' if r['mode'] == 'raw' else '', (r.get('theme') or '')[:22]), fill=(242, 184, 75) if r['mode'] == 'tr' else (248, 113, 113), font=fontb)
            for i, line in enumerate(textwrap.wrap(r['hu'], 56)[:7]):
                d.text((x + 6, y + TH + 22 + i * 17), line, fill=(220, 224, 232), font=font)
        sheet.save(os.path.join(OUT, '%s_%02d.jpg' % (m, s // (COLS * ROWS) + 1)), quality=85)
print('ok')

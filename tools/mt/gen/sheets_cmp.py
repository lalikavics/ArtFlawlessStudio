# Side-by-side review sheets: the earlier test image (R4 translator, mode "tr") next to the new one (R6, mode "tr6"),
# with the Hungarian prompt and, when the English translation changed, both English texts.
#   python sheets_cmp.py <staged gen/out folder> <out folder> <model>
import json, os, sys, textwrap
from PIL import Image, ImageDraw, ImageFont
SRC, OUT, M = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
F = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font = ImageFont.truetype(F, 12); fontb = ImageFont.truetype(F.replace('Sans.ttf', 'Sans-Bold.ttf'), 14)
recs = {}
for l in open(os.path.join(SRC, 'manifest.jsonl'), encoding='utf-8'):
    r = json.loads(l)
    if r['model'] == M:
        recs[(r['id'], r['mode'])] = r
ids = sorted({i for i, m in recs if m == 'tr6'})
if len(sys.argv) > 4:
    ids = [i for i in ids if i in sys.argv[4].split(',')]
TW, CAP, PER = 300, 150, 6          # one pair = 2 x 300 px wide; 2 pairs per row, 3 rows
for s in range(0, len(ids), PER):
    chunk = ids[s:s + PER]
    sheet = Image.new('RGB', (2 * 2 * TW + 20, 3 * (TW + CAP)), (16, 18, 22)); d = ImageDraw.Draw(sheet)
    for k, i in enumerate(chunk):
        x0, y = (k % 2) * (2 * TW + 20), (k // 2) * (TW + CAP)
        for j, mode in enumerate(('tr', 'tr6')):
            p = os.path.join(SRC, M, '%s_%s.jpg' % (i, mode))
            if os.path.exists(p):
                im = Image.open(p); im.thumbnail((TW - 6, TW - 6)); sheet.paste(im, (x0 + j * TW + (TW - im.width) // 2, y + (TW - im.height) // 2))
        old, new = recs.get((i, 'tr'), {}), recs.get((i, 'tr6'), {})
        tag = '%s  [%s]  régi | új%s' % (i, (new.get('theme') or '')[:16], '  +clothed' if new.get('clothed') else '')
        d.text((x0 + 4, y + TW + 2), tag, fill=(242, 184, 75), font=fontb)
        lines = textwrap.wrap('HU: ' + new.get('hu', ''), 95)[:3]
        if old.get('en') != new.get('en'):
            lines += textwrap.wrap('R4: ' + old.get('en', ''), 95)[:2] + textwrap.wrap('R6: ' + new.get('en', ''), 95)[:2]
        else:
            lines += ['(angol fordítás ugyanaz)']
        for n, line in enumerate(lines[:8]):
            d.text((x0 + 4, y + TW + 20 + n * 15), line, fill=(220, 224, 232) if not line.startswith('R') else (150, 200, 255), font=font)
    sheet.save(os.path.join(OUT, '%s_%s_%02d.jpg' % (M, 'sel' if len(sys.argv) > 4 else 'cmp', s // PER + 1)), quality=82)
changed = sum(1 for i in ids if recs.get((i, 'tr'), {}).get('en') != recs[(i, 'tr6')].get('en'))
print(M, len(ids), 'new images,', changed, 'with a changed translation')

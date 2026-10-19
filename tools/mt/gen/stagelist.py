import json, sys
m = sys.argv[1]; raw = {'01','03','08','15','22','27','35','43','51','57'}
fs = ['C:\\ArtFlawlessStudio\\mt-train\\gen\\out\\manifest.jsonl']
for i in ['%02d' % k for k in range(1, 61)]:
    fs.append('C:\\ArtFlawlessStudio\\mt-train\\gen\\out\\%s\\%s_tr.jpg' % (m, i))
    if i in raw: fs.append('C:\\ArtFlawlessStudio\\mt-train\\gen\\out\\%s\\%s_raw.jpg' % (m, i))
print(json.dumps(fs[:50])); print(json.dumps(fs[50:]))

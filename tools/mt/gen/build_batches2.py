# Builds the test workflows with the Studio page itself (its own buildPrompt, theme table, model settings, safe mode),
# against the user's real object_info, so the workflows are exactly what the Studio would send. Placeholders §P§/§N§
# are filled in on the PC by 20_generate.py (translated by the Studio's backend, or raw Hungarian for the baseline).
import json, http.server, threading, sys, os
from playwright.sync_api import sync_playwright
W = '/home/claude/build/studio_out'
OI = json.load(open(sys.argv[1]))           # object_info.json from the PC
OUTDIR = sys.argv[2]
cat = json.load(open(W + '/catalog.json'))
HAVE = {'z_image_turbo_bf16', 'juggernaut_xl_v9', 'realvisxl_v5', 'pony_v6', 'flux1_schnell_fp8'}
for m in cat['models']:
    m['installed'] = m['id'] in HAVE


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def out(self, b, ct='application/json'):
        self.send_response(200); self.send_header('Content-Type', ct); self.end_headers(); self.wfile.write(b if isinstance(b, bytes) else json.dumps(b).encode())
    def do_GET(self):
        p = self.path.split('?')[0]
        if p == '/artflow': return self.out(open(W + '/web/index.html', 'rb').read(), 'text/html')
        if p == '/artflow/catalog': return self.out(cat)
        if p.startswith('/artflow/template/'): return self.out(open(W + '/web/' + p.split('/')[-1], 'rb').read())
        if p.endswith('template.json'): return self.out(open(W + '/web/template.json', 'rb').read())
        if p == '/object_info': return self.out(OI)
        if p.startswith('/object_info/'):
            c = urllib_unquote(p.split('/object_info/')[1]); return self.out({c: OI[c]} if c in OI else {})
        if p == '/artflow/translate/status': return self.out({'installed': True, 'size': 1})
        return self.out({})
    def do_POST(self):
        return self.out({})


from urllib.parse import unquote as urllib_unquote
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8777), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
prompts = []
for line in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts_hu.tsv'), encoding='utf-8'):
    if line.startswith('#') or not line.strip(): continue
    i, th, ra, hu = line.rstrip('\n').split('\t')
    prompts.append({'id': i, 'theme': th, 'ratio': ra, 'hu': hu})
NEG = 'elmosódott, torz kéz, rossz anatómia, vízjel, szöveg, alacsony minőség'
MODELS = [('zimage', 'z_image_turbo_bf16', 'zit'), ('sdxl', 'juggernaut_xl_v9', 'juggernaut'), ('sdxl', 'realvisxl_v5', 'realvis'),
          ('sdxl', 'pony_v6', 'pony'), ('flux', 'flux1_schnell_fp8', 'flux')]
RAW = {'01', '03', '08', '15', '22', '27', '35', '43', '51', '57'}   # baseline: the same prompt sent in Hungarian, untranslated
JS = r"""async ([fam, mid, ps, neg, raw]) => {
  await switchFamily(fam); const m = CAT.models.find(x => x.id === mid); applyModel(m);
  for (const k of Object.keys(T.groups)) S.groups[k] = (k === '5');
  const c = saveCfg(); c.prefix = 'hutest6'; c.tags.theme = true; c.tags.date = false;
  SAFE.safe = true;
  const out = [];
  const esc = s => JSON.stringify(s).slice(1, -1);
  for (const p of ps) {
    setVal('86', 'choice', p.theme); setVal('87', 'choice', p.ratio);
    // the real prompt text goes in, so safe mode sees it (person words), then it is swapped for the placeholder
    setVal('46', 'value', p.hu); setVal('51', 'value', neg);
    const seed = 1000 + Number(p.id);
    const wf = buildPrompt(seed, Number(p.id));
    let js = JSON.stringify(wf);
    const clothed = js.includes(esc(p.hu + ', clothed'));
    js = js.split(esc(p.hu)).join('§P§').split(esc(neg)).join('§N§');
    out.push({id: p.id, theme: p.theme, hu: p.hu, neg, seed, mode: 'tr6', clothed, look: !!(T.ids && T.ids.look && S.vals[T.ids.look + '.value']), workflow: JSON.parse(js)});
  }
  return out;
}"""
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 1500, 'height': 950}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("try{localStorage.clear();localStorage.setItem('artflow.studio.lang','hu')}catch(e){}")
    pg.goto('http://127.0.0.1:8777/artflow'); pg.wait_for_timeout(2000)
    for fam, mid, short in MODELS:
        items = pg.evaluate(JS, [fam, mid, prompts, NEG, sorted(RAW)])
        for it in items: it['model'] = short
        # sanity: placeholders present, model file set, only the save group on
        s = json.dumps(items[0]['workflow'], ensure_ascii=False)
        assert '§P§' in s and '§N§' in s, short
        json.dump(items, open(os.path.join(OUTDIR, 'c_' + short + '.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        print(short, len(items), 'items', 'nodes', len(items[0]['workflow']))
    print('errors', errs)

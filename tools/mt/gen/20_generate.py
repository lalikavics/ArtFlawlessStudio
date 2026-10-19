# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Image test of Hungarian prompting. gen/<batch>.json holds Studio-built workflows (made by the Studio's own buildPrompt)
# whose prompt fields carry the placeholders §P§ / §N§. For each item this script translates the Hungarian prompt with
# the running Studio (/artflow/translate, the same code the Studio uses), or keeps it raw for the "no translation" baseline,
# queues it in ComfyUI, waits, and copies the image + a 512 px preview to gen/out/<model>/.  Resumable (manifest.jsonl).
#   env: GEN_BATCH = name of the json in gen/ (without .json)
import json, os, sys, time, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
B = 'http://127.0.0.1:8199'
GEN = os.path.join(HERE, 'gen')


def post(path, body, timeout=300):
    r = urllib.request.Request(B + path, data=json.dumps(body).encode('utf-8'), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r, timeout=timeout).read().decode('utf-8'))


def get(path, timeout=60):
    return json.loads(urllib.request.urlopen(B + path, timeout=timeout).read().decode('utf-8'))


def esc(s):
    return json.dumps(s, ensure_ascii=False)[1:-1]


def main():
    from PIL import Image
    batch = os.environ['GEN_BATCH']
    items = json.load(open(os.path.join(GEN, batch + '.json'), encoding='utf-8'))
    for i in range(120):
        try:
            get('/system_stats', 5); break
        except Exception:
            time.sleep(5)
    man_p = os.path.join(GEN, 'out', 'manifest.jsonl'); os.makedirs(os.path.dirname(man_p), exist_ok=True)
    done = set()
    if os.path.exists(man_p):
        for line in open(man_p, encoding='utf-8'):
            try:
                done.add(json.loads(line)['key'])
            except Exception:
                pass
    t_all = time.time(); n = 0
    for it in items:
        key = it['model'] + '/' + it['id'] + '_' + it['mode']
        if key in done:
            continue
        hu, neg = it['hu'], it.get('neg', '')
        t0 = time.time()
        if it['mode'].startswith('tr'):
            j = post('/artflow/translate', {'texts': [hu, neg]}); en, en_neg = j['texts']; tr_ms = j.get('ms')
        else:
            en, en_neg, tr_ms = hu, neg, 0
        wf = json.dumps(it['workflow'], ensure_ascii=False).replace('§P§', esc(en)).replace('§N§', esc(en_neg))
        wf = json.loads(wf)
        r = post('/prompt', {'prompt': wf, 'client_id': 'hutest', 'extra_data': {'extra_pnginfo': {}}})   # like the Studio; Power Puter needs it
        pid = r.get('prompt_id')
        if not pid:
            print('REJECTED', key, json.dumps(r)[:800], flush=True); continue
        out = None
        for k in range(900):
            time.sleep(2)
            h = get('/history/' + pid)
            if pid in h:
                st = h[pid].get('status', {})
                if st.get('completed') or st.get('status_str') in ('success', 'error'):
                    out = h[pid]; break
        if not out:
            print('TIMEOUT', key, flush=True); continue
        imgs = []
        for nid, o in out.get('outputs', {}).items():
            for im in o.get('images', []):
                if im.get('type') == 'output':
                    imgs.append(im)
        if not imgs:
            print('NO IMAGE', key, json.dumps(out.get('status'))[:600], flush=True); continue
        im = imgs[-1]
        q = urllib.parse.urlencode({'filename': im['filename'], 'subfolder': im.get('subfolder', ''), 'type': 'output'})
        data = urllib.request.urlopen(B + '/view?' + q, timeout=120).read()      # the output folder is set by the launcher
        dd = os.path.join(GEN, 'out', it['model']); os.makedirs(dd, exist_ok=True)
        base = it['id'] + '_' + it['mode']
        src = os.path.join(dd, base + '.png'); open(src, 'wb').write(data)
        p = Image.open(src).convert('RGB'); p.thumbnail((512, 512)); p.save(os.path.join(dd, base + '.jpg'), quality=86)
        rec = {'key': key, 'model': it['model'], 'id': it['id'], 'mode': it['mode'], 'theme': it.get('theme'), 'clothed': it.get('clothed'), 'look': it.get('look'), 'hu': hu, 'en': en,
               'neg_en': en_neg, 'seed': it.get('seed'), 'tr_ms': tr_ms, 'sec': round(time.time() - t0, 1), 'file': im['filename'], 'subfolder': im.get('subfolder', '')}
        open(man_p, 'a', encoding='utf-8').write(json.dumps(rec, ensure_ascii=False) + '\n')
        n += 1
        print('%s  %.1fs  EN: %s' % (key, time.time() - t0, en[:140]), flush=True)
    print('done', n, 'images in', round(time.time() - t_all), 's')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback; traceback.print_exc(); sys.exit(1)

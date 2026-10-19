# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Step 4: round-trip check. Each Hungarian candidate (EuroLLM, opus-mt-en-hu) is translated back to English with
# opus-mt-hu-en and compared with the original (chrF). Unfaithful candidates (made-up words, loops) score low.
#   in : data/hu_pairs.jsonl, data/hu_opus.jsonl     out: data/scored.jsonl ({"id","en","cands":[{"src","hu","back","chrf"}]})
import json, os, re, sys, time, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); DATA = os.path.join(HERE, 'data')
MDIR = os.path.join(ROOT, 'ComfyUI_windows_portable', 'ComfyUI', 'models', 'mt-test', 'opus-mt-hu-en')
DST = os.path.join(DATA, 'scored.jsonl')
LOG = open(os.path.join(DATA, '04_roundtrip.log'), 'a', encoding='utf-8')
def log(*a):
    s = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
def ngrams(t, n):
    t = re.sub(r'\s+', ' ', t.lower()).strip()
    return collections.Counter(t[i:i + n] for i in range(max(0, len(t) - n + 1)))
def chrf(hyp, ref, n=6, beta=2.0):
    ps, rs = [], []
    for k in range(1, n + 1):
        h, r = ngrams(hyp, k), ngrams(ref, k); m = sum((h & r).values())
        ps.append(m / max(1, sum(h.values()))); rs.append(m / max(1, sum(r.values())))
    p, r = sum(ps) / n, sum(rs) / n
    return 0.0 if p + r == 0 else (1 + beta ** 2) * p * r / (beta ** 2 * p + r)
def main():
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    tok = MarianTokenizer.from_pretrained(MDIR); model = MarianMTModel.from_pretrained(MDIR).to(dev).eval()
    if dev == 'cuda': model = model.half()
    euro = {r['id']: r for r in map(json.loads, open(os.path.join(DATA, 'hu_pairs.jsonl'), encoding='utf-8'))}
    opus = {r['id']: r['hu'] for r in map(json.loads, open(os.path.join(DATA, 'hu_opus.jsonl'), encoding='utf-8'))}
    en = {r['id']: r for r in map(json.loads, open(os.path.join(DATA, 'en_prompts.jsonl'), encoding='utf-8'))}
    done = set(json.loads(l)['id'] for l in open(DST, encoding='utf-8')) if os.path.exists(DST) else set()
    ids = [i for i in sorted(en) if i not in done and (i in euro or i in opus)]
    log('to score', len(ids), dev)
    out = open(DST, 'a', encoding='utf-8'); t0 = time.time()
    for k in range(0, len(ids), 24):
        ch = ids[k:k + 24]; cands = []
        for i in ch:
            if i in euro: cands.append((i, 'eurollm', euro[i]['hu']))
            if i in opus: cands.append((i, 'opus', opus[i]))
        b = tok([c[2] for c in cands], return_tensors='pt', padding=True, truncation=True, max_length=400).to(dev)
        with torch.no_grad():
            g = model.generate(**b, num_beams=4, max_new_tokens=500, no_repeat_ngram_size=4)
        back = tok.batch_decode(g, skip_special_tokens=True)
        per = collections.defaultdict(list)
        for (i, src, hu), bk in zip(cands, back):
            per[i].append({'src': src, 'hu': hu, 'back': bk, 'chrf': round(chrf(bk, en[i]['en']), 4)})
        for i in ch:
            out.write(json.dumps({'id': i, 'en': en[i]['en'], 'nsfw': en[i].get('nsfw', 0), 'cands': per[i]}, ensure_ascii=False) + '\n')
        out.flush()
        if (k // 24) % 50 == 0:
            n = k + len(ch); log('%d / %d (%.1f/s)' % (n, len(ids), n / (time.time() - t0)))
    log('done')
if __name__ == '__main__':
    try: main()
    except Exception:
        import traceback; log('ERROR', traceback.format_exc()); sys.exit(1)

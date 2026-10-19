# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Step 7: translate the held-out test prompts (eval/*.tsv, never used for training) with the original opus-mt-hu-en and
# with the fine-tuned model, and write both next to the reference translation for review.
#   out: data/07_eval.json, data/07_eval.txt
import glob, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); DATA = os.path.join(HERE, 'data')
MODELS = os.path.join(ROOT, 'ComfyUI_windows_portable', 'ComfyUI', 'models')
CANDS = {'base': os.path.join(MODELS, 'mt-test', 'opus-mt-hu-en'), 'tuned': os.path.join(MODELS, 'translate', 'artflawless-hu-en'),
         'tuned_big': os.path.join(MODELS, 'translate', 'artflawless-hu-en-big')}
SPLIT = {'base'}   # the original model drops sentences when it gets several at once, so it gets them one by one


def main():
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    tests = []
    for f in sorted(glob.glob(os.path.join(HERE, 'eval', '*.tsv'))):
        for line in open(f, encoding='utf-8'):
            if line.startswith('#') or '\t' not in line:
                continue
            hu, ref = line.rstrip('\n').split('\t')[:2]
            tests.append({'set': os.path.basename(f), 'hu': hu, 'ref': ref})
    for name, path in CANDS.items():
        if not os.path.isdir(path):
            continue
        tok = MarianTokenizer.from_pretrained(path); model = MarianMTModel.from_pretrained(path).to(dev).eval()
        t0 = time.time()
        for i in range(0, len(tests), 16):
            ch = tests[i:i + 16]
            if name in SPLIT:
                for t in ch:
                    parts = [x for x in re.split(r'(?<=[.!?])\s+', t['hu']) if x]
                    b = tok(parts, return_tensors='pt', padding=True, truncation=True, max_length=256).to(dev)
                    with torch.no_grad():
                        g = model.generate(**b, num_beams=4, max_new_tokens=300, no_repeat_ngram_size=4)
                    t[name] = ' '.join(x.strip() for x in tok.batch_decode(g, skip_special_tokens=True))
                continue
            b = tok([t['hu'] for t in ch], return_tensors='pt', padding=True, truncation=True, max_length=256).to(dev)
            with torch.no_grad():
                g = model.generate(**b, num_beams=4, max_new_tokens=300, no_repeat_ngram_size=4)
            for t, o in zip(ch, tok.batch_decode(g, skip_special_tokens=True)):
                t[name] = o.strip()
        print(name, round(time.time() - t0, 1), 's', flush=True)
        del model
    tag = os.environ.get('MT_EVAL_TAG', '')
    json.dump(tests, open(os.path.join(DATA, '07_eval%s.json' % tag), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, '07_eval%s.txt' % tag), 'w', encoding='utf-8') as f:
        for i, t in enumerate(tests, 1):
            f.write('%d. [%s]\nHU   : %s\nREF  : %s\nBASE : %s\nTUNED: %s\nBIG  : %s\n\n' % (i, t['set'], t['hu'], t['ref'], t.get('base', ''), t.get('tuned', ''), t.get('tuned_big', '')))
    print('done', len(tests))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback; traceback.print_exc(); sys.exit(1)

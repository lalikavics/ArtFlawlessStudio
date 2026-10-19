# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Step 3: a second Hungarian candidate for every English prompt, from opus-mt-en-hu (Helsinki-NLP) on the GPU.
#   in : data/en_prompts.jsonl      out: data/hu_opus.jsonl ({"id", "hu"}), resumable
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); DATA = os.path.join(HERE, 'data')
MDIR = os.path.join(ROOT, 'ComfyUI_windows_portable', 'ComfyUI', 'models', 'mt-test')
SRC, DST = os.path.join(DATA, 'en_prompts.jsonl'), os.path.join(DATA, 'hu_opus.jsonl')
LOG = open(os.path.join(DATA, '03_opus_en_hu.log'), 'a', encoding='utf-8')
def log(*a):
    s = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
def main():
    import torch
    from huggingface_hub import snapshot_download
    from transformers import MarianMTModel, MarianTokenizer
    p = snapshot_download('Helsinki-NLP/opus-mt-en-hu', local_dir=os.path.join(MDIR, 'opus-mt-en-hu'),
                          allow_patterns=['*.json', '*.spm', '*.txt', 'pytorch_model.bin', '*.safetensors', 'vocab*'])
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    tok = MarianTokenizer.from_pretrained(p); model = MarianMTModel.from_pretrained(p).to(dev).eval()
    if dev == 'cuda': model = model.half()
    rows = [json.loads(l) for l in open(SRC, encoding='utf-8')]
    done = set(json.loads(l)['id'] for l in open(DST, encoding='utf-8')) if os.path.exists(DST) else set()
    todo = [r for r in rows if r['id'] not in done]
    log('to do', len(todo), dev)
    out = open(DST, 'a', encoding='utf-8'); t0 = time.time()
    for i in range(0, len(todo), 48):
        ch = todo[i:i + 48]
        b = tok([r['en'] for r in ch], return_tensors='pt', padding=True, truncation=True, max_length=400).to(dev)
        with torch.no_grad():
            g = model.generate(**b, num_beams=4, max_new_tokens=500, no_repeat_ngram_size=4)
        for r, hu in zip(ch, tok.batch_decode(g, skip_special_tokens=True)):
            out.write(json.dumps({'id': r['id'], 'hu': hu.strip()}, ensure_ascii=False) + '\n')
        out.flush()
        if (i // 48) % 50 == 0:
            n = i + len(ch); log('%d / %d (%.1f/s)' % (n, len(todo), n / (time.time() - t0)))
    log('done')
if __name__ == '__main__':
    try: main()
    except Exception:
        import traceback; log('ERROR', traceback.format_exc()); sys.exit(1)

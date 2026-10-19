# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Step 11: make the distributable translator from the best fine-tuned big model:
#   fp16 weights + tokenizer + model card -> models/translate/artflawless-hu-en-v1
# then time it on CPU (fp32) and GPU (fp16) and check that fp16 gives the same translations.
import glob, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MODELS = os.path.join(ROOT, 'ComfyUI_windows_portable', 'ComfyUI', 'models')
SRC = os.path.join(MODELS, 'translate', os.environ.get('MT_SRC', 'artflawless-hu-en-big'))
DST = os.path.join(MODELS, 'translate', 'artflawless-hu-en-v1')
CARD = """---
license: cc-by-4.0
language: [hu, en]
base_model: Helsinki-NLP/opus-mt-tc-big-hu-en
pipeline_tag: translation
tags: [translation, marian, prompt, text-to-image]
---
# ArtFlawless HU→EN prompt translator v1

Hungarian → English translator fine-tuned for text-to-image prompts (people, photography, art styles, scenes).
English words and phrases inside a Hungarian prompt (e.g. "golden hour, 85mm, film grain") are kept as they are.
Made for [ArtFlawless Studio](https://github.com/Lalikavics/ArtFlawlessStudio); runs locally, offline.

* Base model: [Helsinki-NLP/opus-mt-tc-big-hu-en](https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-hu-en) (CC-BY 4.0), by the Language Technology Research Group at the University of Helsinki (OPUS-MT, Tiedemann et al.).
* Fine-tuning data: English prompts from [DiffusionDB](https://huggingface.co/datasets/poloclub/diffusiondb) (CC0) translated to Hungarian with [EuroLLM-1.7B-Instruct](https://huggingface.co/utter-project/EuroLLM-1.7B-Instruct) (Apache-2.0) and [opus-mt-en-hu](https://huggingface.co/Helsinki-NLP/opus-mt-en-hu) (CC-BY 4.0), filtered by round-trip quality, plus about 1,800 hand-written prompt pairs.
* Weights: fp16, about %d MB.
* Changes compared with the base model: fine-tuned weights only; architecture and tokenizer unchanged.

## License
CC-BY 4.0, same as the base model. Attribution: Helsinki-NLP / OPUS-MT (base model) and Lalikavics / ArtFlawless Studio (fine-tuning).

## Use
```python
from transformers import MarianMTModel, MarianTokenizer
tok = MarianTokenizer.from_pretrained("artflawless-hu-en-v1"); model = MarianMTModel.from_pretrained("artflawless-hu-en-v1")
b = tok(["vöröshajú nő, szeplők, őszi erdő, golden hour"], return_tensors="pt", padding=True)
print(tok.batch_decode(model.generate(**b, num_beams=4, max_new_tokens=300), skip_special_tokens=True))
```
"""


def tests():
    out = []
    for f in sorted(glob.glob(os.path.join(HERE, 'eval', '*.tsv'))):
        for line in open(f, encoding='utf-8'):
            if line.startswith('#') or '\t' not in line:
                continue
            out.append(line.split('\t')[0])
    return out


def run(model, tok, items, dev):
    import torch
    res = []
    for i in range(0, len(items), 16):
        b = tok(items[i:i + 16], return_tensors='pt', padding=True, truncation=True, max_length=256).to(dev)
        with torch.no_grad():
            g = model.generate(**b, num_beams=4, max_new_tokens=300, no_repeat_ngram_size=4)
        res += [x.strip() for x in tok.batch_decode(g, skip_special_tokens=True)]
    return res


def main():
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    tok = MarianTokenizer.from_pretrained(SRC)
    m = MarianMTModel.from_pretrained(SRC, dtype=torch.float32)
    m.half().save_pretrained(DST, safe_serialization=True); tok.save_pretrained(DST)
    for junk in ('training_args.bin',):
        p = os.path.join(DST, junk)
        if os.path.exists(p):
            os.remove(p)
    files = {}
    for f in sorted(os.listdir(DST)):
        files[f] = os.path.getsize(os.path.join(DST, f))
    mb = files.get('model.safetensors', 0) // (1024 * 1024)
    open(os.path.join(DST, 'README.md'), 'w', encoding='utf-8').write(CARD % mb)
    files['README.md'] = os.path.getsize(os.path.join(DST, 'README.md'))
    print('files', json.dumps(files, indent=1), flush=True)
    json.dump(files, open(os.path.join(HERE, 'data', 'v1_files.json'), 'w'), indent=1)
    items = tests()
    short = ['vöröshajú nő, szeplők, zöld szem, kötött pulóver, őszi erdő, avar, aranyóra, 85mm, f/1.8, bokeh']
    long_ = [' '.join(items[:4])]
    # CPU, fp32
    torch.set_num_threads(max(1, min(8, (os.cpu_count() or 4))))
    t0 = time.time(); mc = MarianMTModel.from_pretrained(DST, dtype=torch.float32).eval(); print('cpu load', round(time.time() - t0, 2), 's', flush=True)
    for name, x in (('short', short), ('long', long_)):
        run(mc, tok, x, 'cpu'); t0 = time.time(); o = run(mc, tok, x, 'cpu'); print('cpu', name, round(time.time() - t0, 2), 's ->', o[0][:160], flush=True)
    cpu_all = run(mc, tok, items, 'cpu'); del mc
    if torch.cuda.is_available():
        t0 = time.time(); mg = MarianMTModel.from_pretrained(DST, dtype=torch.float16).to('cuda').eval(); torch.cuda.synchronize(); print('gpu load', round(time.time() - t0, 2), 's', flush=True)
        for name, x in (('short', short), ('long', long_)):
            run(mg, tok, x, 'cuda'); t0 = time.time(); o = run(mg, tok, x, 'cuda'); torch.cuda.synchronize(); print('gpu', name, round(time.time() - t0, 2), 's', flush=True)
        print('gpu vram MB', torch.cuda.max_memory_allocated() // (1024 * 1024))
        gpu_all = run(mg, tok, items, 'cuda')
        diff = [(a, b) for a, b in zip(cpu_all, gpu_all) if a != b]
        print('fp16 vs fp32 differences:', len(diff), 'of', len(items))
        for a, b in diff[:15]:
            print(' fp32:', a, '\n fp16:', b)
    print('done')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback; traceback.print_exc(); sys.exit(1)

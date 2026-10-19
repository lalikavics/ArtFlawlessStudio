# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Step 2 of the Hungarian prompt translator: write the Hungarian side of the training pairs.
# EuroLLM-1.7B-Instruct (Apache-2.0) translates the English DiffusionDB prompts into Hungarian on the GPU.
#   in : data/en_prompts.jsonl      out: data/hu_pairs.jsonl ({"id", "en", "hu"}), resumable
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, 'data')
MODEL = os.path.join(ROOT, 'ComfyUI_windows_portable', 'ComfyUI', 'models', 'mt-test', 'EuroLLM-1.7B-Instruct')
SRC, DST = os.path.join(DATA, 'en_prompts.jsonl'), os.path.join(DATA, 'hu_pairs.jsonl')
BATCH = int(os.environ.get('MT_BATCH', '24'))
LIMIT = int(os.environ.get('MT_LIMIT', '0'))          # 0 = all
LOG = open(os.path.join(DATA, '02_translate.log'), 'a', encoding='utf-8')


def log(*a):
    s = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a)
    print(s, flush=True); LOG.write(s + '\n'); LOG.flush()


SYSTEM = ("You translate English prompts for an AI image generator into natural, fluent Hungarian, the way a Hungarian person "
          "would write them. Translate every ordinary word and phrase, including photography and art terms that have a usual "
          "Hungarian form. Keep unchanged: names of people, artists, characters, places, brands, films, games and software "
          "(for example Unreal Engine, Octane render, ArtStation), numbers, resolutions and camera settings. Keep the structure: "
          "sentences stay sentences, comma-separated lists stay comma-separated lists. Do not add or leave out anything. "
          "Output only the Hungarian translation.")
SHOTS = [
    ("portrait of an old fisherman with a weathered face, golden hour, shallow depth of field, 85mm, film grain, by Annie Leibovitz",
     "egy öreg halász portréja cserzett arccal, aranyóra, kis mélységélesség, 85mm, filmszemcse, Annie Leibovitz stílusában"),
    ("A cozy reading nook by a rain-streaked window, a steaming mug on a small wooden table. Warm lamp light, soft evening atmosphere, octane render, 8k",
     "Hangulatos olvasósarok egy esőcseppes ablak mellett, egy kis fa asztalon gőzölgő bögre. Meleg lámpafény, lágy esti hangulat, octane render, 8k"),
]


def main():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    rows = [json.loads(l) for l in open(SRC, encoding='utf-8')]
    if LIMIT:
        rows = rows[:LIMIT]
    done = set()
    if os.path.exists(DST):
        for l in open(DST, encoding='utf-8'):
            try:
                done.add(json.loads(l)['id'])
            except Exception:
                pass
    todo = [r for r in rows if r['id'] not in done]
    log('total', len(rows), 'already done', len(done), 'to do', len(todo), 'cuda', torch.cuda.is_available())
    if not todo:
        log('nothing to do'); return
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    tok = AutoTokenizer.from_pretrained(MODEL)
    tok.padding_side = 'left'
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16 if dev == 'cuda' else torch.float32).to(dev).eval()
    base = [{'role': 'system', 'content': SYSTEM}]
    for en, hu in SHOTS:
        base += [{'role': 'user', 'content': en}, {'role': 'assistant', 'content': hu}]
    out = open(DST, 'a', encoding='utf-8')
    t0, n = time.time(), 0
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        texts = [tok.apply_chat_template(base + [{'role': 'user', 'content': r['en']}], tokenize=False, add_generation_prompt=True) for r in chunk]
        enc = tok(texts, return_tensors='pt', padding=True, add_special_tokens=False).to(dev)
        longest = max(len(tok(r['en'], add_special_tokens=False)['input_ids']) for r in chunk)
        with torch.no_grad():
            g = model.generate(**enc, max_new_tokens=min(512, int(longest * 2.2) + 24), do_sample=False,
                               repetition_penalty=1.05, no_repeat_ngram_size=4, pad_token_id=tok.pad_token_id)
        res = tok.batch_decode(g[:, enc['input_ids'].shape[1]:], skip_special_tokens=True)
        for r, hu in zip(chunk, res):
            out.write(json.dumps({'id': r['id'], 'en': r['en'], 'hu': hu.strip(), 'nsfw': r.get('nsfw', 0)}, ensure_ascii=False) + '\n')
        out.flush()
        n += len(chunk)
        if (i // BATCH) % 10 == 0 or n == len(todo):
            rate = n / max(1e-6, time.time() - t0)
            log('%d / %d  (%.2f prompts/s, about %.0f min left)' % (len(done) + n, len(rows), rate, (len(todo) - n) / max(rate, 1e-6) / 60))
    log('done')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        log('ERROR', traceback.format_exc())
        sys.exit(1)

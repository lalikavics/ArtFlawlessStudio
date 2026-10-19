# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Step 6: fine-tune opus-mt-hu-en (Helsinki-NLP, MarianMT) on the image-prompt pairs. Plain PyTorch loop (no extra
# packages), bf16 autocast on the GPU. The best checkpoint by validation loss goes to
#   ComfyUI\models\translate\artflawless-hu-en\   (model + tokenizer files, ready for the Studio)
import json, math, os, random, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); DATA = os.path.join(HERE, 'data')
MODELS = os.path.join(ROOT, 'ComfyUI_windows_portable', 'ComfyUI', 'models')
BASE_REPO = os.environ.get('MT_BASE', 'Helsinki-NLP/opus-mt-hu-en')
BASE = os.path.join(MODELS, 'mt-test', BASE_REPO.split('/')[-1])
OUT = os.path.join(MODELS, 'translate', os.environ.get('MT_OUT', 'artflawless-hu-en'))
EPOCHS = float(os.environ.get('MT_EPOCHS', '5'))
LR = float(os.environ.get('MT_LR', '5e-5'))
BATCH_TOKENS = int(os.environ.get('MT_BATCH_TOKENS', '6000'))
MAXLEN = 256
AMP = os.environ.get('MT_AMP', '1') == '1'   # bf16 autocast; the big tc model needs it off (its loss turns into NaN)
LOG = open(os.path.join(DATA, '06_train.log'), 'a', encoding='utf-8')
random.seed(11)


def log(*a):
    s = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()


def read(name):
    out = []
    for line in open(os.path.join(DATA, name), encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if len(p) >= 2 and p[0] and p[1]:
            out.append((p[0], p[1]))
    return out


def batches(tok, pairs, shuffle=True):
    enc = [(tok(hu, truncation=True, max_length=MAXLEN)['input_ids'], tok(text_target=en, truncation=True, max_length=MAXLEN)['input_ids']) for hu, en in pairs]
    order = sorted(range(len(enc)), key=lambda i: len(enc[i][0]) + random.random())
    out, cur, longest = [], [], 0
    for i in order:
        l = max(len(enc[i][0]), len(enc[i][1]))
        if cur and max(longest, l) * (len(cur) + 1) > BATCH_TOKENS:
            out.append(cur); cur, longest = [], 0
        cur.append(enc[i]); longest = max(longest, l)
    if cur:
        out.append(cur)
    if shuffle:
        random.shuffle(out)
    return out


def collate(tok, b, dev):
    import torch
    pad = tok.pad_token_id
    ml, tl = max(len(x) for x, _ in b), max(len(y) for _, y in b)
    ids = torch.full((len(b), ml), pad); att = torch.zeros((len(b), ml), dtype=torch.long); lab = torch.full((len(b), tl), -100)
    for i, (x, y) in enumerate(b):
        ids[i, :len(x)] = torch.tensor(x); att[i, :len(x)] = 1; lab[i, :len(y)] = torch.tensor(y)
    return ids.to(dev), att.to(dev), lab.to(dev)


def main():
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    if not os.path.isdir(BASE):
        from huggingface_hub import snapshot_download
        snapshot_download(BASE_REPO, local_dir=BASE, allow_patterns=['*.json', '*.spm', '*.txt', 'pytorch_model.bin', '*.safetensors', 'vocab*'])
    tok = MarianTokenizer.from_pretrained(BASE)
    model = MarianMTModel.from_pretrained(BASE, dtype=torch.float32).to(dev)   # some checkpoints (tc-big) are stored in fp16
    train, valid = read('train.tsv'), read('valid.tsv')
    log('train', len(train), 'valid', len(valid), 'device', dev)
    vb = batches(tok, valid, shuffle=False)
    steps_per_epoch = len(batches(tok, train))
    total = int(steps_per_epoch * EPOCHS); warm = min(500, total // 10)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / warm) * max(0.05, 1 - s / total))

    def evaluate():
        model.eval(); tot, n = 0.0, 0
        with torch.no_grad():
            for b in vb:
                ids, att, lab = collate(tok, b, dev)
                with torch.autocast(dev, dtype=torch.bfloat16, enabled=AMP and dev == 'cuda'):
                    loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
                tot += loss.item() * len(b); n += len(b)
        model.train(); return tot / max(1, n)

    best = evaluate(); log('start valid loss %.4f, %d steps' % (best, total))
    step, t0, skipped = 0, time.time(), 0; model.train()
    while step < total:
        for b in batches(tok, train):
            ids, att, lab = collate(tok, b, dev)
            with torch.autocast(dev, dtype=torch.bfloat16, enabled=AMP and dev == 'cuda'):
                loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
            if not torch.isfinite(loss):
                opt.zero_grad(set_to_none=True); step += 1; sched.step(); log('step %d: loss not finite, skipped' % step); continue
            loss.backward(); gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            if not torch.isfinite(gn):
                # one bad batch must not destroy the weights (seen with opus-mt-tc-big): skip the update
                opt.zero_grad(set_to_none=True); step += 1; sched.step(); skipped += 1
                if skipped <= 20 or skipped % 100 == 0:
                    log('step %d: gradient not finite, update skipped (%d so far)' % (step, skipped))
                continue
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True); step += 1
            if step % 100 == 0:
                log('step %d / %d  loss %.4f  lr %.2e  %.1f min' % (step, total, loss.item(), sched.get_last_lr()[0], (time.time() - t0) / 60))
            if step % max(200, steps_per_epoch // 3) == 0 or step >= total:
                v = evaluate(); log('valid loss %.4f (best %.4f)' % (v, best))
                if v < best:
                    best = v; os.makedirs(OUT, exist_ok=True)
                    model.save_pretrained(OUT); tok.save_pretrained(OUT)
                    json.dump({'step': step, 'valid_loss': round(v, 4), 'base': BASE_REPO,
                               'data': 'DiffusionDB (CC0) + ArtFlawless hand-written pairs'}, open(os.path.join(OUT, 'artflawless_train.json'), 'w'), indent=2)
                    log('saved', OUT)
            if step >= total:
                break
    log('done, best valid loss %.4f' % best)
    # keep every trained version: copy the best checkpoint into a dated archive folder
    if os.path.isdir(OUT):
        import shutil
        arch = os.path.join(os.path.dirname(OUT), 'archive', time.strftime('%Y-%m-%d_%H%M_') + os.path.basename(OUT))
        shutil.copytree(OUT, arch); log('archived', arch)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback; log('ERROR', traceback.format_exc()); sys.exit(1)

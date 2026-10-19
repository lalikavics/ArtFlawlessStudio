# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Step 5: build the training set.
#  - synthetic pairs: the best Hungarian candidate per prompt if its round-trip chrF is high enough (and a second
#    candidate too when both are very good); loops and odd lengths are dropped
#  - mixed-language pairs: some list items stay in English on the Hungarian side, the target is unchanged,
#    so the model learns to copy English words instead of translating them
#  - hand-written pairs (handmade/train_*.tsv), repeated a few times
#   out: data/train.tsv, data/valid.tsv, data/05_build.json   (eval/*.tsv is never used for training)
import collections, glob, json, os, random, re

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, 'data')
random.seed(7)
MIN_CHRF = float(os.environ.get('MT_MIN_CHRF', '0'))   # 0 = pick automatically (about 60 % of the prompts)
HAND_REPEAT = int(os.environ.get('MT_HAND_REPEAT', '10'))


def loops(t):
    w = t.lower().split()
    tri = collections.Counter(zip(w, w[1:], w[2:]))
    return bool(tri) and tri.most_common(1)[0][1] > 2


def ok_len(en, hu):
    r = len(hu) / max(1, len(en))
    return 0.55 <= r <= 2.2


def tsv(s):
    return re.sub(r'[\t\r\n]+', ' ', s).strip()


def main():
    rows = [json.loads(l) for l in open(os.path.join(DATA, 'scored.jsonl'), encoding='utf-8')]
    # each translator is judged against its own scores: opus-mt-en-hu round-trips through its own family more easily,
    # a shared threshold would leave almost only its (more literal) Hungarian in the data
    by_src = collections.defaultdict(list)
    for r in rows:
        for c in r['cands']:
            by_src[c['src']].append(c['chrf'])
    thr = {}
    for src, v in by_src.items():
        v.sort()
        thr[src] = MIN_CHRF or max(0.55, v[int(len(v) * 0.40)])
    pairs, stats = [], collections.Counter()
    for r in rows:
        good = [c for c in r['cands'] if ok_len(r['en'], c['hu']) and not loops(c['hu']) and c['chrf'] >= thr[c['src']]]
        if not good:
            stats['dropped (round trip)'] += 1; continue
        seen = set()
        for c in sorted(good, key=lambda c: -c['chrf']):
            if c['hu'] in seen:
                continue
            seen.add(c['hu']); pairs.append((c['hu'], r['en'], 'syn-' + c['src'])); stats['kept ' + c['src']] += 1
    # English tags that people paste after a Hungarian description ("..., cinematic lighting, volumetric fog")
    tagc = collections.Counter()
    for r in rows:
        for t in r['en'].split(','):
            t = t.strip().lower()
            if 1 <= len(t.split()) <= 3 and 3 <= len(t) <= 30 and re.fullmatch(r"[a-z0-9 .'/-]+", t):
                tagc[t] += 1
    tags = [t for t, n in tagc.most_common(600) if n >= 15 and not re.search(r'\b(by|and|of|in)\b', t)]
    stats['english tag pool'] = len(tags)
    # mixed-language: comma lists with the same number of items on both sides
    mixed = []
    for hu, en, src in pairs:
        hi, ei = [x.strip() for x in hu.split(',')], [x.strip() for x in en.split(',')]
        if len(hi) >= 4 and len(hi) == len(ei) and random.random() < 0.25:
            k = random.sample(range(len(hi)), random.randint(1, max(1, len(hi) // 3)))
            for j in k:
                hi[j] = ei[j]
            mixed.append((', '.join(hi), en, 'mixed'))
    stats['mixed-language'] = len(mixed)
    hand = []
    for f in sorted(glob.glob(os.path.join(HERE, 'handmade', 'train_*.tsv'))):
        for line in open(f, encoding='utf-8'):
            if '\t' in line and not line.startswith('#'):
                hu, en = line.rstrip('\n').split('\t')[:2]
                if hu.strip() and en.strip():
                    hand.append((hu.strip(), en.strip(), 'hand'))
    stats['hand-written'] = len(hand)
    tagged = []
    base = [p for p in pairs if p[0].count(',') < 3] + hand
    for hu, en, src in random.sample(base, min(len(base), 7000)):
        k = random.sample(tags, random.randint(1, 3))
        hu2, en2 = hu.rstrip(' .'), en.rstrip(' .')
        tagged.append((hu2 + ', ' + ', '.join(k), en2 + ', ' + ', '.join(k), 'tags'))
    stats['sentence + english tags'] = len(tagged)
    allp = pairs + mixed + tagged + hand * HAND_REPEAT
    random.shuffle(allp)
    nval = max(200, len(allp) // 100)
    val, train = allp[:nval], allp[nval:]
    for name, part in (('train.tsv', train), ('valid.tsv', val)):
        with open(os.path.join(DATA, name), 'w', encoding='utf-8') as f:
            for hu, en, src in part:
                f.write('%s\t%s\t%s\n' % (tsv(hu), tsv(en), src))
    info = {'threshold_chrf': {k: round(v, 3) for k, v in thr.items()}, 'train': len(train), 'valid': len(val), **stats}
    json.dump(info, open(os.path.join(DATA, '05_build.json'), 'w', encoding='utf-8'), indent=2)
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()

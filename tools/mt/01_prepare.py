# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# Step 1 of the Hungarian prompt translator: collect clean English image prompts from DiffusionDB (CC0 1.0).
#   in : poloclub/diffusiondb  metadata.parquet  (2 million rows, column "prompt")
#   out: data/en_prompts.jsonl (one {"id", "en", "nsfw"} per line), data/stats.json, data/review_sample.txt
# Adult prompts are kept. Always removed: prompts that combine minors with sexual content, and sexual violence.
import collections, hashlib, json, os, random, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
TARGET = int(os.environ.get('MT_TARGET', '45000'))
random.seed(1234)
os.makedirs(DATA, exist_ok=True)
LOG = open(os.path.join(DATA, '01_prepare.log'), 'a', encoding='utf-8')


def log(*a):
    s = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a)
    print(s); LOG.write(s + '\n'); LOG.flush()


# ---------- cleaning ----------
WEIGHT = re.compile(r'\(([^()]*?):\s*-?\d+(?:\.\d+)?\)')          # (word:1.2) -> word
BRACK = re.compile(r'[\[\]{}()]+')                                  # ((masterpiece)) [x] {y} -> plain
ARGS = re.compile(r'(?<!\S)--?[a-z]+(?:\s+[\w:./-]+)?', re.I)        # midjourney style --ar 16:9, --v 5
URL = re.compile(r'https?://\S+|www\.\S+', re.I)
SPACES = re.compile(r'\s+')
COMMAS = re.compile(r'\s*,[\s,]*')
SPLITDIG = re.compile(r'(?<=\d) (?=\d)')                            # DiffusionDB stores "1 9 6 9", "4 k", "5 0 mm"
DIGUNIT = re.compile(r'\b(\d+) (k|mm|d|px|fps|s)\b', re.I)
HYPH = re.compile(r'(?<=\w) - (?=\w)')                               # "sci - fi" -> "sci-fi"
PARAMS = re.compile(r'\b[hwn] ?- ?\d+\b', re.I)                     # leftovers like "h-1024 w-1024 n-9"
EN_WORDS = set('a an the of in on with and at by from to for under over into through near behind beside wearing holding standing sitting walking '
               'portrait photo photograph painting illustration art style light lighting detailed realistic background woman man girl boy city '
               'forest sky night sunset beautiful old young dark red blue green black white golden is are her his their its'.split())


def clean(p):
    p = URL.sub(' ', p)
    for _ in range(4):
        p = SPLITDIG.sub('', p)
    p = DIGUNIT.sub(r'\1\2', p)
    p = HYPH.sub('-', p)
    p = PARAMS.sub(' ', p)
    for _ in range(3):
        p = WEIGHT.sub(r'\1', p)
    p = ARGS.sub(' ', p)
    p = BRACK.sub(' ', p)
    p = p.replace('|', ', ').replace(';', ',')
    p = COMMAS.sub(', ', SPACES.sub(' ', p)).strip(' ,.')
    return p


def is_junk(p):
    if not (20 <= len(p) <= 420):
        return 'length'
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", p)
    if len(words) < 4:
        return 'few words'
    letters = sum(c.isalpha() for c in p)
    if letters < 0.6 * len(p.replace(' ', '')):
        return 'symbols'
    if sum(c.isascii() for c in p) < 0.97 * len(p):
        return 'non-English letters'
    low = [w.lower() for w in words]
    if not (set(low) & EN_WORDS):
        return 'no English'
    cnt = collections.Counter(low)
    if cnt.most_common(1)[0][1] > max(4, len(low) // 3):
        return 'repetition'
    items = [x for x in p.split(',') if x.strip()]
    if len(items) > 45:
        return 'tag soup'
    caps = sum(1 for w in words if w[0].isupper())
    if len(words) >= 8 and caps > 0.7 * len(words):
        return 'name list'
    return None


# ---------- safety: these are never used for training ----------
MINOR = re.compile(r"\b(child|children|kid|kids|toddler|baby|babies|infant|preteen|pre-teen|tween|teen|teens|teenage|teenager|underage|"
                   r"under-age|minor|minors|schoolgirl|schoolboy|school girl|school boy|loli|lolita|shota|little girl|little boy|young girl|"
                   r"young boy|daughter|son|elementary|kindergarten|(?:[1-9]|1[0-7])[ -]?(?:yo|y/o|years? old|year-old))\b", re.I)
SEXUAL = re.compile(r"\b(nude|nudes|naked|nudity|topless|bottomless|nsfw|sex|sexy|sexual|erotic|porn|porno|pornographic|hentai|lingerie|"
                    r"underwear|bikini|breasts?|boobs?|nipples?|genitals?|penis|vagina|pussy|ass|butt|buttocks|crotch|orgasm|seductive|"
                    r"aroused|fetish|bdsm|spread legs|undressed|undressing|cleavage)\b", re.I)
ALWAYS = re.compile(r"\b(loli|lolicon|shota|shotacon|preteen|underage|child porn|cp)\b", re.I)
VIOLENT_SEX = re.compile(r"\b(rape|raped|raping|non-?consensual|sexual assault|molest\w*|forced sex)\b", re.I)


def unsafe(p):
    if ALWAYS.search(p) or VIOLENT_SEX.search(p):
        return True
    return bool(MINOR.search(p) and SEXUAL.search(p))


def main():
    from huggingface_hub import hf_hub_download
    import polars as pl
    log('download DiffusionDB metadata.parquet (once)')
    path = hf_hub_download('poloclub/diffusiondb', 'metadata.parquet', repo_type='dataset', local_dir=os.path.join(DATA, 'diffusiondb'))
    log('file', path, round(os.path.getsize(path) / 1e6), 'MB')
    df = pl.read_parquet(path, columns=['prompt', 'prompt_nsfw'])
    log('rows', df.height)
    df = df.group_by('prompt').agg(pl.col('prompt_nsfw').max())
    log('unique prompts', df.height)

    stats = collections.Counter()
    seen, prefix = set(), collections.Counter()
    keep = []
    rows = list(zip(df['prompt'].to_list(), df['prompt_nsfw'].to_list()))
    random.shuffle(rows)
    for raw, nsfw in rows:
        if not raw:
            stats['empty'] += 1; continue
        p = clean(raw)
        why = is_junk(p)
        if why:
            stats['junk: ' + why] += 1; continue
        if unsafe(p):
            stats['removed: minors/sexual violence'] += 1; continue
        key = hashlib.md5(re.sub(r'[^a-z]+', ' ', p.lower()).strip().encode()).hexdigest()
        if key in seen:
            stats['near duplicate'] += 1; continue
        pre = ' '.join(p.lower().split()[:5])
        if prefix[pre] >= 3:
            stats['same start (spam variants)'] += 1; continue
        seen.add(key); prefix[pre] += 1
        keep.append({'en': p, 'nsfw': round(float(nsfw or 0), 3)})
        stats['kept'] += 1
        if len(keep) >= TARGET:
            break
    for i, k in enumerate(keep):
        k['id'] = i
    with open(os.path.join(DATA, 'en_prompts.jsonl'), 'w', encoding='utf-8') as f:
        for k in keep:
            f.write(json.dumps(k, ensure_ascii=False) + '\n')
    lens = sorted(len(k['en']) for k in keep)
    info = {'kept': len(keep), 'filters': dict(stats.most_common()), 'median_chars': lens[len(lens) // 2] if lens else 0,
            'share_nsfw_over_0.5': round(sum(k['nsfw'] > 0.5 for k in keep) / max(1, len(keep)), 3),
            'share_lists': round(sum(k['en'].count(',') >= 3 for k in keep) / max(1, len(keep)), 3)}
    json.dump(info, open(os.path.join(DATA, 'stats.json'), 'w', encoding='utf-8'), indent=2)
    with open(os.path.join(DATA, 'review_sample.txt'), 'w', encoding='utf-8') as f:
        for k in random.sample(keep, min(300, len(keep))):
            f.write(k['en'] + '\n')
    log('done', json.dumps(info))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        log('ERROR', traceback.format_exc())
        sys.exit(1)

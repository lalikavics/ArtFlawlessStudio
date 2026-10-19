# Check whether a larger Hungarian->English opus-mt model exists on Hugging Face (only its config is downloaded).
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
from huggingface_hub import hf_hub_download
out = {}
for repo in ('Helsinki-NLP/opus-mt-tc-big-hu-en', 'Helsinki-NLP/opus-mt-tc-big-fiu-en', 'Helsinki-NLP/opus-mt-fiu-en', 'Helsinki-NLP/opus-mt-mul-en'):
    try:
        p = hf_hub_download(repo, 'config.json', local_dir=os.path.join(HERE, 'data', 'probe', repo.replace('/', '_')))
        c = json.load(open(p, encoding='utf-8'))
        out[repo] = {'ok': True, 'd_model': c.get('d_model'), 'layers': [c.get('encoder_layers'), c.get('decoder_layers')], 'vocab': c.get('vocab_size')}
    except Exception as e:
        out[repo] = {'ok': False, 'error': str(e)[:200]}
json.dump(out, open(os.path.join(HERE, 'data', '08_probe.json'), 'w'), indent=2)
print(json.dumps(out, indent=2))

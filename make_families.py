# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
"""Build-time: derives the SDXL and Flux templates from the Z-Image Turbo template.
Run after make_studio_files.py:  python3 -I make_families.py
Reads  studio_out/web/template.json, writes studio_out/web/template-sdxl.json and template-flux.json."""
import copy, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, 'studio_out', 'web')
BASE = json.load(open(os.path.join(WEB, 'template.json'), encoding='utf-8'))

THEMES = ["None (own prompt only)", "Portrait", "People – full body", "Landscape – nature", "Architecture – cityscape",
          "Interior", "Product – object – food", "Animal – macro"]

# ---------------------------------------------------------------- theme tables
# steps/cfg = base sampler; refine / upscale = denoise of those passes; lora = base LoRA strength
SDXL_PRESETS = {
    "None (own prompt only)": dict(w=832, h=1216, steps=30, cfg=4.5, lora=0.0, refine=0.3, upscale=0.2, groups="", pre="", post=""),
    "Portrait": dict(people=1, w=832, h=1216, steps=35, cfg=4.0, lora=0.0, refine=0.3, upscale=0.2, groups="2, 3",
                     pre="close-up portrait photograph of ",
                     post=", 85mm lens, shallow depth of field, soft natural light, natural skin texture, sharp focus on the eyes, photorealistic"),
    "People – full body": dict(people=1, w=832, h=1216, steps=35, cfg=4.0, lora=0.0, refine=0.3, upscale=0.2, groups="2, 3, 3b",
                               pre="full body candid photograph of ",
                               post=", natural pose, 35mm lens, shallow depth of field, natural light, realistic proportions, detailed hands, photorealistic"),
    "Landscape – nature": dict(w=1216, h=832, steps=35, cfg=5.5, lora=0.0, refine=0.35, upscale=0.25, groups="2, 4",
                               pre="landscape photograph, ",
                               post=", wide-angle lens, deep depth of field, sharp foreground detail, atmospheric haze, natural colors, highly detailed"),
    "Architecture – cityscape": dict(w=1216, h=832, steps=35, cfg=6.0, lora=0.0, refine=0.3, upscale=0.2, groups="2, 4",
                                     pre="architectural photograph, ",
                                     post=", straight vertical lines, deep depth of field, clean geometric lines, realistic materials, highly detailed"),
    "Interior": dict(w=1216, h=832, steps=35, cfg=5.5, lora=0.0, refine=0.3, upscale=0.2, groups="2, 4",
                     pre="interior design photograph, ",
                     post=", wide-angle lens, natural window light, realistic material textures, tidy room, highly detailed"),
    "Product – object – food": dict(w=1024, h=1024, steps=30, cfg=6.0, lora=0.0, refine=0.25, upscale=0.15, groups="2, 4",
                                    pre="professional product photograph of ",
                                    post=", soft diffused studio lighting, soft shadow, macro lens, centered composition, clean plain backdrop"),
    "Animal – macro": dict(w=1216, h=832, steps=35, cfg=5.0, lora=0.0, refine=0.3, upscale=0.2, groups="2, 4",
                           pre="wildlife photograph of ",
                           post=", telephoto lens, softly blurred background, fine fur texture, catchlight in the eye, natural light"),
}
FLUX_PRESETS = {
    "None (own prompt only)": dict(w=832, h=1216, steps=4, cfg=1.0, lora=0.0, refine=0.2, upscale=0.15, groups="", pre="", post=""),
    "Portrait": dict(people=1, w=832, h=1216, steps=4, cfg=1.0, lora=0.0, refine=0.2, upscale=0.15, groups="2, 3",
                     pre="A photorealistic portrait photograph. ",
                     post=" Shot on an 85mm lens with shallow depth of field, soft natural light, natural skin texture, sharp focus on the eyes. No text, no watermark."),
    "People – full body": dict(people=1, w=832, h=1216, steps=4, cfg=1.0, lora=0.0, refine=0.2, upscale=0.15, groups="2, 3, 3b",
                               pre="A photorealistic candid full-body photograph. ",
                               post=" Natural pose, natural skin texture, 35mm lens, documentary realism, correct anatomy with five fingers on each hand. No text, no watermark."),
    "Landscape – nature": dict(w=1216, h=832, steps=4, cfg=1.0, lora=0.0, refine=0.2, upscale=0.15, groups="2, 4",
                               pre="An ultra detailed, realistic landscape photograph. ",
                               post=" Wide-angle lens, deep depth of field, sharp foreground detail, atmospheric haze in the distance, natural colors. No text, no watermark."),
    "Architecture – cityscape": dict(w=1216, h=832, steps=4, cfg=1.0, lora=0.0, refine=0.2, upscale=0.15, groups="2, 4",
                                     pre="An ultra detailed architectural photograph. ",
                                     post=" Straight vertical lines, deep depth of field, clean geometric lines, realistic materials. No text, no signage, no watermark."),
    "Interior": dict(w=1216, h=832, steps=4, cfg=1.0, lora=0.0, refine=0.2, upscale=0.15, groups="2, 4",
                     pre="An ultra detailed interior design photograph. ",
                     post=" Wide-angle lens with straight vertical lines, natural window light, realistic material textures, tidy room. No text, no watermark."),
    "Product – object – food": dict(w=1024, h=1024, steps=4, cfg=1.0, lora=0.0, refine=0.25, upscale=0.15, groups="2, 4",
                                    pre="A professional close-up product photograph. ",
                                    post=" Soft diffused studio lighting, soft shadow on the surface, macro lens, centered composition, clean plain backdrop. No logos, no text, no watermark."),
    "Animal – macro": dict(w=1216, h=832, steps=4, cfg=1.0, lora=0.0, refine=0.2, upscale=0.15, groups="2, 4",
                           pre="An ultra detailed wildlife and macro photograph. ",
                           post=" Telephoto lens with softly blurred background, fine fur and texture visible, catchlight in the eye, natural light. No text, no watermark."),
}

CUSTOM_PRESETS = {name: dict(w=1024, h=1024, steps=25, cfg=6.0, lora=0.0, refine=0.3, upscale=0.2, groups="", pre="", post="") for name in THEMES}

FAMILIES = {
    'sdxl': dict(label='SDXL', ckpt='Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors', presets=SDXL_PRESETS,
                 sampler='dpmpp_2m', scheduler='karras', latent='EmptyLatentImage', clip_skip=True,
                 refine_steps=20, det_steps=20, det_denoise={'25': 0.35, '30': 0.4, '62': 0.4}, up_steps=20,
                 neg='lowres, blurry, deformed, bad anatomy, bad hands, extra fingers, watermark, text',
                 title='Load checkpoint – SDXL (Juggernaut XL)'),
    'flux': dict(label='Flux', ckpt='flux1-schnell-fp8.safetensors', presets=FLUX_PRESETS,
                 sampler='euler', scheduler='simple', latent='EmptySD3LatentImage', clip_skip=False,
                 # tested on 8 GB: refine/face passes with 4 steps at 0.3 denoise gave blotchy, painted faces;
                 # 10 steps at 0.2-0.3 denoise is clean (slower: about 4 s per step at 1.5x size)
                 refine_steps=10, det_steps=10, det_denoise={'25': 0.2, '30': 0.3, '62': 0.3}, up_steps=10,
                 neg='', title='Load checkpoint – Flux.1 schnell (fp8)'),
    'custom': dict(label='Custom', ckpt='', presets=CUSTOM_PRESETS,
                   sampler='dpmpp_2m', scheduler='karras', latent='EmptyLatentImage', clip_skip=True,
                   refine_steps=20, det_steps=20, det_denoise={'25': 0.35, '30': 0.4, '62': 0.4}, up_steps=20,
                   neg='lowres, blurry, deformed, bad anatomy, watermark, text',
                   title='Load checkpoint – your own model'),
}


def preset_code(presets, base_code):
    """Replace the preset dict of the Z-Image table, and add steps/cfg (+ manual overrides j, k) to the outputs."""
    lines = ['presets = {']
    for name in THEMES:
        p = dict(presets[name]); p.setdefault('people', 0); p['shift'] = 0.0
        pre, post = p.pop('pre'), p.pop('post')
        body = ', '.join(f'"{k}": {json.dumps(v, ensure_ascii=False)}' for k, v in p.items())
        lines.append(f'  {json.dumps(name, ensure_ascii=False)}: {{{body},\n    "pre": {json.dumps(pre, ensure_ascii=False)},\n    "post": {json.dumps(post, ensure_ascii=False)}}},')
    lines.append('}')
    new_dict = '\n'.join(lines)
    i = base_code.index('presets = {')
    j = base_code.index('\n}\n', i) + 2
    code = base_code[:i] + new_dict + base_code[j:]
    header = ('# PRESET TABLE – edit the theme values here.\n'
              '# w, h = image size when ASPECT RATIO is "Theme default"  |  steps, cfg = base sampler (j, k = manual override, 0 = theme)\n'
              '# lora = base LoRA strength, 0 = not used  |  refine = refine denoise  |  upscale = final upscale denoise\n'
              '# groups = recommended steps (shown only)  |  pre = added before the prompt  |  post = added after the prompt\n')
    code = header + code[code.index('presets = {'):]
    # theme steps/cfg with manual override
    code = code.replace('shift = preset["shift"]',
                        'shift = preset["shift"]\nsteps = int(preset["steps"])\ncfg = float(preset["cfg"])\n'
                        'if j and int(j) > 0:\n  steps = int(j)\nif k and float(k) > 0:\n  cfg = round(float(k), 2)')
    assert 'steps = int(preset["steps"])' in code
    code = code.replace('|  Shift: {shift}  |', '|  Steps: {steps}  |  CFG: {cfg}  |')
    code = code.replace('|shift={shift}|', '|shift={shift}|base_steps={steps}|cfg={cfg}|')
    code = code.replace('return (final, wid, hei, shift, lora, refine, upscale, summary, denoise, info)',
                        'return (final, wid, hei, shift, lora, refine, upscale, summary, denoise, info, steps, cfg)')
    assert code.count('steps, cfg)') == 1
    return code


def build(fam):
    F = FAMILIES[fam]
    t = copy.deepcopy(BASE); P = t['prompt']; PASS = t['pass']; G = t['groups']

    def refs_replace(old, new, skip=()):
        for nid, n in P.items():
            if nid in skip: continue
            for k, v in list(n['inputs'].items()):
                if isinstance(v, list) and len(v) == 2 and str(v[0]) == old[0] and v[1] == old[1]:
                    n['inputs'][k] = list(new)

    def delete_passthrough(nid, in_name, slot=0):
        src = P[nid]['inputs'][in_name]
        refs_replace((nid, slot), src)
        del P[nid]; PASS.pop(nid, None)

    # 1) checkpoint loader in place of the Z-Image diffusion-model loader
    P['2'] = {'inputs': {'ckpt_name': F['ckpt']}, 'class_type': 'CheckpointLoaderSimple', '_meta': {'title': F['title']}}
    clip_src = ['2', 1]
    if F['clip_skip']:
        P['120'] = {'inputs': {'stop_at_clip_layer': -1, 'clip': ['2', 1]}, 'class_type': 'CLIPSetLastLayer',
                    '_meta': {'title': 'CLIP skip (Pony needs -2)'}}
        clip_src = ['120', 0]
    refs_replace(('65', 0), clip_src, skip=('83',))     # the Qwen3 encoder stays only for the style extractor (1c)
    P['65']['_meta'] = {'title': 'Qwen3 4B – used only by the style extractor (1c)'}
    refs_replace(('66', 0), ['2', 2])
    del P['66']
    # 2) no AuraFlow sampling shift
    delete_passthrough('67', 'model')
    # 3) latent
    P['70']['class_type'] = F['latent']; P['70']['_meta'] = {'title': 'Image size (Empty Latent)'}
    # 4) Z-Image layout ControlNet (1b) is not available for this family
    refs_replace(('74', 0), P['74']['inputs']['model'])
    for nid in G['1b']['nodes']:
        P.pop(nid, None); PASS.pop(nid, None)
    del G['1b']
    # 5) base LoRA: no default one yet for these families
    delete_passthrough('89', 'model')
    # 6) model prefix (Pony score tags etc.) – set by the Studio from the model catalogue
    P['121'] = {'inputs': {'string_a': '', 'string_b': ['81', 0], 'delimiter': ''}, 'class_type': 'StringConcatenate',
                '_meta': {'title': 'Model prompt prefix (set by the Studio)'}}
    P['122'] = {'inputs': {'string_a': '', 'string_b': ['52', 0], 'delimiter': ''}, 'class_type': 'StringConcatenate',
                '_meta': {'title': 'Model negative prefix (set by the Studio)'}}
    P['3']['inputs']['text'] = ['121', 0]
    P['4']['inputs']['text'] = ['122', 0]
    # 7) theme table with steps/cfg + manual overrides
    P['123'] = {'inputs': {'value': 0}, 'class_type': 'PrimitiveInt', '_meta': {'title': 'Manual steps (0 = by theme)'}}
    P['124'] = {'inputs': {'value': 0.0}, 'class_type': 'PrimitiveFloat', '_meta': {'title': 'Manual CFG (0 = by theme)'}}
    pt = P['88']['inputs']
    pt['outputs']['outputs'] = pt['outputs']['outputs'] + ['INT', 'FLOAT']
    pt['j'] = ['123', 0]; pt['k'] = ['124', 0]
    pt['code'] = preset_code(F['presets'], pt['code'])
    P['6']['inputs']['steps'] = ['88', 10]
    for nid in ('6', '17', '25', '30', '62', '33'):
        n = P[nid]['inputs']; n['cfg'] = ['88', 11]; n['sampler_name'] = F['sampler']; n['scheduler'] = F['scheduler']
    P['17']['inputs']['steps'] = F['refine_steps']
    for nid in ('25', '30', '62'):
        P[nid]['inputs']['steps'] = F['det_steps']; P[nid]['inputs']['denoise'] = F['det_denoise'][nid]
    P['33']['inputs']['steps'] = F['up_steps']
    # 8) default negative prompt; the "European look" switch is Z-Image specific
    P['51']['inputs']['value'] = F['neg']
    P['114']['inputs']['value'] = False
    t['ids'] = {'info': t['ids']['info']}
    # bookkeeping
    t['family'] = fam
    t['id'] = f"{fam}-{t['id']}"
    t['source'] = f"derived from {BASE.get('source', 'template.json')}"
    if fam == 'custom':
        # no themes: a single neutral preset; size = aspect ratio scaled to the chosen base size (512 / 768 / 1024 …)
        for k in list(P['86']['inputs']):
            if k.startswith('option'):
                P['86']['inputs'][k] = THEMES[0] if k == 'option1' else ''
        P['86']['inputs']['choice'] = THEMES[0]
        P['127'] = {'inputs': {'value': 1024}, 'class_type': 'PrimitiveInt', '_meta': {'title': 'Base size (512 = SD 1.5, 1024 = SDXL)'}}
        pt['l'] = ['127', 0]
        c = pt['code']
        a = 'wid = size[0]\nhei = size[1]\n'
        assert c.count(a) == 1
        pt['code'] = c.replace(a, 'wid = size[0]\nhei = size[1]\nif l and int(l) > 0 and int(l) != 1024:\n  wid = int(round(wid * int(l) / 1024 / 8)) * 8\n  hei = int(round(hei * int(l) / 1024 / 8)) * 8\n')
        # optional own VAE: Any Switch takes the first connected input, so a bypassed VAE loader falls back to the checkpoint VAE
        P['125'] = {'inputs': {'vae_name': ''}, 'class_type': 'VAELoader', '_meta': {'title': 'Own VAE (optional)'}}
        P['126'] = {'inputs': {'any_01': ['125', 0], 'any_02': ['2', 2]}, 'class_type': 'Any Switch (rgthree)', '_meta': {'title': 'VAE switch: own VAE OR checkpoint VAE'}}
        refs_replace(('2', 2), ['126', 0], skip=('126',))
        G['v'] = {'title': 'Own VAE (optional)', 'nodes': ['125'], 'on': False}
        PASS['125'] = {'0': None}
        P['51']['inputs']['value'] = F['neg']
    # layout for "Open a copy in ComfyUI": same arrangement, family name in the titles, no Z-Image-only parts
    lay = t.get('layout')
    if lay:
        lay['groups'] = [dict(g, title=g['title'].replace('Z-Image Turbo', F['label'])) for g in lay['groups'] if not g['title'].startswith('1b.')]
        ex = []
        for x in lay['extra']:
            if x.get('properties', {}).get('matchTitle', '').startswith('^1b'):
                continue
            if x['type'] == 'MarkdownNote':
                x = dict(x, widgets_values=['# ArtFlawless Studio – ' + F['label'] + ' workflow (copy)\n\nThis is a copy of the node graph that the Studio builds for the ' + F['label'] + ' family. '
                    'You can explore and change it freely here – nothing done here flows back into the Studio.\n\n'
                    'Blocks: **A** image inputs (each group has its own ON/OFF switch above it), **B** theme, size, prompt, LoRA, model → base image, **C** refine, detailers, upscale, save.\n\n'
                    'Groups that are switched off in the Studio are bypassed (purple) here.'])
            ex.append(x)
        lay['extra'] = ex
    # sanity: every link points to an existing node
    for nid, n in P.items():
        for k, v in n['inputs'].items():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[1], int) and isinstance(v[0], str):
                assert v[0] in P, (fam, nid, k, v)
    for g in G.values():
        g['nodes'] = [x for x in g['nodes'] if x in P]
    with open(os.path.join(WEB, f'template-{fam}.json'), 'w', encoding='utf-8') as f:
        json.dump(t, f, ensure_ascii=False, separators=(',', ':'))
    print(fam, len(P), 'nodes')


BASE['family'] = 'zimage'
with open(os.path.join(WEB, 'template.json'), 'w', encoding='utf-8') as f:
    json.dump(BASE, f, ensure_ascii=False, separators=(',', ':'))
for fam in FAMILIES:
    build(fam)

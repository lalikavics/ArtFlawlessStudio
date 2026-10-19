# Copy the current trained translators into a dated archive folder, together with their evaluation, so every version stays selectable.
import os, shutil, json, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); ROOT = os.path.dirname(HERE)
T = os.path.join(ROOT, 'ComfyUI_windows_portable', 'ComfyUI', 'models', 'translate')
A = os.path.join(T, 'archive'); os.makedirs(A, exist_ok=True)
items = [('artflawless-hu-en', 'small-r2-80pct', '07_eval.txt'), ('artflawless-hu-en-big', 'big-r3-84pct', '07_eval_r3.txt')]
for src, name, ev in items:
    s = os.path.join(T, src); d = os.path.join(A, '2026-10-16_' + name)
    if os.path.isdir(s) and not os.path.isdir(d):
        shutil.copytree(s, d)
        e = os.path.join(HERE, 'data', ev)
        if os.path.exists(e): shutil.copy2(e, os.path.join(d, 'eval.txt'))
        print('archived', d)
print(sorted(os.listdir(A)))

# Hungarian → English prompt translator (tools/mt)

How the translator behind the Studio's Hungarian prompting (ArtFlawless HU→EN v1) was made. These scripts are not needed to use the
Studio. They are here so the model can be rebuilt, checked and improved.

The scripts expect to sit in `C:\ArtFlawlessStudio\mt-train\` next to an installed Studio. They use the Studio's own Python and
models are saved under `ComfyUI\models\translate\`. Run them one after another, or put them in `mt-train\jobs\` for `runner.py`.

| Step | Script | What it does |
|---|---|---|
| 1 | `01_prepare.py` | collects clean English image prompts from [DiffusionDB](https://huggingface.co/datasets/poloclub/diffusiondb) (CC0), dropping sexual and unsafe ones |
| 2 | `02_translate_hu.py` | Hungarian candidates with [EuroLLM-1.7B-Instruct](https://huggingface.co/utter-project/EuroLLM-1.7B-Instruct) (Apache-2.0) |
| 3 | `03_opus_en_hu.py` | a second Hungarian candidate with [opus-mt-en-hu](https://huggingface.co/Helsinki-NLP/opus-mt-en-hu) (CC-BY 4.0) |
| 4 | `04_roundtrip_score.py` | translates every candidate back and scores it (chrF); made-up words and loops score low |
| 5 | `05_build_dataset.py` | builds the training set: good synthetic pairs, mixed Hungarian/English pairs and the hand-written pairs |
| 6 | `06_train.py` | fine-tunes [opus-mt-tc-big-hu-en](https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-hu-en) and archives every run |
| 7 | `07_eval.py` | translates the test sets (`eval/`) with the base and the fine-tuned model, next to the reference |
| 11 | `11_package_v1.py` | makes the distributable fp16 model with its model card and times it on CPU and GPU |

Settings used for v1: `MT_BASE=Helsinki-NLP/opus-mt-tc-big-hu-en MT_OUT=artflawless-hu-en-big MT_EPOCHS=4 MT_LR=2e-5 MT_BATCH_TOKENS=2500 MT_AMP=0`
(the big model's loss turns into NaN with bf16 autocast).

- `handmade/`: hand-written Hungarian → English prompt pairs: people, photography terms, Hungarian places and food, mixed-language
  prompts, and the words the image test found wrong.
- `eval/`: held-out test sets. They are never used for training: A and B are full prompts, C has people and tag lists, D has the
  words that failed in the image test, and E has 100 blind sentences on every theme.
- `gen/`: the image test. `build_batches.py` builds the workflows with the Studio page itself. `20_generate.py` translates with the running
  Studio and generates. `sheets.py` makes contact sheets for review. `scores/` holds the review of 60 prompts × 5 models.

The fine-tuned model is under CC-BY 4.0, the same licence as its base model. The scripts are under GPL-3.0-or-later, like the rest of the repository.

# Changelog

All notable changes to ArtFlawless Studio are listed here.
The version number lives in the `VERSION` file and follows [Semantic Versioning](https://semver.org): MAJOR.MINOR.PATCH.

## [1.4.0] - 2026-10-19
### Added
- Hungarian prompting (Hungarian interface): a switch in card 1 and in the Settings menu. The prompt and the negative prompt can be written in Hungarian; a local translator turns them into English before generating. The English text is shown in an editable box under each field ("corrected by hand" stays until you translate again), and the content check looks at both the Hungarian original and the English text.
- The translator (ArtFlawless HU→EN v1, about 470 MB, CC-BY 4.0) is fine-tuned from Helsinki-NLP opus-mt-tc-big-hu-en for image prompts and is downloaded once, from this repository's `translator-v1` release or, if that fails, from Hugging Face. It runs offline: on the graphics card when it has room (well under a second), otherwise on the processor (a few seconds). English words inside a Hungarian prompt, `<lora:...>` tags and `(word:1.2)` weights are kept.
- With Hungarian prompting off, a prompt that looks Hungarian gets a note under the field, and Generate asks whether to switch the translator on, send the text as it is, or cancel (the models do not understand Hungarian).
- `tools/mt/`: the scripts and hand-written data used to make the translator, its test sets and the image test.
- CUSTOM tab for any model: the Studio reads the header of the chosen file (no weights) and recognises SD 1.5, SDXL, Pony, Illustrious, Z-Image and Flux schnell / dev, as a complete checkpoint, a diffusion-only model (also when it sits in `models\checkpoints`) or a GGUF file. It builds the run for that type (text encoder and VAE loaders, sampling shift, Flux guidance, latent type) and shows a detailed settings panel: sampler, scheduler, steps, CFG, base size, CLIP skip, prompt prefixes (Pony score tags), text encoders, VAE, weight precision. The settings are remembered per model file; "Defaults" brings back the values for the type.
- Hardware check on the CUSTOM tab: a note when a model does not fit the graphics card (it runs partly from RAM), and a question before starting when it is far too large or does not fit into the memory.
- Flux text encoders (CLIP-L, T5-XXL fp8) are offered for download when a Flux model without them is chosen.
- GGUF models: the ComfyUI-GGUF node (city96, Apache-2.0) is installed with the other add-ons; GGUF files in `models\unet` appear in the CUSTOM model list.
- LoRA rows on every tab: whether the LoRA fits the loaded model ("Does not work with the loaded checkpoint" switches it off), its trigger words from the training data (click one, or "All into the prompt"), the other frequent training tags, and a separate text-encoder strength for SD 1.5 / SDXL LoRAs. Files in the LoRA folder that are not LoRAs (a checkpoint, an embedding) are named as such.
- Image info: "Use the settings (CUSTOM)" takes the steps, CFG, sampler, scheduler, size, CLIP skip and seed of an A1111 / Civitai image.
- Header: live GPU and CPU load under the connection address (tooltip: VRAM and RAM use).
- Status bar: elapsed time of the run and an estimate from earlier runs with the same model, size and steps.
### Changed
- Safe mode on Z-Image Turbo and Flux.1 schnell: these run at CFG 1 and ignore the negative prompt, so when the prompt is about people (Portrait / People themes or words like woman, man) safe mode adds "clothed" to the prompt itself. Not added for swimwear prompts, with the adult setting, or on SDXL.
- Z-Image: the European look is on by default in the Hungarian interface; switching it off is remembered.
- Pony Diffusion V6 XL is labelled as an anime model; its note says it is for anime, cartoon and illustrated characters, not for photos (in tests it drew most people as young women and dropped objects of the scene).
- About window, setup texts and README credit the translator's base model (OPUS-MT, University of Helsinki, CC-BY 4.0).
### Fixed
- Image info no longer blurs an image you opened yourself; only adult images picked from the history stay blurred.
- CUSTOM tab: a Z-Image or Flux file used to fail with a CLIP error ("-2") whatever the settings were.

## [1.3.2] - 2026-10-14
### Fixed
- The history strip now follows the output folder itself: at start and whenever you come back to the Studio window it shows the newest 40 images that really exist (also those in `output\18+`), newest first. Images deleted in Explorer leave the strip and the viewer, and a thumbnail is checked before it opens.
- "Read embedded prompt from image" (1d): an image without a saved prompt gets a red dashed frame and the label "No embedded prompt", and a short message offers to describe the image instead (1a) or to switch the option off; Generate does not start with such an image.
- Number fields: the arrows (and arrow keys) now move in a typical step for each setting (for example 0.05 for denoise and strengths, 0.25 for upscale amounts) while the sliders and typing still allow 0.01; the up arrow works again. A typed value above the maximum jumps to the maximum at once, a value below the minimum is set to the minimum when you leave the field.
- A run could freeze at "Apply layout ControlNet" (start image and layout reference together) on graphics cards with more than 10 GB: ComfyUI's dynamic VRAM loading hung there. On these cards the launcher now starts ComfyUI with `--disable-dynamic-vram`; 8 GB cards keep dynamic loading, where it works and is faster. `--enable-dynamic-vram` in `launcher\comfy-args.txt` turns it back on. The decision is written to `launcher\launcher.log`.
- Layout reference (1b): the layout image is first resized to about 1 megapixel, so the depth map and the ControlNet do not work on the full size of a large photo.
- Cancel shows "Cancelling…" right away; if ComfyUI is inside a step that cannot be interrupted, a note explains it after 20 seconds.
- Extra ComfyUI start options can be put in `launcher\comfy-args.txt` (one or more per line, `#` for comments), for example `--disable-dynamic-vram`.
- The launcher keeps the ComfyUI log of the previous session (`launcher\comfyui.prev.log`), so a hang can still be looked into after a restart.
- The prompt and text fields no longer show red spell-check underlines (Windows checked the English prompt against the system language).
- The Studio window (ArtFlawlessHost.exe) now shows the program icon in Task Manager too; existing installs rebuild the window once on the next start.
### Added
- Setup: a welcome page that explains what the program is, a Terms of Use page that must be accepted (use at your own risk, acceptable use, no warranty, third-party model licences; your GPL rights are kept), and a details page before installing. The age declaration stays a separate page. All pages are in English and Hungarian.
### Changed
- Credits in the About window and the setup: "Created by Lalikavics. Developed with the help of Claude (Anthropic)."

## [1.3.1] - 2026-10-13
### Changed
- While the content filter is on, a new image stays hidden (the viewer stays dark) until its content check has finished, instead of flashing up blurred; with the filter off, images appear right away.
- The window can now be moved by dragging any empty part of the header, also inside the dashed boxes (for example around the model family tabs); only buttons, fields and menus are excluded.
- Text can only be selected where it makes sense (text fields, the prompt and settings boxes, the Image info and About windows), so a stray mouse drag no longer highlights buttons and labels.
- An adult image shown with the eye button can be hidden again with the "Hide image" button in the bottom right corner; pressing Generate hides every shown adult image again.
- The default European look also works with the theme "None (own prompt only)" when your own prompt describes a person.
- "five fingers on each hand" was removed from the People themes: with short prompts it made people raise both hands.
- Images of a generation whose prompt (or final prompt from an image description) asks for nudity or sexual content are treated as adult content right away, even if the detectors miss it (for example when the image is cropped just above the nudity).
- Switching to another image (thumbnails, step chips) hides an adult image that was shown with the eye button again.
- Credits line in the About window, the README and the release notes.

## [1.3.0] - 2026-10-13
### Added
- Age requirement: the setup asks you to confirm that you are at least 18 years old.
- Content filter: every image is checked locally (NudeNet detector and Falconsai classifier, on the processor). Adult images are blurred with an eye button to show them, and saved into `output\18+`. On by default, can be switched off in Settings after an 18+ confirmation.
- Safe mode: adds "no nudity" words to the negative prompt. On by default, can be switched off.
- One-time 18+ confirmation for prompts that ask for nudity or sexual content.
- Child protection: a prompt that refers to a minor together with nudity or sexual content is always refused (cannot be switched off).
- Machine-readable "AI-generated" mark (IPTC DigitalSourceType in XMP) in generated PNG images.
- Voluntary support: a "Buy me a coffee" button in the About window and a quiet link in the window header. The program stays completely free; supporting it changes nothing.
### Changed
- The setup recognises an existing installation and asks whether to update it (or repair it, or go back to an older version), then installs into the same folder without asking for a folder again. Your images, saved workflows, downloaded models and settings are kept.
- The setup asks you to close the Studio first if it is still running.
### Fixed
- "Read embedded prompt from image" (1d) now reads the original prompt of A1111 / Civitai / Studio images itself; the extractor node took the first text field of the embedded graph (for Studio images the face detailer's prompt).
- The Studio's own minimise / maximise / close buttons no longer appear when the Studio runs in a normal Microsoft Edge window, where they do not work.

## [1.2.0] - 2026-10-12
First public release.

### Installation
- One Windows setup installs ComfyUI (portable), the needed custom nodes and the AI models from their original sources (about 25 GB). It checks the graphics card, free disk space, Microsoft Edge and WebView2, and can be re-run to resume an interrupted download.
- Everything runs locally on your own computer.

### Studio interface
- Three model families with ready-made themes: **Z-Image Turbo**, **SDXL** (Juggernaut XL v9, RealVisXL V5.0, Pony Diffusion V6 XL) and **Flux.1 schnell**, plus a **CUSTOM** tab for your own checkpoint, base size and optional VAE.
- Processing steps: refine (hires fix), face / hand / foot fix and final upscale, each with its own settings; image inputs: start image, style reference, layout reference (ControlNet, Z-Image) and automatic image description.
- Image viewer with mouse-wheel zoom in real-pixel percent (up to 300 %), panning and double-click to fit; "Open folder" shows the saved image in Explorer.
- Save options with Civitai-compatible metadata, file-name tags and a persistent counter; Image info window.
- Saved workflows (new, save, open), notifications, model downloads from the Studio.
- Learning mode with hover hints for beginners; English and Hungarian interface.
- Frameless window with its own minimise / maximise / close buttons and resizable edges; the header folds step by step on narrow windows.
- "Open a copy in ComfyUI" shows the full node graph with groups, switches and all connections, for those who want to look under the hood.
- Licence button with link and notes for every model, general licence information and a disclaimer for your own models; system requirements in the setup and in the About window.

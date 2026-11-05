# Changelog

All notable changes to ArtFlawless Studio are listed here.
The version number lives in the `VERSION` file and follows [Semantic Versioning](https://semver.org): MAJOR.MINOR.PATCH.

## [1.5.0] - 2026-11-05
### Added
- New look, "frosted aluminium": the panels, the header, the buttons and the pop-ups are fine-grained matt metal with rounded corners (the inner panels are sunk into the surface), the yellow buttons are sandblasted glass with a thin light edge, switches and sliders are pressed into the surface, dividers are soft shadows that fade out at both ends, and the viewer has a glass rim with a light edge at the bottom. The bluish greys of the interface are neutral greys now.
- New program icon (yellow logo on a dark rounded panel) for the desktop shortcut, the taskbar, the window and the header.
- Start window: a rounded panel without a Windows frame (smooth corners, soft shadow) with the logo, a turning ring and a list of what is happening - starting the engine, the graphics card found (name and memory), the components loading (with a counter), the server, opening the workspace and restoring the last session. Finished steps slide up with a tick. It speaks the Studio's language (English on the first start), stays until the Studio page has loaded, and shows an error with the log's location when the start fails.
- The Studio starts in the language chosen in the setup (until a language is picked in the Studio itself).
- Open and closed cards (and the "Applied settings and final prompt" panel) are remembered. On the very first start only card 1 (the prompt) and card 6 (generate) are open, the others, the "Applied settings and final prompt" panel and the history strip are folded; Hungarian prompting is off until it is switched on.
- Setup: the component download runs without a console window; the same window shows each step, and for every download the size done, the total, the percentage and the speed (for example "Z-Image Turbo: 3.2 / 12.3 GB (26%) · 18 MB/s"). The Civitai LoRA step and the summary are message boxes. The language of the setup is the start window's first language.
- History strip under the viewer as its own panel: open it into a larger area that shows the whole output folder (continuous scrolling) and resize it by dragging its upper edge; closed, it shows one row of whole thumbnails. The thumbnail size is set with a slider (thumbnails icon), the image count is on the right, a refresh button reloads the folder.
- An eye button in the strip's header hides or shows the 18+ images of the folder (grey when there are none).
- An eye button at the bottom right of the viewer marks any image as adult content: it goes into `output\18+` and is blurred from now on - also an image marked "not adult" earlier.
- The step chips under the viewer (Base image, Refined, ...) are there from the start (inactive until there is an image), with small triangles between them showing the order of the steps.
- Long explanations fold away behind a small triangle (one-line summary shown); the LoRA details and its trigger words fold away the same way.
- "output folder" in the texts of the cards opens the output folder.
### Changed
- Header subtitle: "Local AI image studio, built on ComfyUI".
- The output folder opens on the first click and comes in front of the Studio (Explorer is given up to 8 s on its first start, and is asked once more if no window appeared).
- Thin, frameless scrollbars with a dark handle that lightens under the pointer.
- Window frame line in the colour of the background.
### Fixed
- A model file that is missing under its saved name is found under another version number ("... v1" -> "... v1.1", the newest is taken); the base LoRA is found under any name with "Hands" and "Feet" in it.
- When the base LoRA is not there, card 2 says so and offers its download page, the LoRA folder and a new check.
- "Check again" (missing components, notifications) now says what it found; before it seemed to do nothing.
- The 18+ confirmation (switching the content filter off) showed "null" under its text, and its accept button was not yellow like the other active buttons.
- Image info shows the LoRAs and their strengths: the image saver removed the `<lora:...>` tags from the saved text, so they are written into the image's parameters separately now; for earlier images they are read from the embedded ComfyUI run.
- SDXL images were marked adult because the check also read the Hungarian source of the negative prompt.
- The settings drawer's close button could not be clicked in a maximised window.
- An image removed from the `18+` folder by hand no longer stays blurred in the viewer and the step chips.

## [1.4.1] - 2026-11-04
### Fixed
- The Studio used processor and graphics card time even when idle, and moving the window stuttered: the GPU/CPU load meters in the header animated their width, which made the whole page lay itself out on every screen frame (about 70 times a second, more on high refresh rate monitors). The bars now move on the graphics card and change only when the value changes; idle work of the page dropped from 0.56 s to 0.04 s per 10 s, the window's own processor use from about 26 % to 0.5 % of a core.
- Resizing the window: the header no longer measures itself several times on every step to decide what to fold away; the widths are measured once when the header content changes, and resizing only compares the window width with them.
- No grey frame line around the window after switching to another program and back.
### Changed
- The Studio window shows the page through visual hosting (DirectComposition): during a resize drag the window and the page change together, one step per screen refresh, so the content no longer trembles or jumps. Mouse input, the cursor and drag & drop are passed to the page by the window. If visual hosting cannot start, the window uses the previous way (the page in its own child window), now passing the new size on at most once per screen refresh. `studio-window\window-mode.txt` with the word `window` selects that way by hand.
- Right-click menu: in text fields only Cut, Copy, Paste and Select all, on selected text only Copy, elsewhere none (no Inspect, Save, Print and the like); F12 no longer opens the developer tools.

## [1.4.0] - 2026-10-19
### Added
- Hungarian prompting (Hungarian interface): a switch in card 1 and in the Settings menu. The prompt and the negative prompt can be written in Hungarian; a local translator turns them into English before generating. The English text is shown in an editable box under each field ("corrected by hand" stays until you translate again), and the content check looks at both the Hungarian original and the English text.
- The translator (ArtFlawless HU→EN v1, about 470 MB, CC-BY 4.0) is fine-tuned from Helsinki-NLP opus-mt-tc-big-hu-en for image prompts and is downloaded once, as one zip (`artflawless-hu-en-v1.zip`) from this repository's `translator-v1` release or, if that fails, from Hugging Face. It runs offline: on the graphics card when it has room (well under a second), otherwise on the processor (a few seconds). English words inside a Hungarian prompt, `<lora:...>` tags and `(word:1.2)` weights are kept.
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

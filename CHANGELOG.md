# Changelog

All notable changes to ArtFlawless Studio are listed here.
The version number lives in the `VERSION` file and follows [Semantic Versioning](https://semver.org): MAJOR.MINOR.PATCH.

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

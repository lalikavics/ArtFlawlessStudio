# ArtFlawless Studio

**Local AI image generation, made simple.** ArtFlawless Studio is a free Windows setup and a simple interface on top of
[ComfyUI](https://github.com/comfyanonymous/ComfyUI). Everything runs on your own computer: nothing is generated or sent anywhere else.

*Magyarul: lásd [OLVASSEL.md](OLVASSEL.md).*

## Features

- One setup installs ComfyUI, the needed add-ons and the AI models from their original sources.
- Three model families with ready-made themes: **Z-Image Turbo**, **SDXL** (Juggernaut XL, RealVisXL, Pony) and **Flux.1 schnell**, plus a **CUSTOM** tab for your own checkpoint.
- Refine, face / hand / foot fix and final upscale steps, image inputs (start image, style reference, image description).
- Civitai-compatible metadata, Image info window, saved workflows, learning mode with hints (English and Hungarian).
- "Open a copy in ComfyUI" shows the full node graph, for those who want to look under the hood.

## System requirements

| | Minimum | Recommended |
|---|---|---|
| Windows | 10 64-bit (1803 or newer) or 11 | 11, or 10 22H2 |
| Graphics card | NVIDIA GeForce RTX with 8 GB video memory, up-to-date driver | NVIDIA RTX with 12 GB or more |
| Memory | 32 GB RAM | 64 GB RAM |
| Processor | 4 cores, 64-bit | 6 or more cores |
| Disk | 50 GB free (SSD) | 100 GB free on an NVMe SSD |
| Other | Microsoft Edge (part of Windows), internet connection for the setup | |

Tested on an RTX 3060 Ti 8 GB with 64 GB RAM under Windows 10 22H2. AMD and Intel graphics cards are not supported.

## Download and install

1. Download `ArtFlawlessStudio-Setup-X.Y.Z.exe` from the [Releases](../../releases) page.
2. Run it. The setup downloads about 25 GB, so this takes a while; it can be re-run to resume.
3. Start **ArtFlawless Studio** from the desktop shortcut.

## Build from source

You need [Python 3](https://www.python.org/downloads/) and [Inno Setup 6.3+](https://jrsoftware.org/isdl.php). Then run:

```
build.bat
```

The setup appears in the `Output` folder. `build.bat` runs `make_studio_files.py` and `make_families.py` (they generate
`studio_out/`) and then compiles `ArtFlawlessStudio.iss`.

GitHub also builds the setup automatically for every change (Actions tab → latest run → *Artifacts*).

## Releasing a new version

1. Change the number in the `VERSION` file (for example `1.2.0` → `1.3.0`). This is the only place where the version is set;
   the setup, the Studio and the About window all read it from there.
2. Add a section for the new version at the top of `CHANGELOG.md`.
3. Commit and push.
4. On GitHub: **Releases → Draft a new release**, tag `v1.3.0` (the same number with a `v`), title `ArtFlawless Studio 1.3.0`, **Publish**.
   The workflow builds the setup and attaches it to the release, with the notes from `CHANGELOG.md`.

Version numbers follow [Semantic Versioning](https://semver.org): fixes raise the last number (1.2.**1**), new features the middle one
(1.**3**.0), changes that break saved workflows or settings the first one (**2**.0.0).

## Project layout

| Path | What it is |
|---|---|
| `VERSION` | the version number (single source) |
| `ArtFlawlessStudio.iss` | Inno Setup script of the Windows setup |
| `build.bat` | builds the setup locally |
| `launcher/` | PowerShell installer and launcher, the frameless window (`ArtFlawlessHost.cs`, compiled on the user's computer) |
| `studio/` | the original Z-Image workflow and the Studio page |
| `make_studio_files.py`, `make_families.py`, `help_texts.py` | generate the Studio page and the SDXL / Flux / Custom templates into `studio_out/` |
| `assets/` | ComfyUI add-on of the Studio (`studio_init.py`), model catalogue, setup texts, icon and logo |
| `tools/` | helper scripts for the release workflow |

## Licence

ArtFlawless Studio is free software: you can redistribute it and/or modify it under the terms of the
**GNU General Public License version 3 or (at your option) any later version**. See [LICENSE](LICENSE).

Copyright (C) 2026 Lalikavics.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

### Third-party components

This repository contains only the ArtFlawless Studio code. ComfyUI, the custom nodes and the AI models are **not** included: the setup
downloads them from their original sources, and each of them stays under its own licence:

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) (GPL-3.0), installed unmodified.
- Custom nodes: rgthree-comfy, ComfyUI Impact Pack and Subpack, Ultimate SD Upscale, ComfyUI-Florence2, ComfyUI-Custom-Scripts,
  ControlNet Auxiliary Preprocessors, ComfyUI Image Saver, ComfyUI-Prompt-Manager.
- Models: Z-Image Turbo and Flux.1 schnell (Apache-2.0), Juggernaut XL v9 (CreativeML Open RAIL-M), RealVisXL V5.0 (OpenRAIL++),
  Pony Diffusion V6 XL (Fair AI Public License 1.0-SD), and the LoRAs, detectors and upscalers listed in the setup.

What you may do with the generated images is set by the licence of each model and LoRA you used. Please read them, especially before
commercial use. The Studio shows a **Licence** button with a link next to every model.

ArtFlawless Studio is an independent project. It is not affiliated with, endorsed by or connected to Comfy Org or the ComfyUI developers.

## Disclaimer

The software is provided "as is", without warranty of any kind. You alone are responsible for what you create with it and how you use
it, including the licences of the models and the laws that apply to you. Do not use it to depict real people without their consent or
to create unlawful or harmful content.

## Contact

Questions, ideas and bug reports: please use [Issues](../../issues) on this page.
If you are the author of a model, LoRA or node used by the setup and want it removed or credited differently, open an issue too.

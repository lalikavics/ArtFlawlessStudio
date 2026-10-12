# Changelog

All notable changes to ArtFlawless Studio are listed here.
The version number lives in the `VERSION` file and follows [Semantic Versioning](https://semver.org): MAJOR.MINOR.PATCH.

## [1.2.0] - 2026-10-12
### Added
- New name: **ArtFlawless Studio**. The setup renames an earlier `C:\ArtFlowStudio` folder to `C:\ArtFlawlessStudio` (models and images are kept) and replaces the old desktop shortcut.
- Frameless Studio window (WebView2) with its own minimise / maximise / close buttons, resizable edges and a thin footer; falls back to a Microsoft Edge window when WebView2 is not available.
- Header that folds step by step on narrow windows (icon buttons into a "more" menu, model families into a dropdown).
- CUSTOM tab: your own checkpoint, base size and optional VAE, without themes or automatic LoRAs.
- Image viewer with mouse-wheel zoom in real-pixel percent (up to 300 %), panning and double-click to fit.
- Learning mode: hover hints for beginners in English and Hungarian (asked on first start).
- Separate Save card: metadata switch and file-name tags.
- Licence button for every model (link and notes), general licence information and disclaimer for your own models.
- System requirements in the setup and in the About window; the setup checks for Microsoft Edge and WebView2.
- "Open a copy in ComfyUI" opens the original layout with groups, switches, guide and all connections; switched-off groups are bypassed.
- "Open folder" brings Explorer to the front at the saved image; the image picker starts in the input folder.
### Changed
- Header redesign: brand block with version, dashed boxes, monochrome icons, connection indicator with IP address, gear menu (language, learning mode, advanced settings).
- Themed scrollbars; the first-start hint disappears when you press Generate.

## [1.1.0] - 2026-10-11
### Added
- Three model families with their own workflow and themes: Z-Image Turbo, SDXL (Juggernaut XL v9, RealVisXL V5, Pony V6) and Flux.1 schnell.
- Model downloads from the Studio, workflows (new, save, open), notifications.
- Civitai-compatible metadata with Image Saver and a persistent file-name counter; Image info window.

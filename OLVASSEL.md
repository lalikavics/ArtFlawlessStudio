# ArtFlawless Studio 1.2.0 – telepítő és Studio

Fordítás: `build.bat` (Python 3 és Inno Setup 6.3+ kell) → `Output\ArtFlawlessStudio-Setup-<verzió>.exe`. A verziószám egyetlen helyen van: a `VERSION` fájlban.
A Studio fájljait a `make_studio_files.py` és a `make_families.py` állítja elő (`studio_out\`), ezek kerülnek a telepítőbe.

ArtFlawless Studio független projekt, a ComfyUI-ra épül (GPL-3.0); nem áll kapcsolatban a Comfy Org-gal.

## Újdonságok az 1.2.0-ban
- Új név: **ArtFlawless Studio**. A telepítő a régi `C:\ArtFlowStudio` mappát átnevezi `C:\ArtFlawlessStudio`-ra (a modellek és képek megmaradnak), a régi asztali ikont lecseréli. Telepítés előtt zárd be a Studiót.
- Új fejléc: márkablokk sárga verziószámmal, szaggatott keretes csoportok, egyszínű ikonok, kapcsolat-jelző IP-címmel, fogaskerék menü (nyelv, tanuló mód, haladó beállítások).
- **CUSTOM** fül: saját checkpoint, alapméret, opcionális VAE – témák és automatikus LoRA-k nélkül.
- Képnéző: görgős nagyítás valódi pixelhez mért %-kal (max. 300%), húzással mozgatás, dupla katt = illesztés.
- Tanuló mód: rámutatásos magyarázatok kezdőknek (első indításkor rákérdez).
- Külön Mentés kártya: metaadat-kapcsoló, fájlnév-címkék.
- Generálás közben forgó jelző a gombon és a képen.
- "Mappa megnyitása" az Intézőt a kép helyén nyitja meg, előtérben.
- A képbetöltő tallózás a Windows saját ablakával az input mappában indul.
- "Másolat megnyitása a ComfyUI-ban": az eredeti elrendezéssel, csoportokkal, kapcsolókkal és útmutatóval; a Studióban kikapcsolt csoportok kikerülve (bypass) jelennek meg.
- Keret nélküli Studio-ablak (WebView2) saját ─ □ ✕ gombokkal, széleknél átméretezhető, vékony lábléccel; ha a WebView2 nem érhető el, Edge-ablakban nyílik meg. Témához illő görgetősáv.
- Keskeny ablaknál a fejléc fokozatosan összecsukódik (ikonok a ⋯ menübe, modellcsalád legördülő listába).
- Licenc gomb modellenként (link + tudnivalók), általános licencinfó és felelősségkizárás a saját modellekhez.
- Rendszerkövetelmények a telepítőben és a névjegyben; a telepítő ellenőrzi az Edge és a WebView2 meglétét.

## Rendszerkövetelmények
- Minimum: Windows 10 64 bit (1803+) / 11, NVIDIA RTX 8 GB VRAM, 32 GB RAM, 4 mag, 50 GB SSD, Microsoft Edge, internet.
- Ajánlott: Windows 11 / 10 22H2, NVIDIA RTX 12 GB+ VRAM, 64 GB RAM, 6+ mag, 100 GB NVMe SSD.

## A te gépeden tesztelve (RTX 3060 Ti 8 GB, 64 GB RAM)
- Mind a 8 téma × 3 család lefutott; RealVis és Pony külön tesztelve.
- Tipikus idők: alapkép 20–40 mp, finomítás + arcjavítás 1–3 perc, végső nagyítás 4–6 perc (Flux a leglassabb).

## Ismert korlátok
- Az elrendezés-referencia (ControlNet) csak Z-Image-nél van.
- SDXL-hez és Fluxhoz nincs automatikus bőr/kéz LoRA; az arc/kéz/láb javító lépések mindegyiknél működnek.
- A Flux schnell bőre kissé "műanyag" – emberekhez a Z-Image vagy a RealVis ajánlott.
- Az exe nincs digitálisan aláírva (SmartScreen figyelmeztet).

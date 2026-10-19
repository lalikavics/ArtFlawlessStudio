# ArtFlawless Studio

**Helyi AI-képgenerálás, egyszerűen.**

![Az ArtFlawless Studio főablaka: modellcsalád-fülek, bal oldalt a prompt és a beállítások, középen az elkészült kép, jobb oldalt a képbemenetek és a mentés](docs/screenshot.png)

Az ArtFlawless Studio ingyenes, nyílt forráskódú Windows-alkalmazás, amellyel mesterséges intelligenciával készíthetsz képeket a saját
gépeden. Két részből áll: egy telepítőből, amely mindent feltesz, ami kell, és egy egyszerű, barátságos kezelőfelületből (a *Studióból*),
amely a népszerű, node-alapú képgeneráló motorra, a [ComfyUI](https://github.com/comfyanonymous/ComfyUI)-ra épül.

A ComfyUI nagyon sokoldalú, de a node-gráfjai kezdőként ijesztőek lehetnek. A Studio elrejti ezt a bonyolultságot: kiválasztod a
modellcsaládot és egy témát, leírod, mit szeretnél látni, és megnyomod a **Generate** gombot. A háttérben egy gondosan összekötött
ComfyUI-munkafolyamat elkészíti a képet, finomítja, kijavítja az arcot, a kezet és a lábat, majd felnagyítja az eredményt. A teljes
node-gráfot bármikor megnyithatod a ComfyUI-ban, ha szeretnéd megérteni, hogyan működik, vagy magad alakítanád tovább.

Minden a saját gépeden fut: nincs fiók, nincs előfizetés, nincs felhőszolgáltatás. A leírásaid és a képeid nem hagyják el a
számítógépedet, a modellek pedig egyszer töltődnek le az eredeti forrásukból.

*English: see [README.md](README.md).*

## Funkciók

- Egyetlen telepítő felteszi a ComfyUI-t, a szükséges kiegészítőket és az AI-modelleket az eredeti forrásukból.
- Három modellcsalád kész témákkal: **Z-Image Turbo**, **SDXL** (Juggernaut XL, RealVisXL, Pony) és **Flux.1 schnell**, valamint egy **CUSTOM** fül a saját modelljeidhez.
- **CUSTOM fül**: felismeri a kiválasztott fájl típusát (SD 1.5, SDXL, Pony, Illustrious, Z-Image, Flux schnell / dev; teljes checkpoint,
  csak képalkotó modell és GGUF fájl), betölti a hozzá való szövegkódolót és VAE-t, és a típusnak megfelelő részletes beállításokat mutat,
  modellenként megjegyezve. Figyelmeztet, ha a modell túl nagy a videókártyához vagy a memóriához. A LoRA-soroknál látszik, illik-e a
  LoRA a betöltött modellhez, a trigger szavai (egy kattintással a promptba kerülnek), és külön állítható a szövegkódoló erőssége.
- A fejlécben élő GPU- és CPU-terhelés, futás közben pedig a korábbiak alapján becsült idő.
- Finomítás, arc-, kéz- és lábjavítás, végső nagyítás; képbemenetek (kezdőkép, stílusreferencia, elrendezés-referencia, automatikus képleírás).
- Civitai-kompatibilis metaadatok, képinfó ablak, mentett munkafolyamatok, tanuló mód rámutatásos magyarázatokkal (magyarul és angolul).
- **Magyar promptolás** (magyar felületen): a promptot és a negatív promptot magyarul írhatod; egy helyi fordító (egyszer
  kell letölteni, kb. 470 MB, internet nélkül fut) angolra fordítja, az angol szöveget generálás előtt kézzel is javíthatod.
- „Másolat megnyitása a ComfyUI-ban”: a teljes node-gráf, ha kíváncsi vagy, mi van a motorháztető alatt.

## Rendszerkövetelmények

| | Minimum | Ajánlott |
|---|---|---|
| Windows | 10 64 bites (1803 vagy újabb) vagy 11 | 11, vagy 10 22H2 |
| Videokártya | NVIDIA GeForce RTX 8 GB videomemóriával, friss illesztőprogrammal | NVIDIA RTX 12 GB vagy több |
| Memória | 32 GB RAM | 64 GB RAM |
| Processzor | 4 mag, 64 bites | 6 vagy több mag |
| Lemez | 50 GB szabad hely (SSD) | 100 GB szabad hely NVMe SSD-n |
| Egyéb | Microsoft Edge (a Windows része), internetkapcsolat a telepítéshez | |

RTX 3060 Ti 8 GB kártyával és 64 GB RAM-mal, Windows 10 22H2 alatt tesztelve. AMD és Intel videokártyákat nem támogat.

## Letöltés és telepítés

1. Töltsd le az `ArtFlawlessStudio-Setup-X.Y.Z.exe` fájlt a [Releases](../../releases) oldalról.
2. Futtasd. A telepítő kb. 25 GB-ot tölt le, ez eltart egy ideig; ha megszakad, újraindítva onnan folytatja.
3. Indítsd az **ArtFlawless Studiót** az asztali ikonról.

## Frissítés

Töltsd le az új telepítőt a [Releases](../../releases) oldalról, és futtasd. Felismeri a meglévő telepítést, rákérdez a frissítésre, és
ugyanabba a mappába telepít. A képeid (`input` és `output` mappa), a mentett munkafolyamatok, a letöltött modellek és a beállítások
megmaradnak. Frissítés előtt zárd be a Studiót.

## Ismert korlátok

- Az elrendezés-referencia (ControlNet) csak a Z-Image Turbónál érhető el.
- Az SDXL-hez és a Fluxhoz nincs automatikus bőr- és kéz-LoRA; az arc-, kéz- és lábjavító lépések minden családnál működnek.
- A Flux.1 schnell bőre kissé „műanyag” hatású; emberekhez a Z-Image Turbo vagy a RealVisXL jobb.
- A telepítő még nincs digitálisan aláírva, ezért a Windows SmartScreen figyelmeztethet („További információ” → „Futtatás mindenképp”).

## Fordítás forrásból

Kell hozzá [Python 3](https://www.python.org/downloads/) és [Inno Setup 6.3+](https://jrsoftware.org/isdl.php). Utána futtasd:

```
build.bat
```

A telepítő az `Output` mappában jelenik meg. A `build.bat` lefuttatja a `make_studio_files.py` és a `make_families.py` szkriptet
(ezek állítják elő a `studio_out/` mappát), majd lefordítja az `ArtFlawlessStudio.iss` fájlt.

A GitHub minden változtatás után automatikusan is elkészíti a telepítőt (Actions fül → legutóbbi futás → *Artifacts*).

## Új verzió kiadása

1. Írd át a számot a `VERSION` fájlban (például `1.3.0` → `1.3.1`). A verziószám csak itt van megadva; a telepítő, a Studio és a
   névjegy is innen olvassa.
2. Írj egy szakaszt az új verzióról a `CHANGELOG.md` elejére.
3. Commit és push.
4. A GitHubon: **Releases → Draft a new release**, tag: `v1.3.1` (ugyanaz a szám `v` betűvel), cím: `ArtFlawless Studio 1.3.1`, **Publish**.
   A workflow elkészíti a telepítőt, és a `CHANGELOG.md` szövegével együtt csatolja a kiadáshoz.

A verziószámok a [szemantikus verziózást](https://semver.org/lang/hu/) követik: a javítások az utolsó számot emelik (1.2.**1**), az új
funkciók a középsőt (1.**3**.0), a mentett munkafolyamatokat vagy beállításokat érintő, nem visszafelé kompatibilis változások az elsőt (**2**.0.0).

## Korhatár és tartalomvédelem

Az ArtFlawless Studiót csak **felnőtt (18. életévét betöltött) személy** használhatja. A telepítő ezt megerősítteti veled.

- **Tartalomszűrő**: minden kép a saját gépeden ellenőrződik (NudeNet felismerő és Falconsai osztályozó, a processzoron). A felnőtt
  tartalmúnak (meztelenség, szexuális tartalom) felismert képek homályosítva jelennek meg, szem gombbal megjeleníthetők, és az
  `output\18+` mappába kerülnek. Alapból be van kapcsolva; a beállításokban kikapcsolható, miután megerősítetted, hogy elmúltál 18 éves.
- **Biztonságos mód**: „meztelenség nélkül” jellegű szavakat tesz a negatív promptba, hogy véletlenül se jelenjen meg meztelenség.
  A Z-Image Turbo és a Flux.1 schnell negatív prompt nélkül fut (CFG 1), ezért ezeknél, ha a prompt emberekről szól, a biztonságos
  mód magába a promptba teszi a „clothed” (felöltözött) szót. Alapból be van kapcsolva, kikapcsolható.
- **18+ megerősítés**: ha a prompt meztelenséget vagy szexuális tartalmat kér, egyszer meg kell erősítened, hogy felnőtt vagy.
- **Gyermekvédelem**: ha a prompt kiskorúra utal meztelenséggel vagy szexuális tartalommal együtt, a program mindig megtagadja a
  generálást, és ez nem kapcsolható ki. Kiskorúak szexuális ábrázolása tilos, a mesterséges és MI-vel készített is
  ([2011/93/EU irányelv](https://eur-lex.europa.eu/eli/dir/2011/93/oj)).
- **MI-jelölés**: a generált PNG-képek géppel olvasható „MI által készített” jelölést kapnak (IPTC DigitalSourceType, XMP), az
  [EU MI-rendelet, (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) 50. cikkének szellemében.

A felismerés automatikus, és nem tökéletes: tévedhet mindkét irányba. Az AI-modelleket nem az ArtFlawless Studio szerzője készítette,
és nem ő terjeszti: a telepítő az eredeti forrásukból tölti le őket, és mindegyikre a saját licence vonatkozik. Az ArtFlawless Studio
igyekszik csökkenteni a visszaélés kockázatát, de nyílt forráskódú szoftverként ezt teljesen kizárni nem tudja. Aki ezeket a védelmeket
megkerüli, vagy a programot ennek érdekében átírja, a saját felelősségére teszi; ehhez a szerző nem járul hozzá, és ezért nem vállal
felelősséget.

## Támogatás

Az ArtFlawless Studio ingyenes, és az is marad: nincs fizetős változat, nincsenek zárolt funkciók, a támogatók sem kapnak elsőbbséget.
Ha tetszik, [meghívhatsz egy kávéra](https://buymeacoffee.com/lalikavics) önkéntes köszönetként. Ez semmin nem változtat a programban.

## Licenc

Az ArtFlawless Studio szabad szoftver: a **GNU General Public License 3-as vagy (választásod szerint) bármely későbbi változata**
szerint terjesztheted és módosíthatod. Lásd: [LICENSE](LICENSE).

Copyright (C) 2026 Lalikavics.

A programot abban a reményben terjesztjük, hogy hasznos lesz, de MINDENFÉLE GARANCIA NÉLKÜL, beleértve az eladhatóságra vagy egy adott
célra való alkalmasságra vonatkozó hallgatólagos garanciát is. A részletekért lásd a GNU General Public License-t.

### Külső összetevők

Ez a tároló csak az ArtFlawless Studio kódját tartalmazza. A ComfyUI, a kiegészítő node-ok és az AI-modellek **nincsenek** benne: a
telepítő az eredeti forrásukból tölti le őket, és mindegyikre a saját licence vonatkozik:

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) (GPL-3.0), módosítás nélkül telepítve.
- Kiegészítő node-ok: rgthree-comfy, ComfyUI Impact Pack és Subpack, Ultimate SD Upscale, ComfyUI-Florence2, ComfyUI-Custom-Scripts,
  ControlNet Auxiliary Preprocessors, ComfyUI Image Saver, ComfyUI-Prompt-Manager, [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) (Apache-2.0).
- Flux szövegkódolók a CUSTOM fülhöz, csak ha kellenek (előtte rákérdez): CLIP-L (MIT) és T5-XXL fp8 (Apache-2.0),
  forrás: [comfyanonymous/flux_text_encoders](https://huggingface.co/comfyanonymous/flux_text_encoders).
- Tartalomellenőrzés: [NudeNet](https://github.com/notAI-tech/NudeNet) (a csomag AGPL-3.0 és MIT licencet is feltüntet) és
  [Falconsai/nsfw_image_detection](https://huggingface.co/Falconsai/nsfw_image_detection) (Apache-2.0).
- Promptfordító: ArtFlawless HU→EN v1, a [Helsinki-NLP/opus-mt-tc-big-hu-en](https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-hu-en)
  (CC-BY 4.0, OPUS-MT, Helsinki Egyetem) továbbtanított változata; ez is CC-BY 4.0, és e tároló `translator-v1` kiadásából vagy a
  [Hugging Face-ről](https://huggingface.co/Lalikavics/artflawless-hu-en-v1) töltődik le.
- Modellek: Z-Image Turbo és Flux.1 schnell (Apache-2.0), Juggernaut XL v9 (CreativeML Open RAIL-M), RealVisXL V5.0 (OpenRAIL++),
  Pony Diffusion V6 XL (Fair AI Public License 1.0-SD), valamint a telepítőben felsorolt LoRA-k, detektorok és nagyítók.

Hogy mit tehetsz a generált képekkel, azt az általad használt modellek és LoRA-k licence határozza meg. Kérlek, olvasd el őket, főleg
kereskedelmi felhasználás előtt. A Studio minden modell mellett mutat egy **Licenc** gombot a linkkel.

Az ArtFlawless Studio független projekt. Nem áll kapcsolatban a Comfy Org-gal vagy a ComfyUI fejlesztőivel, és ők nem támogatják hivatalosan.

## Felelősségkizárás

A szoftvert „ahogy van” alapon, mindenféle garancia nélkül adjuk közre. Kizárólag te felelsz azért, amit vele létrehozol, és azért,
ahogyan felhasználod, beleértve a modellek licencét és a rád vonatkozó jogszabályokat is. Ne használd valós személyek ábrázolására a
beleegyezésük nélkül, sem jogellenes vagy ártalmas tartalom készítésére.

## Kapcsolat

Kérdések, ötletek és hibajelzések: kérlek, az oldal [Issues](../../issues) részét használd.
Ha egy, a telepítő által használt modell, LoRA vagy node szerzője vagy, és szeretnéd, hogy a munkád kikerüljön vagy másképp legyen
feltüntetve, szintén nyiss egy issue-t.

---

*A Claude (Anthropic) segítségével fejlesztve.*

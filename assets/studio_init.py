# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# ArtFlawless Studio – ComfyUI add-on: serves the Studio page at /artflow, the family templates,
# a small model downloader (catalog.json lists what can be downloaded and where it goes)
# the local content check of generated images (adult content, AI-generated mark)
# and the local Hungarian -> English prompt translator.
import asyncio
import json
import os
import re
import shutil
import subprocess
import threading
import time

import aiohttp
from aiohttp import web
from server import PromptServer
import folder_paths

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
CATALOG = os.path.join(HERE, "catalog.json")
NO_CACHE = {"Cache-Control": "no-store"}
CHUNK = 4 * 1024 * 1024

routes = PromptServer.instance.routes
DL = {}        # model id -> {"state", "done", "total", "error", "speed"}
TASKS = {}     # model id -> asyncio.Task


def _catalog():
    with open(CATALOG, encoding="utf-8") as f:
        return json.load(f)


def _dest(m):
    folder = m["folder"]
    paths = folder_paths.get_folder_paths(folder)
    if not paths:
        raise RuntimeError("unknown model folder: " + folder)
    rel = os.path.join(*m["file"].split("/"))
    for p in paths:                      # already there (e.g. diffusion_models also lists models/unet)
        if os.path.isfile(os.path.join(p, rel)):
            return os.path.join(p, rel)
    named = [p for p in paths if os.path.basename(os.path.normpath(p)).lower() == folder.lower()]
    return os.path.join((named or paths)[0], rel)


def _installed(m):
    try:
        p = _dest(m)
        return os.path.isfile(p) and os.path.getsize(p) >= int(m.get("size", 1) * 0.98)
    except Exception:
        return False


def _forget_cache(folder):
    cache = getattr(folder_paths, "filename_list_cache", None)
    if isinstance(cache, dict):
        cache.pop(folder, None)


async def _download(m):
    mid = m["id"]
    st = DL[mid] = {"state": "running", "done": 0, "total": int(m.get("size") or 0), "error": "", "speed": 0}
    dest = _dest(m)
    part = dest + ".part"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    headers = {"User-Agent": "ArtFlawlessStudio/1.3"}
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token and "huggingface.co" in m["url"]:
        headers["Authorization"] = "Bearer " + token
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=120)
    try:
        for attempt in range(1, 6):
            have = os.path.getsize(part) if os.path.exists(part) else 0
            h = dict(headers)
            if have:
                h["Range"] = "bytes=%d-" % have
            try:
                async with aiohttp.ClientSession(timeout=timeout) as s:
                    async with s.get(m["url"], headers=h, allow_redirects=True) as r:
                        if r.status == 416:          # already complete
                            break
                        if r.status not in (200, 206):
                            raise RuntimeError("HTTP %d" % r.status)
                        if r.status == 200:
                            have = 0
                        length = r.headers.get("Content-Length")
                        if length:
                            st["total"] = have + int(length)
                        st["done"] = have
                        t0, d0 = time.time(), have
                        with open(part, "ab" if have else "wb") as f:
                            async for chunk in r.content.iter_chunked(CHUNK):
                                f.write(chunk)
                                st["done"] += len(chunk)
                                dt = time.time() - t0
                                if dt > 1:
                                    st["speed"] = int((st["done"] - d0) / dt)
                                    t0, d0 = time.time(), st["done"]
                break
            except asyncio.CancelledError:
                raise
            except Exception as e:  # network hiccup: retry, resuming from the .part file
                st["error"] = str(e)
                if attempt == 5:
                    raise
                await asyncio.sleep(3 * attempt)
        size = os.path.getsize(part)
        if m.get("size") and size < int(m["size"] * 0.98):
            raise RuntimeError("incomplete download (%d of %d bytes)" % (size, m["size"]))
        os.replace(part, dest)
        _forget_cache(m["folder"])
        st.update(state="done", done=size, total=size, error="")
    except asyncio.CancelledError:
        st.update(state="cancelled")
        raise
    except Exception as e:
        st.update(state="error", error=str(e))
    finally:
        TASKS.pop(mid, None)


@routes.get("/artflow")
async def artflow_index(request):
    return web.FileResponse(os.path.join(WEB, "index.html"), headers=NO_CACHE)


@routes.get("/artflow/")
async def artflow_index_slash(request):
    raise web.HTTPFound("/artflow")


@routes.get("/artflow/template.json")
async def artflow_template(request):
    path = os.path.join(WEB, "template.json")
    if not os.path.isfile(path):
        raise web.HTTPNotFound()
    return web.FileResponse(path, headers=NO_CACHE)


@routes.get("/artflow/template/{name}")
async def artflow_family_template(request):
    name = request.match_info["name"]
    if not re.fullmatch(r"template(-[a-z0-9]+)?\.json", name):
        raise web.HTTPNotFound()
    path = os.path.join(WEB, name)
    if not os.path.isfile(path):
        raise web.HTTPNotFound()
    return web.FileResponse(path, headers=NO_CACHE)


@routes.get("/artflow/catalog")
async def artflow_catalog(request):
    cat = _catalog()
    for m in cat["models"]:
        m["installed"] = _installed(m)
        m["download"] = DL.get(m["id"])
    return web.json_response(cat, headers=NO_CACHE)


@routes.post("/artflow/download")
async def artflow_download(request):
    body = await request.json()
    mid = str(body.get("id", ""))
    m = next((x for x in _catalog()["models"] if x["id"] == mid), None)
    if not m:
        return web.json_response({"error": "unknown model"}, status=404)
    if body.get("cancel"):
        task = TASKS.get(mid)
        if task:
            task.cancel()
        return web.json_response({"ok": True})
    if _installed(m):
        DL[mid] = {"state": "done", "done": m.get("size", 0), "total": m.get("size", 0), "error": "", "speed": 0}
        return web.json_response({"ok": True, "installed": True})
    if mid not in TASKS:
        TASKS[mid] = asyncio.ensure_future(_download(m))
    return web.json_response({"ok": True})


def _media_dir(kind):
    if kind == "temp":
        return folder_paths.get_temp_directory()
    if kind == "input":
        return folder_paths.get_input_directory()
    return folder_paths.get_output_directory()


@routes.post("/artflow/open-folder")
async def artflow_open_folder(request):
    """Opens Windows Explorer on the folder of a generated image and selects the file (local use only)."""
    body = await request.json()
    base = os.path.abspath(_media_dir(str(body.get("type", "output"))))
    path = os.path.abspath(os.path.join(base, str(body.get("subfolder", "") or ""), os.path.basename(str(body.get("filename", "")))))
    if not path.startswith(base + os.sep) and path != base:
        return web.json_response({"error": "outside the media folders"}, status=400)
    if os.name != "nt":
        return web.json_response({"error": "only supported on Windows"}, status=400)
    folder = path if os.path.isdir(path) else os.path.dirname(path)
    await asyncio.get_running_loop().run_in_executor(None, _open_explorer, path, folder)
    return web.json_response({"ok": True})


def _explorer_windows():
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    found = []
    buf = ctypes.create_unicode_buffer(256)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        u.GetClassNameW(h, buf, 256)
        if buf.value == "CabinetWClass" and u.IsWindowVisible(h):
            t = ctypes.create_unicode_buffer(512)
            u.GetWindowTextW(h, t, 512)
            found.append((h, t.value))
        return True
    u.EnumWindows(cb, 0)
    return found


def _bring_front(h):
    """Windows only lets the foreground app raise windows; a short Alt tap lifts that lock for us."""
    import ctypes
    u = ctypes.windll.user32
    u.keybd_event(0x12, 0, 0, 0)
    u.keybd_event(0x12, 0, 2, 0)
    if u.IsIconic(h):
        u.ShowWindow(h, 9)
    u.ShowWindow(h, 5)
    u.BringWindowToTop(h)
    u.SetForegroundWindow(h)


def _open_explorer(path, folder):
    before = set()
    try:
        before = {h for h, _ in _explorer_windows()}
    except Exception:
        pass
    if os.path.isfile(path):
        subprocess.Popen(["explorer", "/select," + path])
    else:
        subprocess.Popen(["explorer", folder])
    name = os.path.basename(os.path.normpath(folder)).lower()
    try:
        for _ in range(30):                     # up to ~3 s for the window to appear
            time.sleep(0.1)
            wins = _explorer_windows()
            new = [h for h, _ in wins if h not in before]
            same = [h for h, t in wins if t.lower() == name or t.lower().endswith("\\" + name)]
            if new or (same and _ > 8):
                _bring_front((new or same)[0])
                return
    except Exception:
        pass


PICK_PS = r"""
Add-Type -AssemblyName System.Windows.Forms
$f = New-Object System.Windows.Forms.Form -Property @{TopMost = $true; ShowInTaskbar = $false; StartPosition = 'CenterScreen'; Width = 1; Height = 1}
$f.Show(); $f.Activate()
$d = New-Object System.Windows.Forms.OpenFileDialog
$d.InitialDirectory = $env:AF_START
$d.Filter = 'Images|*.png;*.jpg;*.jpeg;*.webp;*.bmp|All files|*.*'
$d.Title = 'ArtFlawless Studio'
if ($d.ShowDialog($f) -eq 'OK') { [Console]::Out.Write($d.FileName) }
$f.Close()
"""


def _pick_file(start):
    env = dict(os.environ, AF_START=start)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-Command", PICK_PS],
                       capture_output=True, env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.stdout.decode("utf-8", "replace").strip()


@routes.post("/artflow/pick-image")
async def artflow_pick_image(request):
    """Native Windows file dialog that starts in the input folder; a file chosen elsewhere is copied into it."""
    if os.name != "nt":
        return web.json_response({"error": "only supported on Windows"}, status=400)
    inp = os.path.abspath(folder_paths.get_input_directory())
    chosen = await asyncio.get_running_loop().run_in_executor(None, _pick_file, inp)
    if not chosen:
        return web.json_response({"cancelled": True})
    chosen = os.path.abspath(chosen)
    if chosen.startswith(inp + os.sep):
        name = os.path.relpath(chosen, inp).replace(os.sep, "/")
    else:
        base = os.path.basename(chosen)
        stem, ext = os.path.splitext(base)
        name, i = base, 1
        while os.path.exists(os.path.join(inp, name)):
            name = "%s_%d%s" % (stem, i, ext)
            i += 1
        shutil.copy2(chosen, os.path.join(inp, name))
    return web.json_response({"name": name})


# ------------------------------------------------------------------ content check
# Every image the Studio shows is checked here, locally, on the CPU (no video memory is used):
#  - NudeNet (YOLOv8 detector of exposed body parts) and the Falconsai ViT classifier (normal / nsfw);
#    if either of them finds adult content, the Studio blurs the image (unless the filter is switched off)
#  - final images with adult content are moved into output\18+
#  - final PNG images get a machine-readable "AI-generated" mark (IPTC DigitalSourceType in XMP, EU AI Act art. 50)
NSFW_DIR = os.path.join(folder_paths.models_dir, "nsfw")
VIT_DIR = os.path.join(NSFW_DIR, "falconsai")
ADULT_SUB = "18+"
NN_FLAG = {"FEMALE_BREAST_EXPOSED": 0.45, "FEMALE_GENITALIA_EXPOSED": 0.35, "MALE_GENITALIA_EXPOSED": 0.35,
           "ANUS_EXPOSED": 0.35, "BUTTOCKS_EXPOSED": 0.55}
VIT_FLAG = 0.75
_DET = {"nn": None, "vit": None, "err": {}}
_DET_LOCK = threading.Lock()
_CHECKED = {}   # path -> (mtime, result)


def _nudenet():
    if _DET["nn"] is None:
        try:
            import onnxruntime
            import nudenet.nudenet as nm
            path = os.path.join(os.path.dirname(nm.__file__), "320n.onnx")
            sess = onnxruntime.InferenceSession(path, providers=["CPUExecutionProvider"])
            _DET["nn"] = (sess, nm)
        except Exception as e:
            _DET["nn"] = False
            _DET["err"]["nudenet"] = str(e)
    return _DET["nn"] or None


def _falconsai():
    if _DET["vit"] is None:
        try:
            if not os.path.isfile(os.path.join(VIT_DIR, "model.safetensors")):
                raise FileNotFoundError("model not installed: " + VIT_DIR)
            from transformers import AutoImageProcessor, AutoModelForImageClassification
            proc = AutoImageProcessor.from_pretrained(VIT_DIR)
            model = AutoModelForImageClassification.from_pretrained(VIT_DIR).to("cpu").eval()
            _DET["vit"] = (proc, model)
        except Exception as e:
            _DET["vit"] = False
            _DET["err"]["falconsai"] = str(e)
    return _DET["vit"] or None


def _detect(path):
    """{"nsfw": bool|None, "score": 0..1, "reasons": [...], "detectors": [...]}; None = no detector available."""
    import numpy as np
    with open(path, "rb") as f:
        data = f.read()
    res = {"nsfw": False, "score": 0.0, "reasons": [], "detectors": []}
    with _DET_LOCK:
        nn = _nudenet()
        if nn:
            import cv2
            sess, nm = nn
            mat = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if mat is not None:
                blob, xr, yr, xp, yp, w, h = nm._read_image(mat, 320)
                out = sess.run(None, {sess.get_inputs()[0].name: blob})
                for d in nm._postprocess(out, xp, yp, xr, yr, w, h, 320, 320):
                    lim = NN_FLAG.get(d["class"])
                    if lim is not None and d["score"] >= lim:
                        res["nsfw"] = True
                        res["reasons"].append("%s %.2f" % (d["class"], d["score"]))
                        res["score"] = max(res["score"], float(d["score"]))
                res["detectors"].append("nudenet")
        vit = _falconsai()
        if vit:
            import io
            import torch
            from PIL import Image
            proc, model = vit
            img = Image.open(io.BytesIO(data)).convert("RGB")
            with torch.no_grad():
                logits = model(**proc(images=img, return_tensors="pt")).logits[0]
            probs = torch.softmax(logits.float(), dim=-1)
            idx = {str(k).lower(): int(v) for k, v in (model.config.label2id or {}).items()}.get("nsfw", 1)
            p = float(probs[idx])
            if p >= VIT_FLAG:
                res["nsfw"] = True
                res["reasons"].append("falconsai %.2f" % p)
            res["score"] = max(res["score"], p if p >= VIT_FLAG else 0.0)
            res["detectors"].append("falconsai")
    if not res["detectors"]:
        res["nsfw"] = None
    return res


XMP_AI = ('<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
          '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
          '<rdf:Description rdf:about="" xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
          'xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/" '
          'Iptc4xmpExt:DigitalSourceType="http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia" '
          'xmp:CreatorTool="ArtFlawless Studio">'
          '<dc:description><rdf:Alt><rdf:li xml:lang="x-default">AI-generated image (ArtFlawless Studio)</rdf:li></rdf:Alt></dc:description>'
          '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>')


def _png_chunk(kind, payload):
    import struct
    import zlib
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def _mark_png(path):
    """Adds the XMP "AI-generated" packet and a tEXt note before IEND, without re-encoding the image."""
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or b"trainedAlgorithmicMedia" in data:
        return False
    end = data.rfind(b"IEND")
    if end < 4:
        return False
    end -= 4
    itxt = b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + XMP_AI.encode("utf-8")
    note = b"AI-Generated\x00Yes - image created with generative AI (ArtFlawless Studio)"
    tmp = path + ".mark"
    with open(tmp, "wb") as f:
        f.write(data[:end] + _png_chunk(b"iTXt", itxt) + _png_chunk(b"tEXt", note) + data[end:])
    os.replace(tmp, path)
    return True


def _check(body):
    kind = str(body.get("type", "output"))
    if kind not in ("output", "temp"):
        return {"error": "unsupported type"}, 400
    base = os.path.abspath(_media_dir(kind))
    sub = str(body.get("subfolder", "") or "")
    path = os.path.abspath(os.path.join(base, sub, os.path.basename(str(body.get("filename", "")))))
    if not path.startswith(base + os.sep) or not os.path.isfile(path):
        return {"error": "not found"}, 404
    if body.get("discard"):
        os.remove(path)
        _CHECKED.pop(path, None)
        return {"ok": True, "discarded": True}, 200
    mt = os.path.getmtime(path)
    hit = _CHECKED.get(path)
    if hit and hit[0] == mt and (hit[1].get("nsfw") or not body.get("force")):
        return dict(hit[1]), 200
    rel0 = os.path.relpath(os.path.dirname(path), base).replace("\\", "/")
    if kind == "output" and (rel0 == ADULT_SUB or rel0.startswith(ADULT_SUB + "/")):
        body = dict(body, force=True)   # already sorted into output\18+ earlier: stays adult
    if body.get("force"):   # the prompt itself asks for nudity / sexual content: adult, whatever the detectors see
        res = {"nsfw": True, "score": 1.0, "reasons": ["prompt"], "detectors": ["prompt"]}
    else:
        res = _detect(path)
    if kind == "output":
        try:
            res["marked"] = _mark_png(path) if path.lower().endswith(".png") else False
        except Exception as e:
            res["marked"] = False
            res["markError"] = str(e)
        rel = os.path.relpath(os.path.dirname(path), base)
        parts = [] if rel == "." else rel.replace("\\", "/").split("/")
        if res["nsfw"] and (not parts or parts[0] != ADULT_SUB) and not body.get("noMove"):
            dest_dir = os.path.join(base, ADULT_SUB, *parts)
            os.makedirs(dest_dir, exist_ok=True)
            name = os.path.basename(path)
            stem, ext = os.path.splitext(name)
            i = 1
            while os.path.exists(os.path.join(dest_dir, name)):
                name = "%s_%d%s" % (stem, i, ext)
                i += 1
            dest = os.path.join(dest_dir, name)
            shutil.move(path, dest)
            res["moved"] = {"filename": name, "subfolder": "/".join([ADULT_SUB] + parts), "type": "output"}
            path = dest
    _CHECKED[path] = (os.path.getmtime(path), {k: v for k, v in res.items() if k != "moved"})
    return res, 200


@routes.post("/artflow/check")
async def artflow_check(request):
    """Checks one image of the output or temp folder for adult content (see above)."""
    body = await request.json()
    try:
        res, status = await asyncio.get_running_loop().run_in_executor(None, _check, body)
    except Exception as e:
        res, status = {"error": str(e)}, 500
    return web.json_response(res, status=status, headers=NO_CACHE)


IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")


def _recent(limit):
    base = os.path.abspath(folder_paths.get_output_directory())
    found = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.lower().endswith(IMG_EXT):
                p = os.path.join(root, f)
                try:
                    found.append((os.path.getmtime(p), p))
                except OSError:
                    pass
    found.sort(reverse=True)
    out = []
    for mt, p in found[:limit]:
        rel = os.path.relpath(os.path.dirname(p), base)
        out.append({"filename": os.path.basename(p), "subfolder": "" if rel == "." else rel.replace("\\", "/"),
                    "type": "output", "mtime": int(mt * 1000)})
    return out


@routes.get("/artflow/recent")
async def artflow_recent(request):
    """The newest images of the output folder (with subfolders such as 18+), newest first - the Studio's history strip."""
    try:
        limit = max(1, min(200, int(request.query.get("limit", "40"))))
    except ValueError:
        limit = 40
    files = await asyncio.get_running_loop().run_in_executor(None, _recent, limit)
    return web.json_response({"files": files}, headers=NO_CACHE)


@routes.post("/artflow/exists")
async def artflow_exists(request):
    """Which of the given images (output / temp / input folder) still exist - files deleted in Explorer leave the Studio's lists."""
    body = await request.json()
    out = []
    for f in (body.get("files") or [])[:500]:
        try:
            base = os.path.abspath(_media_dir(str(f.get("type", "output"))))
            path = os.path.abspath(os.path.join(base, str(f.get("subfolder", "") or ""), os.path.basename(str(f.get("filename", "")))))
            out.append(path.startswith(base + os.sep) and os.path.isfile(path))
        except Exception:
            out.append(True)
    return web.json_response({"exists": out}, headers=NO_CACHE)


@routes.get("/artflow/check-status")
async def artflow_check_status(request):
    def st():
        with _DET_LOCK:
            return {"nudenet": bool(_nudenet()), "falconsai": bool(_falconsai()), "errors": dict(_DET["err"])}
    return web.json_response(await asyncio.get_running_loop().run_in_executor(None, st), headers=NO_CACHE)


@routes.get("/artflow/downloads")
async def artflow_downloads(request):
    return web.json_response(DL, headers=NO_CACHE)


# ---------------- Hungarian prompting: HU -> EN translator (runs locally) ----------------
# The model (ArtFlawless HU->EN, a fine-tuned opus-mt-tc-big-hu-en, CC-BY 4.0) is downloaded once into
# models/translate/<id>; catalog.json "translator" lists its files. It stays in RAM and borrows about 0.5 GB of VRAM
# only while it translates (if the GPU has room); otherwise it translates on the CPU.
TR_LOCK = threading.Lock()
_TR = {"model": None, "tok": None, "err": "", "cache": {}}
TR_TAG = re.compile(r"(<[^<>]*>|\([^()]*:\s*-?\d+(?:\.\d+)?\s*\))")   # <lora:..>, <embedding> and (text:1.2) weights
TR_W = re.compile(r"^\(([^()]*):\s*(-?\d+(?:\.\d+)?)\s*\)$")
TR_MAX = 100        # tokens per piece (about 2-3 sentences, the length it was trained on); longer text is cut at sentence ends, then at commas


def _tr_info():
    return _catalog().get("translator") or {}


def _tr_dir(info=None):
    info = info or _tr_info()
    return os.path.join(folder_paths.models_dir, "translate", info.get("id", "artflawless-hu-en-v1"))


def _tr_installed(info=None):
    info = info or _tr_info()
    d = _tr_dir(info)
    files = info.get("files") or {}
    if not files:
        return False
    for name, size in files.items():
        p = os.path.join(d, name)
        if not os.path.isfile(p) or os.path.getsize(p) < int(size * 0.98):
            return False
    return True


async def _tr_download(info):
    st = DL["translator"] = {"state": "running", "done": 0, "total": int(sum((info.get("files") or {}).values())), "error": "", "speed": 0}
    d = _tr_dir(info)
    os.makedirs(d, exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=120)
    headers = {"User-Agent": "ArtFlawlessStudio/1.4"}
    base_done = 0
    try:
        for name, size in (info.get("files") or {}).items():
            dest = os.path.join(d, name)
            if os.path.isfile(dest) and os.path.getsize(dest) >= int(size * 0.98):
                base_done += size
                st["done"] = base_done
                continue
            part = dest + ".part"
            urls = [u.rstrip("/") + "/" + name for u in (info.get("base_urls") or [info.get("base_url", "")]) if u]
            for attempt in range(1, 6):
                url = urls[(attempt - 1) % len(urls)]       # GitHub first, then the mirror (Hugging Face)
                have = os.path.getsize(part) if os.path.exists(part) else 0
                h = dict(headers)
                if have:
                    h["Range"] = "bytes=%d-" % have
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as s:
                        async with s.get(url, headers=h, allow_redirects=True) as r:
                            if r.status == 416:
                                break
                            if r.status not in (200, 206):
                                raise RuntimeError("HTTP %d (%s)" % (r.status, name))
                            if r.status == 200:
                                have = 0
                            st["done"] = base_done + have
                            t0, d0 = time.time(), st["done"]
                            with open(part, "ab" if have else "wb") as f:
                                async for chunk in r.content.iter_chunked(CHUNK):
                                    f.write(chunk)
                                    st["done"] += len(chunk)
                                    dt = time.time() - t0
                                    if dt > 1:
                                        st["speed"] = int((st["done"] - d0) / dt)
                                        t0, d0 = time.time(), st["done"]
                    break
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    st["error"] = str(e)
                    if attempt == 5:
                        raise
                    await asyncio.sleep(3 * attempt)
            got = os.path.getsize(part)
            if got < int(size * 0.98):
                raise RuntimeError("incomplete download: %s (%d of %d bytes)" % (name, got, size))
            os.replace(part, dest)
            base_done += size
            st["done"] = base_done
        st.update(state="done", done=st["total"], error="")
    except asyncio.CancelledError:
        st.update(state="cancelled")
        raise
    except Exception as e:
        st.update(state="error", error=str(e))
    finally:
        TASKS.pop("translator", None)


def _tr_load():
    if _TR["model"] is not None:
        return _TR["model"], _TR["tok"]
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    d = _tr_dir()
    tok = MarianTokenizer.from_pretrained(d)
    model = MarianMTModel.from_pretrained(d, dtype=torch.float16).eval()   # kept in RAM; moved to the GPU only while translating
    _TR["model"], _TR["tok"], _TR["cpu32"] = model, tok, None
    return model, tok


def _tr_ct2():
    """CPU translation with CTranslate2 (int8), about 8x faster than PyTorch on the processor with the same quality
    (tools/mt 80_cpu_speed: 0.3 s instead of 2.3 s per sentence). Used only when the ctranslate2 package is installed;
    the int8 copy is made once from the downloaded model (a few seconds) next to it and remade when the model changes."""
    if _TR.get("ct2") is False:
        return None
    if _TR.get("ct2") is not None:
        return _TR["ct2"]
    try:
        import ctranslate2
    except Exception:
        _TR["ct2"] = False
        return None
    try:
        src = _tr_dir()
        dst = src.rstrip("\\/") + "-ct2int8"
        st = os.stat(os.path.join(src, "model.safetensors"))
        stamp = "%d %d" % (st.st_size, int(st.st_mtime))
        mark = os.path.join(dst, "source.txt")
        if not (os.path.isfile(mark) and open(mark, encoding="utf-8").read().strip() == stamp):
            tmp = dst + ".tmp"
            shutil.rmtree(tmp, ignore_errors=True)
            ctranslate2.converters.TransformersConverter(src).convert(tmp, quantization="int8", force=True)
            open(os.path.join(tmp, "source.txt"), "w", encoding="utf-8").write(stamp)
            shutil.rmtree(dst, ignore_errors=True)
            os.replace(tmp, dst)
        _TR["ct2"] = ctranslate2.Translator(dst, device="cpu", compute_type="int8",
                                            intra_threads=max(1, min(8, (os.cpu_count() or 4) // 2 or 1)))
    except Exception as e:
        print("[ArtFlawless Studio] CTranslate2 not used:", e)
        _TR["ct2"] = False
        return None
    return _TR["ct2"]


def _tr_generate(batch):
    """Translates on the GPU when it has room (about 0.5 GB, a fraction of a second), otherwise on the CPU (a few seconds)."""
    import torch
    model, tok = _TR["model"], _TR["tok"]
    b = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=256)
    kw = dict(num_beams=4, max_length=400, no_repeat_ngram_size=4)
    if torch.cuda.is_available():
        try:
            if torch.cuda.mem_get_info()[0] > 1536 * 1024 * 1024:
                try:
                    model.to("cuda")
                    with torch.inference_mode():
                        g = model.generate(**{k: v.to("cuda") for k, v in b.items()}, **kw)
                    return tok.batch_decode(g.cpu(), skip_special_tokens=True)
                finally:
                    model.to("cpu")
                    torch.cuda.empty_cache()
        except Exception:      # out of memory or the GPU is busy: the CPU does it
            pass
    ct = _tr_ct2()
    if ct is not None:
        try:
            res = ct.translate_batch([tok.convert_ids_to_tokens(tok.encode(t)) for t in batch],
                                     beam_size=4, no_repeat_ngram_size=4, max_decoding_length=400)
            return [tok.decode(tok.convert_tokens_to_ids(r.hypotheses[0]), skip_special_tokens=True) for r in res]
        except Exception as e:
            _TR["ct2"] = False
            print("[ArtFlawless Studio] CTranslate2 translation failed, using PyTorch:", e)
    if _TR.get("cpu32") is None:
        import copy
        _TR["cpu32"] = copy.deepcopy(model).float()
    torch.set_num_threads(max(1, min(8, (os.cpu_count() or 4) // 2 or 1)))
    with torch.inference_mode():
        g = _TR["cpu32"].generate(**b, **kw)
    return tok.batch_decode(g, skip_special_tokens=True)


def _tr_pieces(text, tok):
    """Cut a line into pieces the model handles well; returns a list of (kind, value): ("t", text to translate) or ("k", kept as is)."""
    out = []
    for part in TR_TAG.split(text):
        if not part:
            continue
        if TR_TAG.fullmatch(part):
            m = TR_W.match(part)
            if m and re.search(r"[^\W\d_]", m.group(1)):
                out.append(("w", (m.group(1), m.group(2))))
            else:
                out.append(("k", part))
            continue
        lead = re.match(r"^[\s,;]*", part).group(0)     # separators around a piece are kept as they are
        trail = re.search(r"[\s,;]*$", part[len(lead):]).group(0)
        body = part[len(lead):len(part) - len(trail)]
        if lead:
            out.append(("k", lead))
        if body:
            if not re.search(r"[^\W\d_]", body):       # numbers and punctuation only
                out.append(("k", body))
            else:
                for i, chunk in enumerate(_tr_split(body, tok)):
                    if i:
                        out.append(("k", " "))
                    out.append(("t", chunk))
        if trail:
            out.append(("k", trail))
    return out


def _tr_split(body, tok):
    n = lambda x: len(tok(x)["input_ids"])
    sents = re.split(r"(?<=[.!?])\s+", body)
    if n(body) <= TR_MAX and len(set(sents)) == len(sents):
        return [body]
    res = []
    for sent in sents:
        if n(sent) <= TR_MAX:
            res.append(sent)
            continue
        cur = ""
        for item in re.split(r"(?<=,)\s*", sent):
            if cur and n(cur + " " + item) > TR_MAX:
                res.append(cur)
                cur = item
            else:
                cur = (cur + " " + item).strip()
        if cur:
            res.append(cur)
    # glue short neighbours back together, so the model keeps the context
    glued = []
    for x in res:
        if glued and x not in glued[-1] and n(glued[-1] + " " + x) <= TR_MAX:   # a repeated sentence goes alone (the model may not repeat itself)
            glued[-1] = glued[-1] + " " + x
        else:
            glued.append(x)
    return glued


def _tr_run(texts):
    with TR_LOCK:
        model, tok = _tr_load()
        plans, todo = [], []
        for text in texts:
            lines = []
            for line in str(text).split("\n"):
                pcs = _tr_pieces(line, tok)
                lines.append(pcs)
                for kind, v in pcs:
                    src = v if kind == "t" else v[0] if kind == "w" else None
                    if src is not None and src not in _TR["cache"] and src not in todo:
                        todo.append(src)
            plans.append(lines)
        for i in range(0, len(todo), 8):
            batch = todo[i:i + 8]
            for src, out in zip(batch, _tr_generate(batch)):
                out = out.strip()
                if not re.search(r"[.!?]$", src.strip()):      # the model likes to close a fragment with a full stop
                    out = re.sub(r"\.$", "", out)
                _TR["cache"][src] = out
        if len(_TR["cache"]) > 2000:
            _TR["cache"] = dict(list(_TR["cache"].items())[-1000:])
        res = []
        for lines in plans:
            done = []
            for pcs in lines:
                s = ""
                for kind, v in pcs:
                    if kind == "t":
                        s += _TR["cache"][v]
                    elif kind == "w":
                        s += "(%s:%s)" % (_TR["cache"][v[0]], v[1])
                    else:
                        s += v
                done.append(s)
            res.append("\n".join(done))
        return res


@routes.get("/artflow/translate/status")
async def artflow_translate_status(request):
    info = _tr_info()
    return web.json_response({"installed": _tr_installed(info), "size": int(sum((info.get("files") or {}).values())),
                              "id": info.get("id", ""), "license": info.get("license", ""), "dl": DL.get("translator"),
                              "loaded": _TR["model"] is not None, "error": _TR["err"]}, headers=NO_CACHE)


@routes.post("/artflow/translate/download")
async def artflow_translate_download(request):
    body = await request.json()
    info = _tr_info()
    if not info.get("files"):
        return web.json_response({"error": "no translator in the catalog"}, status=404)
    if body.get("cancel"):
        task = TASKS.get("translator")
        if task:
            task.cancel()
        return web.json_response({"ok": True})
    if _tr_installed(info):
        DL["translator"] = {"state": "done", "done": 0, "total": 0, "error": "", "speed": 0}
        return web.json_response({"ok": True, "installed": True})
    if "translator" not in TASKS:
        TASKS["translator"] = asyncio.ensure_future(_tr_download(info))
    return web.json_response({"ok": True})


@routes.post("/artflow/translate")
async def artflow_translate(request):
    body = await request.json()
    texts = body.get("texts")
    if not isinstance(texts, list) or not all(isinstance(x, str) for x in texts) or sum(len(x) for x in texts) > 20000:
        return web.json_response({"error": "bad request"}, status=400)
    if not _tr_installed():
        return web.json_response({"error": "the translator is not installed"}, status=409)
    t0 = time.time()
    try:
        out = await asyncio.get_running_loop().run_in_executor(None, _tr_run, texts)
        _TR["err"] = ""
    except Exception as e:
        _TR["err"] = str(e)
        return web.json_response({"error": str(e)}, status=500)
    return web.json_response({"texts": out, "ms": int((time.time() - t0) * 1000)}, headers=NO_CACHE)


# ---------- model kind: which family a checkpoint / LoRA file belongs to (reads only the file header, no weights) ----------
_MK_CACHE = {}
_DT_BYTES = {"F64": 8, "F32": 4, "F16": 2, "BF16": 2, "F8_E4M3": 1, "F8_E5M2": 1, "I8": 1, "U8": 1, "I16": 2, "I32": 4, "I64": 8}


def _st_header(p):
    import struct
    with open(p, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        if n > 200 * 1024 * 1024:
            raise ValueError("header too large")
        hd = json.loads(f.read(n))
    meta = hd.pop("__metadata__", None) or {}
    return hd, meta


def _gguf_header(p):
    """architecture and tensor names of a GGUF file (metadata keys/values are skipped, only names are read)"""
    import struct
    with open(p, "rb") as f:
        if f.read(4) != b"GGUF":
            raise ValueError("not a GGUF file")
        ver = struct.unpack("<I", f.read(4))[0]
        nt, nkv = struct.unpack("<QQ", f.read(16))
        sizes = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}

        def rstr():
            ln = struct.unpack("<Q", f.read(8))[0]
            return f.read(ln).decode("utf-8", "replace")

        def rval(t):
            if t == 8:
                return rstr()
            if t == 9:
                at, ln = struct.unpack("<IQ", f.read(12))
                if at == 8:
                    return [rstr() for _ in range(ln)][:4]
                f.seek(sizes[at] * ln, 1); return None
            b = f.read(sizes[t])
            return b
        meta = {}
        for _ in range(nkv):
            k = rstr(); t = struct.unpack("<I", f.read(4))[0]; v = rval(t)
            if isinstance(v, str):
                meta[k] = v
        names = []
        for _ in range(min(nt, 4000)):
            names.append(rstr()); nd = struct.unpack("<I", f.read(4))[0]; f.seek(8 * nd + 4 + 8, 1)
    return names, meta


def _kind_of(keys, meta, fname):
    has = lambda s: any(s in k for k in keys)
    arch = " ".join(str(meta.get(k, "")) for k in ("modelspec.architecture", "ss_base_model_version", "general.architecture", "ss_sd_model_name")).lower()
    low = (arch + " " + fname.lower())
    if has("double_blocks") or has("single_blocks") or has("single_transformer_blocks") or "flux" in arch:
        kind = "flux"
        if has("distilled_guidance_layer") or "chroma" in low:
            kind = "chroma"
    elif has("joint_blocks") or "sd3" in arch or "stable-diffusion-v3" in arch:
        kind = "sd3"
    elif has("cap_embedder") or (has("adaLN_modulation") and has("layers.")) or (has("layers.") and has("feed_forward.w1")) \
            or "zimage" in arch or "z-image" in arch or "lumina" in arch:
        kind = "zimage"
    elif has("transformer_blocks.0.img_mod") or "qwen_image" in arch or "qwen-image" in arch:
        kind = "qwen_image"
    elif has("conditioner.embedders.1") or has("lora_te2_") or has("input_blocks.7.1.transformer_blocks.9") \
            or has("input_blocks_7_1_transformer_blocks_9") or has("down_blocks.2.attentions.1.transformer_blocks.9") \
            or has("down_blocks_2_attentions_1_transformer_blocks_9") or "xl" in arch or "sdxl" in arch:
        kind = "sdxl"
    elif has("cond_stage_model") or has("lora_te_text_model") or has("input_blocks") or has("lora_unet_down_blocks") \
            or has("down_blocks") or "v1" in arch or "sd1" in arch or "sd_v1" in arch:
        kind = "sd15"
    else:
        kind = "unknown"
    sub = ""
    if kind == "sdxl":
        if "pony" in low:
            sub = "pony"
        elif "illustrious" in low or "noob" in low:
            sub = "illustrious"
    if kind == "flux":
        sub = "dev" if (has("guidance_in") or "dev" in low) and "schnell" not in low else "schnell"
    return kind, sub


# caption words that are in almost every training set; they are never the trigger of a LoRA
_COMMON_TAGS = {"1girl", "1boy", "2girls", "solo", "realistic", "photorealistic", "looking at viewer", "looking_at_viewer", "long hair", "long_hair",
                "short hair", "short_hair", "lips", "smile", "simple background", "white background", "blurry", "blurry background", "female",
                "male", "woman", "man", "girl", "boy", "upper body", "full body", "portrait", "photo", "no humans", "outdoors", "indoors",
                "breasts", "brown hair", "black hair", "blonde hair", "brown eyes", "blue eyes", "closed mouth", "open mouth", "teeth"}


def _triggers(meta):
    """trigger words of a LoRA from its training metadata: the stated trigger phrase, otherwise the words that are in (nearly) every
    caption of a training folder (kohya ss_tag_frequency against the image count). Returns (triggers, other frequent training tags)."""
    trig, tags = [], []
    add = lambda arr, x: (x and x not in trig and x not in tags and arr.append(x))
    tp = meta.get("modelspec.trigger_phrase") or meta.get("ss_activation_text") or meta.get("trigger_words") or ""
    for x in re.split(r"[,\n]", str(tp)):
        add(trig, x.strip())
    try:
        tf = json.loads(meta.get("ss_tag_frequency") or "{}")
        dirs = {}
        try:
            dirs = json.loads(meta.get("ss_dataset_dirs") or "{}")
        except Exception:
            pass
        cnt = {}
        for dname, ds in tf.items():
            n_img = int((dirs.get(dname) or {}).get("img_count") or 0) or max([int(v) for v in ds.values()] or [0])
            for tag, n in ds.items():
                tag = tag.strip().replace("\\(", "(").replace("\\)", ")")
                if not tag:
                    continue
                cnt[tag] = cnt.get(tag, 0) + int(n)
                # a folder with one single tag is a class word made from the folder name, unless it is the only training folder
                if (len(ds) > 1 or len(tf) == 1) and n_img and int(n) >= 0.9 * n_img and tag.lower().replace("_", " ") not in _COMMON_TAGS and len(trig) < 4:
                    add(trig, tag)
        for tag, _ in sorted(cnt.items(), key=lambda x: -x[1]):
            if len(tags) >= 10:
                break
            add(tags, tag)
    except Exception:
        pass
    return trig[:6], tags


def _norm_module(k):
    """module path of a weight or LoRA key in a common form, for comparing a LoRA with a model"""
    k = re.sub(r"\.(lora_(up|down|A|B)|lora\.(up|down)|alpha|hada_w\d_[ab]|lokr_w\d|dora_scale|diff|diff_b)(\.weight)?$", "", k)
    k = re.sub(r"\.(weight|bias|scale|weight_scale)$", "", k)
    # Z-Image / Lumina LoRAs train q, k and v separately; the model keeps them in one qkv weight
    k = re.sub(r"attention\.to_[qkv]$", "attention.qkv", k)
    k = re.sub(r"attention\.to_out\.0$", "attention.out", k)
    for pre in ("model.diffusion_model.", "diffusion_model.", "lora_unet_", "unet.", "transformer."):
        if k.startswith(pre):
            k = k[len(pre):]
            break
    return k.replace(".", "_")


def _model_kind(folder, name):
    p = folder_paths.get_full_path(folder, name)
    if not p or not os.path.isfile(p):
        return {"kind": "missing"}
    st = os.stat(p); key = (p, st.st_size, int(st.st_mtime))
    if key in _MK_CACHE:
        return _MK_CACHE[key]
    res = {"kind": "unknown", "clip": None, "vae": None, "size": st.st_size, "format": os.path.splitext(p)[1].lower().lstrip(".")}
    keys, meta, dt = [], {}, {}
    if p.lower().endswith(".safetensors") or p.lower().endswith(".sft"):
        hd, meta = _st_header(p); keys = list(hd)
        for v in hd.values():
            try:
                n = 1
                for d in v.get("shape", []):
                    n *= d
                dt[v.get("dtype", "?")] = dt.get(v.get("dtype", "?"), 0) + n
            except Exception:
                pass
    elif p.lower().endswith(".gguf"):
        keys, meta = _gguf_header(p); dt = {"GGUF": 1}
    else:
        _MK_CACHE[key] = res
        return res
    kind, sub = _kind_of(keys, meta, os.path.basename(p))
    has = lambda s: any(s in k for k in keys)
    res.update(kind=kind, sub=sub, dtype=max(dt, key=dt.get) if dt else "",
               clip=has("cond_stage_model") or has("conditioner.") or has("text_encoders."),
               vae=has("first_stage_model") or has("vae."))
    if folder == "loras":
        res["triggers"], res["tags"] = _triggers(meta)
        if keys and all(k in ("emb_params", "string_to_param", "string_to_token", "clip_l", "clip_g", "name", "step") or k.startswith("string_to_param.") for k in keys):
            res.update(kind="embedding", notlora="embedding")
        elif res["clip"] and res["vae"]:
            res["notlora"] = "checkpoint"
        res["te"] = has("lora_te") or has("text_encoder") or has("lora_clip")
        res["_mods"] = sorted({_norm_module(k) for k in keys if not re.search(r"lora_te|text_encoder|lora_clip|^te_|^clip_", k)})
    else:
        res["_mods"] = sorted({_norm_module(k) for k in keys})
    _MK_CACHE[key] = res
    return res


def _public(r):
    return {k: v for k, v in r.items() if not k.startswith("_")}


def _lora_match(mfolder, mname, lname):
    m = _model_kind(mfolder, mname); lo = _model_kind("loras", lname)
    out = {"model": _public(m), "lora": _public(lo)}
    mm, lm = set(m.get("_mods") or []), lo.get("_mods") or []
    if mm and lm:
        hit = sum(1 for x in lm if x in mm)
        out["match"] = round(100 * hit / len(lm))
        # LoRAs saved in the diffusers / kohya naming are converted by ComfyUI while loading, so a low score there says nothing
        out["converted"] = out["match"] < 50 and any(re.match(r"^(transformer_|unet_|lora_unet_|down_blocks|up_blocks|mid_block)", x) or "_to_q" in x or "transformer_blocks" in x for x in lm)
    return out


@routes.get("/artflow/model-kind")
async def artflow_model_kind(request):
    folder = request.query.get("folder", "checkpoints")
    if folder not in ("checkpoints", "loras", "diffusion_models", "unet", "unet_gguf"):
        return web.json_response({"error": "bad folder"}, status=400)
    try:
        r = _public(await asyncio.get_running_loop().run_in_executor(None, _model_kind, folder, request.query.get("name", "")))
    except Exception as e:
        r = {"kind": "unknown", "error": str(e)}
    return web.json_response(r, headers=NO_CACHE)


@routes.get("/artflow/lora-match")
async def artflow_lora_match(request):
    q = request.query
    folder = q.get("folder", "checkpoints")
    if folder not in ("checkpoints", "diffusion_models", "unet", "unet_gguf"):
        return web.json_response({"error": "bad folder"}, status=400)
    try:
        r = await asyncio.get_running_loop().run_in_executor(None, _lora_match, folder, q.get("model", ""), q.get("lora", ""))
    except Exception as e:
        r = {"error": str(e)}
    return web.json_response(r, headers=NO_CACHE)


# ---------- system load for the header meters (GPU and CPU usage in percent) ----------
_LOAD = {"t": 0.0, "v": None, "nvml": None}


def _gpu_load():
    if _LOAD["nvml"] is None:
        try:
            import pynvml
            pynvml.nvmlInit(); _LOAD["nvml"] = pynvml.nvmlDeviceGetHandleByIndex(0); _LOAD["pynvml"] = pynvml
        except Exception:
            _LOAD["nvml"] = False
    if _LOAD["nvml"]:
        try:
            nv = _LOAD["pynvml"]; h = _LOAD["nvml"]
            u = nv.nvmlDeviceGetUtilizationRates(h); m = nv.nvmlDeviceGetMemoryInfo(h)
            return {"gpu": int(u.gpu), "vram_used": int(m.used // 2**20), "vram_total": int(m.total // 2**20)}
        except Exception:
            pass
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=3, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        g, mu, mt = [int(float(x)) for x in r.stdout.strip().splitlines()[0].split(",")]
        return {"gpu": g, "vram_used": mu, "vram_total": mt}
    except Exception:
        return {"gpu": None}


def _sys_load():
    if _LOAD["v"] is not None and time.time() - _LOAD["t"] < 0.8:
        return _LOAD["v"]
    v = _gpu_load()
    try:
        import psutil
        vm = psutil.virtual_memory(); v["cpu"] = round(psutil.cpu_percent(interval=None)); v["ram"] = round(vm.percent); v["ram_total"] = int(vm.total // 2**20)
    except Exception:
        v["cpu"] = None
    _LOAD.update(t=time.time(), v=v)
    return v


@routes.get("/artflow/sysload")
async def artflow_sysload(request):
    return web.json_response(await asyncio.get_running_loop().run_in_executor(None, _sys_load), headers=NO_CACHE)


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# ArtFlawless Studio – ComfyUI add-on: serves the Studio page at /artflow, the family templates,
# a small model downloader (catalog.json lists what can be downloaded and where it goes)
# and the local content check of generated images (adult content, AI-generated mark).
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


@routes.get("/artflow/check-status")
async def artflow_check_status(request):
    def st():
        with _DET_LOCK:
            return {"nudenet": bool(_nudenet()), "falconsai": bool(_falconsai()), "errors": dict(_DET["err"])}
    return web.json_response(await asyncio.get_running_loop().run_in_executor(None, st), headers=NO_CACHE)


@routes.get("/artflow/downloads")
async def artflow_downloads(request):
    return web.json_response(DL, headers=NO_CACHE)


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

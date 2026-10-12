# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
# ArtFlawless Studio – ComfyUI add-on: serves the Studio page at /artflow, the family templates,
# and a small model downloader (catalog.json lists what can be downloaded and where it goes).
import asyncio
import json
import os
import re
import shutil
import subprocess
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
    headers = {"User-Agent": "ArtFlawlessStudio/1.2"}
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


@routes.get("/artflow/downloads")
async def artflow_downloads(request):
    return web.json_response(DL, headers=NO_CACHE)


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

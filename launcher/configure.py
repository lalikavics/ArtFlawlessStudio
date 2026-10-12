# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
"""Install-time helper (runs with ComfyUI's embedded Python).
Usage: python configure.py <template.json> <unet_weight_dtype>
Sets the diffusion model's weight dtype in the Studio template (node 2)."""
import json
import sys

path, dtype = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as f:
    t = json.load(f)
t["prompt"]["2"]["inputs"]["weight_dtype"] = dtype
with open(path, "w", encoding="utf-8") as f:
    json.dump(t, f, ensure_ascii=False, separators=(",", ":"))
print("weight_dtype =", dtype)

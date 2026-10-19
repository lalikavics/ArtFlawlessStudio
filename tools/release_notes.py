# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lalikavics - ArtFlawless Studio
"""Prints the CHANGELOG.md section of one version (used by the GitHub release workflow).
Usage: python tools/release_notes.py 1.2.0 [release-notes.md]
With a file name the notes are written there as UTF-8 (printing on a Windows runner fails on characters like →)."""
import os, re, sys

ver = sys.argv[1].lstrip('v')
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
text = open(os.path.join(root, 'CHANGELOG.md'), encoding='utf-8').read()
m = re.search(r'^## \[' + re.escape(ver) + r'\][^\n]*\n(.*?)(?=^## \[|\Z)', text, re.S | re.M)
notes = m.group(1).strip() if m else 'ArtFlawless Studio ' + ver
out = notes + '\n\n---\n\n*Developed with the help of Claude (Anthropic).*\n'
if len(sys.argv) > 2:
    open(sys.argv[2], 'w', encoding='utf-8').write(out)
else:
    sys.stdout.reconfigure(encoding='utf-8')
    print(out, end='')

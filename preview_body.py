# -*- coding: utf-8 -*-
"""Render the body, gauge and cord anchor to one shaded PNG sheet.

    python3 preview_body.py            -> preview_body.png
"""
import json
import os
import numpy as np

import stl_render as R

OUT = os.path.dirname(os.path.abspath(__file__))

# Read the caption dimensions from the build summary rather than hardcoding
# them: a hardcoded "36.30 OD" is exactly the kind of label that survives a
# revision change and lies to the reader.
with open(os.path.join(OUT, "build_summary.json")) as f:
    _S = json.load(f)
BODY_LABEL = "BODY %.2f OD / %.2f BORE" % (_S["od"], _S["bore"])


def panel(stl, az, el, label, pw=430, ph=640):
    tri = R.read_binary_stl(os.path.join(OUT, stl))
    im = R.render(tri, az, el, pw, ph, ss=2)
    return R.labelled(im, pw, ph, label)


panels = [
    panel("body36_cord_anchor.stl", 35, 18, "CORD ANCHOR  (glue-in)"),
    panel("body36_gauge.stl", 35, 18, "FIT GAUGE  20 mm"),
    panel("body36_aft.stl", 35, 12, "AFT  " + BODY_LABEL),
    panel("body36_fwd.stl", 35, 12, "FWD  " + BODY_LABEL),
    panel("body36_fwd.stl", 0, 89.9, "FWD - TOP DOWN (bosses)"),
]
sheet = np.concatenate(panels, axis=1)
R.write_png(os.path.join(OUT, "preview_body.png"), sheet)
print("wrote preview_body.png", sheet.shape)
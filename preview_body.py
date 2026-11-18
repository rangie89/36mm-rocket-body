# -*- coding: utf-8 -*-
"""Render the body, gauge and cord anchor to one shaded PNG sheet.

    python3 preview_body.py            -> preview_body.png
"""
import os
import numpy as np

import stl_render as R

OUT = os.path.dirname(os.path.abspath(__file__))


def panel(stl, az, el, label, pw=430, ph=640):
    tri = R.read_binary_stl(os.path.join(OUT, stl))
    im = R.render(tri, az, el, pw, ph, ss=2)
    return R.labelled(im, pw, ph, label)


panels = [
    panel("body36_cord_anchor.stl", 35, 18, "CORD ANCHOR  (glue-in)"),
    panel("body36_gauge.stl", 35, 18, "FIT GAUGE  20 mm"),
    panel("body36.stl", 35, 12, "BODY 36.00 OD / 32.80 BORE"),
    panel("body36.stl", 0, 89.9, "BODY - TOP DOWN (bore)"),
]
sheet = np.concatenate(panels, axis=1)
R.write_png(os.path.join(OUT, "preview_body.png"), sheet)
print("wrote preview_body.png", sheet.shape)
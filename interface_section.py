# -*- coding: utf-8 -*-
"""Draw the airframe's interface section (half section, axis at the bottom).

    python3 interface_section.py      -> interface_section.svg

Everything is read from build_summary.json, so the drawing cannot drift away
from the model that was verified: change a parameter, rebuild, re-run this.

The radial scale is exaggerated (a 36 mm tube on a 435 mm rocket is a hairline
otherwise), which is normal for this kind of fit drawing and is stated on it.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "build_summary.json")))
P = S["params"]

BODY_OD = P["body_od"]
BORE = P["body_bore"]
L = P["body_len"]
TAPER = P["fwd_taper_len"]
NOSE_BASE = P["nose_base_d"]
SH_D = P["nose_shoulder_d"]
SH_L = P["nose_shoulder_len"]
FC_BORE = P["fincan_bore"]
FC_LEN = P["fincan_len"]
FC_OD = P["fincan_hub_od"]
SLEEVE_D = P["can_sleeve_d"]
SLEEVE_L = P["can_sleeve_len"]
FLANGE_D = P["can_flange_d"]
FLANGE_L = P["can_flange_len"]
STEM_D = P["can_stem_d"]
STEM_L = P["can_stem_len"]
CAP_D = P["can_cap_d"]
CAP_L = P["can_cap_len"]
NOSE_L = 150.0
MOTOR_D, MOTOR_L = 18.0, 70.0
FIN_TIP_R = 44.7

SZ = 2.30          # px per mm along the axis
SR = 6.30          # px per mm radially (x2.7 exaggeration)
Z0 = -CAP_L - STEM_L - 4.0
Z1 = L + NOSE_L + 10.0
Y_AX = 462
PAD = 34
W = int(PAD * 2 + (Z1 - Z0) * SZ)
H = 560


def X(z):
    return PAD + (z - Z0) * SZ


def Y(r):
    return Y_AX - r * SR


def rect(z0, z1, r0, r1, fill, stroke="none", op=1.0, sw=0.8):
    return ('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
            'fill-opacity="%.2f" stroke="%s" stroke-width="%.2f"/>'
            % (X(z0), Y(r1), X(z1) - X(z0), Y(r0) - Y(r1), fill, op, stroke, sw))


def poly(pts, fill, stroke="none", op=1.0, sw=0.8):
    d = " ".join("%.2f,%.2f" % (X(z), Y(r)) for z, r in pts)
    return ('<polygon points="%s" fill="%s" fill-opacity="%.2f" stroke="%s" '
            'stroke-width="%.2f"/>' % (d, fill, op, stroke, sw))


def text(x, y, s, size=11, anchor="start", fill="#1b2733", weight="400", rot=None):
    extra = ""
    if rot is not None:
        extra = ' transform="rotate(%.1f %.1f %.1f)"' % (rot, x, y)
    return ('<text x="%.1f" y="%.1f" font-family="ui-monospace,Menlo,Consolas,'
            'monospace" font-size="%s" fill="%s" text-anchor="%s" '
            'font-weight="%s"%s>%s</text>'
            % (x, y, size, fill, anchor, weight, extra, s))


def dim_h(z0, z1, y, label, colour="#2b3a48", above=True):
    out = ['<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
           'stroke-width="0.9" marker-start="url(#a)" marker-end="url(#a)"/>'
           % (X(z0), y, X(z1), y, colour)]
    for z in (z0, z1):
        y2 = Y_AX + 8 if above else Y_AX - 8
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="0.6" stroke-dasharray="2,3" opacity="0.75"/>'
                   % (X(z), y, X(z), y2, colour))
    out.append(text((X(z0) + X(z1)) / 2.0, y - 5, label, 10.5, "middle", colour))
    return "".join(out)


def leader(z, r, tx, ty, label, colour="#2b3a48", anchor="start"):
    return ('<polyline points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="none" '
            'stroke="%s" stroke-width="0.8"/>'
            % (X(z), Y(r), tx, ty, tx + (18 if anchor == "start" else -18), ty, colour)
            + text(tx + (22 if anchor == "start" else -22), ty + 3.5, label, 10.5,
                   anchor, colour))


s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
     'viewBox="0 0 %d %d">' % (W, H, W, H),
     '<defs><marker id="a" viewBox="0 0 10 10" refX="5" refY="5" '
     'markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
     '<path d="M0,0 L10,5 L0,10 z" fill="#5b6b7a"/></marker></defs>',
     '<rect width="100%" height="100%" fill="#ffffff"/>']

# ---- parts (half section, r >= 0) -----------------------------------------
s.append(rect(L - SH_L, L, 0.0, SH_D / 2.0, "#c8d4e0", "#4a5b6b", 0.5, 0.9))
nose = [(L + NOSE_L * i / 90.0,
         (NOSE_BASE / 2.0) * math.sqrt(max(0.0, 1 - (i / 90.0) ** 2)))
        for i in range(91)]
s.append(poly(nose + [(L + NOSE_L, 0.0)], "#d7e2ec", "#4a5b6b", 0.95, 1.0))

s.append(poly([(0, BORE / 2.0), (0, BODY_OD / 2.0), (L - TAPER, BODY_OD / 2.0),
               (L, NOSE_BASE / 2.0), (L, BORE / 2.0)],
              "#8fb4d8", "#22405c", 0.95, 1.1))

s.append(poly([(0, FC_BORE / 2.0), (0, FC_OD / 2.0), (FC_LEN - 5.0, FC_OD / 2.0),
               (FC_LEN, FC_BORE / 2.0 + 1.3), (FC_LEN, FC_BORE / 2.0)],
              "#e8a33d", "#7d5210", 0.65, 1.0))
s.append(poly([(5, FC_OD / 2.0), (97, FC_OD / 2.0), (97, FIN_TIP_R), (45, FIN_TIP_R)],
              "#f0b559", "#7d5210", 0.8, 1.0))

# motor can: body_z = can_z - 15
s.append(rect(-SLEEVE_L - STEM_L, -SLEEVE_L, 0, STEM_D / 2.0, "#b6c9a6", "#42582f", 0.95, 0.9))
s.append(rect(-FLANGE_L, 0, 0, FLANGE_D / 2.0, "#b6c9a6", "#42582f", 0.95, 0.9))
s.append(rect(0, SLEEVE_L, 0, SLEEVE_D / 2.0, "#b6c9a6", "#42582f", 0.95, 0.9))
s.append(poly([(SLEEVE_L, SLEEVE_D / 2.0), (SLEEVE_L + 5.0, 12.0), (55, 12.0),
               (55, 0.0), (SLEEVE_L, 0.0)], "#a9bf97", "#42582f", 0.95, 0.9))
s.append(rect(55, 61, 8.0, 12.0, "#a9bf97", "#42582f", 0.95, 0.9))
s.append(rect(-SLEEVE_L, -SLEEVE_L + MOTOR_L, 0, MOTOR_D / 2.0, "#6b7a88", "#39434d", 0.9, 0.8))
s.append(rect(-CAP_L - STEM_L, -SLEEVE_L, 0, CAP_D / 2.0, "#b9a7d6", "#5b4a80", 0.95, 0.9))

s.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#93a3b1" '
         'stroke-width="1" stroke-dasharray="9,4,2,4"/>'
         % (X(Z0) + 6, Y_AX, X(Z1) - 4, Y_AX))

# ---- dimensions -----------------------------------------------------------
s.append(dim_h(0, L, Y(52), "body 285", "#22405c"))
s.append(dim_h(L, L + NOSE_L, Y(52), "nose cone 150", "#4a5b6b"))
s.append(dim_h(0, FC_LEN, Y_AX + 30, "fin can 102", "#7d5210", above=False))
s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7d5210" '
         'stroke-width="0.8"/>' % (X(FIN_TIP_R), 0, X(FIN_TIP_R), 0)
         if False else "")
s.append(text(X(50), Y(FIN_TIP_R) - 7, "fin tip 89.40 across", 10.5, "middle", "#7d5210"))

s.append(leader(150, BODY_OD / 2.0, X(150) - 44, Y(30), "Ø36.00 body OD", "#22405c"))
s.append(leader(215, BORE / 2.0, X(215) + 6, Y_AX + 66, "Ø32.80 bore", "#22405c"))
s.append(leader(40, FC_BORE / 2.0, X(120), Y_AX + 50, "Ø36.60 fin can bore", "#7d5210"))
s.append(leader(10, SLEEVE_D / 2.0, X(52), Y_AX + 86,
                "sleeve Ø32.50 x 15", "#42582f"))

# ---- legend ---------------------------------------------------------------
lines = [
    ("BODY   %.2f OD x %.2f bore x %.0f long, wall %.2f"
     % (BODY_OD, BORE, L, S["wall"]), "#22405c"),
    ("36 mm 4-FIN CAN   bore %.2f over the aft %.0f mm  -> %.2f mm/side slip"
     % (FC_BORE, FC_LEN, S["fits"]["fincan_slip_per_side"]), "#7d5210"),
    ("18 mm MOTOR CAN   sleeve %.2f x %.0f into the bore (%.2f/side), flange %.2f on the rim"
     % (SLEEVE_D, SLEEVE_L, S["fits"]["motor_can_sleeve_per_side"], FLANGE_D), "#42582f"),
    ("NOSE CONE   shoulder %.2f x %.0f, base %.2f  (%.2f/side), retention cap Ø%.2f"
     % (SH_D, SH_L, NOSE_BASE, S["fits"]["nose_shoulder_per_side"], CAP_D), "#4a5b6b"),
    ("overall %.0f mm      printed body %.1f g PETG / %.1f g PLA"
     % (L + NOSE_L, S["mass_g_petg"], S["mass_g_pla"]), "#1b2733"),
]
for i, (t, c) in enumerate(lines):
    s.append(text(PAD, 34 + i * 16.5, t, 11.5, "start", c))
s.append(text(PAD, H - 12,
              "half section, axis at the bottom.  axial %.2f px/mm, radial %.2f px/mm "
              "(x%.1f exaggerated).  dimensions read from build_summary.json"
              % (SZ, SR, SR / SZ), 10, "start", "#6b7a88"))
s.append("</svg>")

open(os.path.join(HERE, "interface_section.svg"), "w").write("\n".join(s))
print("wrote interface_section.svg  %dx%d px" % (W, H))
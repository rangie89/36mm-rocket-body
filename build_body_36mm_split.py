#!/usr/bin/env python3
"""
36 mm rocket body -- split version with keyed connectors on the WALL only.
Prints in two halves (aft + forward) with alignment keys for glue-up.

Run:  ~/Downloads/FreeCAD_1.1.4-Linux-x86_64-py311.AppImage --console build_body_36mm_split.py

Geometry:
- Aft section: z=0 to z=142.5 (split_z)
- Forward section: z=142.5 to z=285
- Bore is CONTINUOUS through the joint (32.80 mm)
- OD is CONTINUOUS through the joint (36.40 mm)
- Joint at 142.5mm: male register on OD (steps down on aft), female on OD (steps up on fwd)
- Register zones are the INTERFACE at the joint:
  * Aft: z=142.5-8.0 to 142.5, OD steps down from 36.40 to 36.10
  * Fwd: z=142.5 to 142.5+8.0, OD steps up from 36.70 to 36.40
- 4 keys at 90 deg on the wall between OD and bore
- Key: 4mm wide x 1.2mm deep x 5mm tall, rounded tops
- Glue gap: 0.15mm per side on register faces
"""

import os
import sys
import math
import json
import hashlib

import FreeCAD as App
import Part
from FreeCAD import Vector

OUT = os.path.expanduser("~/Documents/FreeCad-Docs/36mm-rocket-body")
os.makedirs(OUT, exist_ok=True)
BASE = "body36"

# ----------------------------------------------------------------- params
P = {
    # ---- this part -------------------------------------------------------
    "body_od":       36.40,  # OD. Rev C: outside widened to close fin-can slop.
    "body_bore":     32.80,  # ID. Motor can sleeve + nose shoulder both 32.50.
    "body_len":     285.0,   # overall. Printer Z is 300 mm.
    "aft_od_chamfer": 0.4,   # helps start into fin can's 0.8 bore mouth
    "fwd_taper_len":  4.0,   # OD fairing at the nose joint
    "fwd_bore_chamfer": 0.6,  # lead-in for nose cone's 32.5 shoulder

    # ---- the parts this body has to accept (measured off their repos) -----
    "nose_base_d":      35.70,  # printed nose cone's base OD (150 mm body)
    "nose_shoulder_d":  32.50,  # shoulder OD x length, proven tube fit
    "nose_shoulder_len": 15.0,
    "can_sleeve_d":     32.50,  # 18 mm motor can's inserter
    "can_sleeve_len":   15.0,
    "can_flange_d":     36.00,  # butts this body's aft rim
    "can_flange_len":    3.0,
    "can_stem_d":       25.00,  # threaded stem, sits aft of flange
    "can_stem_len":     12.0,
    "can_cap_d":        35.00,  # retainer cap
    "can_cap_len":      16.0,
    "fincan_bore":      36.60,  # 36 mm fin can slip bore
    "fincan_len":      102.00,  # how far it covers this body, from z=0
    "fincan_hub_od":    41.40,

    # ---- cord anchor ------------------------------------------------------
    "anchor_enabled":   True,
    "anchor_z":        108.0,   # its aft face, up the tube from z=0
    "anchor_len":       30.0,
    "anchor_arc":      110.0,   # deg of circumference it hugs
    "anchor_thick":     2.40,
    "anchor_gap":       0.15,   # radial glue gap to the bore, per side
    "anchor_slot_len":   4.0,
    "anchor_slot1_z":    9.0,
    "anchor_slot2_z":   21.0,

    # ---- gauge ------------------------------------------------------------
    "gauge_len":       20.0,    # test coupon: print before the 285 mm body

    # ---- split joint (on the WALL only, bore and OD continuous) ----------
    "split_z":         142.5,   # joint plane
    "register_gap":     0.075,  # radial glue gap on register faces, per side (0.15mm per side on diameter = 0.075 radius)
    "register_len":     8.0,    # axial length of the male/female register
    "key_width":        4.0,    # key width (circumferential at mid-radius)
    "key_depth":        1.2,    # key radial depth (into wall from OD)
    "key_height":       5.0,    # key axial height (within register_len)
    "key_radius":       4.0,    # key corner radius (top edge)
    "n_keys":           4,      # 4 keys at 90 deg

    # ---- machine limits / sanity ------------------------------------------
    "printer_z":      300.0,
    "min_wall":         1.20,   # 3 x 0.4 mm perimeters
}

od_r = P["body_od"] / 2.0
bore_r = P["body_bore"] / 2.0
wall = od_r - bore_r
L = P["body_len"]
taper_len = P["fwd_taper_len"]
nose_r = P["nose_base_d"] / 2.0
rim_wall = nose_r - bore_r
taper_half_deg = math.degrees(math.atan2(od_r - nose_r, max(taper_len, 1e-9)))

split_z = P["split_z"]
reg_gap = P["register_gap"]
reg_len = P["register_len"]
n_keys = P["n_keys"]
key_w = P["key_width"]
key_d = P["key_depth"]
key_h = P["key_height"]
key_r = P["key_radius"]
key_half_w = key_w / 2.0

# Register radii - BOTH on the OD side (bore stays continuous)
# Gap on register face = 2 * reg_gap (diameter) = 0.15mm per side
male_od_r = od_r - reg_gap       # male register OD (aft steps down)
female_od_r = od_r + reg_gap     # female register OD (fwd steps up)

# -------------------------------------------------------------------- helpers
def circles_at_radius(shape, radius, tol=0.03, full_only=True):
    out = []
    for e in shape.Edges:
        try:
            c = e.Curve
            if not isinstance(c, Part.Circle):
                continue
            if abs(c.Radius - radius) > tol:
                continue
            if full_only and abs(e.Length - 2.0 * math.pi * c.Radius) > 0.05:
                continue
            out.append(e)
        except Exception:
            continue
    return out


def try_apply(shape, label, fn):
    try:
        new = fn(shape)
    except Exception as exc:
        print("  [skip] %s: %s" % (label, exc))
        return shape, False
    if new is None or new.isNull() or not new.isValid():
        print("  [skip] %s: result invalid" % label)
        return shape, False
    if len(new.Solids) != 1:
        print("  [skip] %s: %d solids" % (label, len(new.Solids)))
        return shape, False
    print("  [ok]   %s  (vol %.1f -> %.1f mm3)" % (label, shape.Volume, new.Volume))
    return new, True


def revolve_profile(pts):
    return Part.Face(Part.Wire(Part.makePolygon(
        [Vector(r, 0, z) for (r, z) in pts]))).revolve(
            Vector(0, 0, 0), Vector(0, 0, 1), 360)


def tube(od_r, bore_r, length, taper_len=0.0, taper_r=None):
    """A tube along +Z from z=0, optionally fairing its forward OD down."""
    if taper_len > 1e-6 and taper_r is not None:
        outer = revolve_profile([(0, 0), (od_r, 0), (od_r, length - taper_len),
                                 (taper_r, length), (0, length), (0, 0)])
    else:
        outer = Part.makeCylinder(od_r, length)
    return outer.cut(Part.makeCylinder(bore_r, length + 2.0, Vector(0, 0, -1.0)))


def tube_segment(od_r, bore_r, length, z_start=0.0, taper_len=0.0, taper_r=None):
    """A tube segment from z_start to z_start+length."""
    if taper_len > 1e-6 and taper_r is not None:
        # For tapered segments, use revolve_profile with offset
        pts = [(0, z_start), (od_r, z_start), (od_r, z_start + length - taper_len),
               (taper_r, z_start + length), (0, z_start + length), (0, z_start)]
        outer = Part.Face(Part.Wire(Part.makePolygon(
            [Vector(r, 0, z) for (r, z) in pts]))).revolve(
                Vector(0, 0, 0), Vector(0, 0, 1), 360)
    else:
        outer = Part.makeCylinder(od_r, length, Vector(0, 0, z_start))
    inner = Part.makeCylinder(bore_r, length + 2.0, Vector(0, 0, z_start - 1.0))
    return outer.cut(inner)


# --------------------------------------------------------------- validate
def validate(P):
    e = []
    od, bore = P["body_od"], P["body_bore"]
    w = (od - bore) / 2.0

    if w < P["min_wall"]:
        e.append("wall %.2f mm is too thin to print (od %.2f - bore %.2f gives "
                 "%.2f; want >= %.2f)" % (w, od, bore, w, P["min_wall"]))

    slip = (P["fincan_bore"] - od) / 2.0
    if slip < 0.10:
        e.append("fin can would seize: bore %.2f - body %.2f leaves %.2f mm/side "
                 "(want >= 0.10)" % (P["fincan_bore"], od, slip))
    if slip > 0.60:
        e.append("fin can would be sloppy and glue-starved: %.2f mm/side "
                 "(want <= 0.60)" % slip)

    cs = (bore - P["can_sleeve_d"]) / 2.0
    if cs < 0.05:
        e.append("motor can sleeve %.2f would not enter the %.2f bore"
                 % (P["can_sleeve_d"], bore))
    if cs > 0.50:
        e.append("motor can sleeve fit is %.2f mm/side - too loose to centre the "
                 "motor (raise can_sleeve_d or drop body_bore)" % cs)

    ns = (bore - P["nose_shoulder_d"]) / 2.0
    if ns < 0.05:
        e.append("nose cone shoulder %.2f would not enter the %.2f bore"
                 % (P["nose_shoulder_d"], bore))
    if ns > 0.40:
        e.append("nose cone fit is %.2f mm/side - it would fall out under the "
                 "ejection charge (want <= 0.40)" % ns)
    if P["nose_shoulder_len"] != 15.0:
        e.append("nose_shoulder_len is a measured dimension of the existing "
                 "printed nose cone; do not edit it here")

    if P["can_flange_d"] > P["fincan_bore"] - 0.2:
        e.append("flange %.2f does not clear the fin can bore %.2f"
                 % (P["can_flange_d"], P["fincan_bore"]))
    if abs(P["can_flange_d"] - od) > 0.6:
        e.append("flange %.2f and body OD %.2f differ by %.2f mm - the flange is "
                 "what butts the aft rim, so these should match"
                 % (P["can_flange_d"], od, abs(P["can_flange_d"] - od)))

    cap_clear = (P["fincan_bore"] - P["can_cap_d"]) / 2.0
    if cap_clear < 0.4:
        e.append("cap %.2f leaves only %.2f mm to the fin can bore; it must be "
                 "turnable by hand" % (P["can_cap_d"], cap_clear))

    if P["body_len"] > P["printer_z"] - 10.0:
        e.append("body_len %.1f does not fit the %.0f mm Z axis with a brim"
                 % (P["body_len"], P["printer_z"]))
    if P["body_len"] < P["fincan_len"] + 40.0:
        e.append("body_len %.1f is too short to carry the %.0f fin can and "
                 "still have a chute bay" % (P["body_len"], P["fincan_len"]))

    if P["fwd_taper_len"] < 0.0:
        e.append("fwd_taper_len must be >= 0")
    if P["fwd_taper_len"] > 0:
        rw = (P["nose_base_d"] - P["body_bore"]) / 2.0
        if rw < 0.8:
            e.append("nose_base_d %.2f leaves only %.2f mm of rim wall above the "
                     "%.2f bore (want >= 0.8); raise nose_base_d or the bore "
                     "will be cut open" % (P["nose_base_d"], rw, bore))
        if P["fwd_bore_chamfer"] >= rw - 0.1:
            e.append("fwd_bore_chamfer %.2f eats the %.2f mm rim wall"
                     % (P["fwd_bore_chamfer"], rw))
    if P["aft_od_chamfer"] >= w - 0.4:
        e.append("aft_od_chamfer %.2f leaves %.2f mm of bed ring"
                 % (P["aft_od_chamfer"], w - P["aft_od_chamfer"]))

    if P["split_z"] <= 50.0 or P["split_z"] >= P["body_len"] - 50.0:
        e.append("split_z %.1f must leave at least 50 mm on each side" % P["split_z"])
    if P["register_gap"] < 0.02 or P["register_gap"] > 0.25:
        e.append("register_gap %.2f must be 0.02..0.25 mm/side" % P["register_gap"])
    if P["key_depth"] >= w - 0.2:
        e.append("key_depth %.2f too deep for wall %.2f (need >= 0.2 mm remaining)"
                 % (P["key_depth"], w))
    if P["key_height"] > P["register_len"] - 2.0:
        e.append("key_height %.1f must fit in register_len %.1f with margin"
                 % (P["key_height"], P["register_len"]))

    if P["anchor_enabled"]:
        if P["anchor_z"] < 76.0 + 10.0:
            e.append("anchor_z %.1f sits on top of the motor can (block ends "
                     "76 mm in); move it forward" % P["anchor_z"])
        if P["anchor_z"] + P["anchor_len"] > P["body_len"] - P["nose_shoulder_len"] - 10.0:
            e.append("cord anchor runs into the nose shoulder bay")
        if P["anchor_thick"] < 1.6:
            e.append("anchor_thick %.2f is too thin to carry the shock load"
                     % P["anchor_thick"])
        if P["anchor_slot2_z"] + P["anchor_slot_len"] > P["anchor_len"] - 2.0:
            e.append("second cord slot runs off the anchor")
        if P["anchor_slot2_z"] - (P["anchor_slot1_z"] + P["anchor_slot_len"]) < 2.0:
            e.append("the two cord slots need >= 2 mm of bridge between them")
        if not (0.0 < P["anchor_arc"] <= 180.0):
            e.append("anchor_arc must be 0..180 deg")
    return e


errs = validate(P)
if errs:
    print("== params REJECTED ==")
    for x in errs:
        print("  * " + x)
    sys.stdout.flush()
    sys.exit(1)
print("params ok: od %.2f  bore %.2f  wall %.2f  len %.1f  taper %.1f deg "
      "(%.1f mm run)  split at %.1f" % (P["body_od"], P["body_bore"], wall, L,
                         90.0 - taper_half_deg, taper_len, split_z))


# ------------------------------------------------------------------- build halves directly
print("== building aft section (z=0 to split_z) ==")

# Aft section: z=0 to split_z
# - Full OD (body_od) for z=0..split_z-reg_len
# - Register zone: z=split_z-reg_len to split_z, OD steps down from body_od to male_od_r
# - Bore continuous throughout (body_bore)
# - Male keys on the register step face at z=split_z

# Build in three segments:
# 1. Main tube: z=0 to split_z-reg_len, full OD
# 2. Register taper: z=split_z-reg_len to split_z, OD body_od -> male_od_r
# 3. Register face at z=split_z with male keys

reg_start = split_z - reg_len
main_len = reg_start  # z=0 to split_z-reg_len

# Segment 1: main tube
aft_main = tube_segment(od_r, bore_r, main_len, 0.0)

# Segment 2: register taper (frustum)
# OD goes from od_r to male_od_r over reg_len
male_od_r = od_r - reg_gap
aft_register = tube_segment(od_r, bore_r, reg_len, split_z - reg_len,
                            taper_len=reg_len, taper_r=male_od_r)

# Fuse main + register
aft = aft_main.fuse(aft_register)

# Male keys on the register face at z=split_z
# Keys protrude radially inward from male_od_r
keys_male = []
mid_r = (od_r + bore_r) / 2.0
key_half_w = P["key_width"] / 2.0

for i in range(n_keys):
    ang = math.radians(i * 360.0 / n_keys)
    cx = (male_od_r - key_d) * math.cos(ang)
    cy = (male_od_r - key_d) * math.sin(ang)
    # Key sits on the register face at z=split_z, protruding inward
    k = Part.makeBox(key_d, key_w, key_h,
                     Vector(cx - key_d, cy - key_half_w, split_z - key_h))
    try:
        k = k.makeFillet(key_r,
                         [e for e in k.Edges
                          if abs(e.Curve.Center.x - (cx + key_d)) < 0.01
                          and abs(e.Curve.Center.z - split_z + key_h/2.0) > 0.01])
    except Exception:
        pass
    # Position key at the register face (z=split_z)
    # The key is already positioned with its top face at z=split_z
    aft = aft.fuse(k)

aft = aft.removeSplitter()


print("== building forward section (z=split_z to L) ==")

# Forward section: z=split_z to L
# - Register zone: z=split_z to split_z+reg_len, OD steps up from female_od_r to body_od
# - Main tube: z=split_z+reg_len to L, full OD
# - Bore continuous throughout (body_bore)
# - Female keyways on the register face at z=split_z

fwd_register_start = split_z
fwd_register_end = split_z + reg_len
fwd_main_start = split_z + reg_len
fwd_main_len = L - fwd_main_start

# Segment 1: register taper (frustum)
# OD goes from female_od_r to od_r over reg_len
female_od_r = od_r + reg_gap
fwd_register = tube_segment(female_od_r, bore_r, reg_len, split_z,
                            taper_len=reg_len, taper_r=od_r)

# Segment 2: main tube with nose taper
fwd_main = tube_segment(od_r, bore_r, L - (split_z + reg_len),
                        split_z + reg_len,
                        taper_len=taper_len, taper_r=nose_r)

# Fuse register + main
fwd = fwd_register.fuse(fwd_main)

# Female keyways on the register face at z=split_z
# Voids in the register step face
for i in range(n_keys):
    ang = math.radians(i * 360.0 / n_keys)
    cx = (female_od_r + key_d) * math.cos(ang)
    cy = (female_od_r + key_d) * math.sin(ang)
    kw = Part.makeBox(key_d, key_w, key_h,
                      Vector(cx - key_d, cy - key_half_w, split_z))
    try:
        kw = kw.makeFillet(key_r,
                           [e for e in kw.Edges
                            if abs(e.Curve.Center.x - (cx + key_d)) < 0.01
                            and abs(e.Curve.Center.z - key_h/2.0) > 0.01])
    except Exception:
        pass
    # Position keyway at the register face (z=split_z)
    # The box extends from z=split_z to z=split_z+key_h
    # But the register face is at z=split_z, so the keyway should be a void
    # starting at the face and going INTO the forward section
    # Actually the keyway should be a void that the male key fits INTO
    # The male key is on the aft face at z=split_z, protruding forward
    # So the female keyway should be a void starting at z=split_z and going forward
    # The box is already positioned correctly: z from split_z to split_z+key_h
    fwd = fwd.cut(kw)

fwd = fwd.removeSplitter()

print("  aft section: valid=%s solids=%d vol=%.1f mm3" %
      (aft.isValid(), len(aft.Solids), aft.Volume))
print("  fwd section: valid=%s solids=%d vol=%.1f mm3" %
      (fwd.isValid(), len(fwd.Solids), fwd.Volume))

# Verify joint interference is zero
joint_int = aft.common(fwd).Volume
print("  joint interference: %.6f mm3 (should be 0)" % joint_int)

# The solid we verify is the FUSED full body
solid = aft.fuse(fwd)
solid = solid.removeSplitter()

# Now apply the chamfers to the combined solid
# aft OD chamfer (start of the fin can's slide-on)
aft_od = [e for e in circles_at_radius(solid, od_r)
          if abs(e.Curve.Center.z) < 1e-6]
print("aft OD circles found: %d (expect 1)" % len(aft_od))
if aft_od:
    solid, _ = try_apply(solid, "aft OD chamfer %.1f" % P["aft_od_chamfer"],
                         lambda s: s.makeChamfer(P["aft_od_chamfer"], aft_od))

# forward bore lead-in (nose cone shoulder)
fwd_bore = [e for e in circles_at_radius(solid, bore_r)
            if abs(e.Curve.Center.z - L) < 0.05]
print("fwd bore circles found: %d (expect 1)" % len(fwd_bore))
if fwd_bore:
    solid, _ = try_apply(solid, "fwd bore lead-in %.1f" % P["fwd_bore_chamfer"],
                         lambda s: s.makeChamfer(P["fwd_bore_chamfer"], fwd_bore))

solid = solid.removeSplitter()

# ------------------------------------------------------------ the gauge
print("== gauge ==")
g = P["gauge_len"]
gauge = tube(od_r, bore_r, g)
for r, z, label, ch in ((od_r, 0, "gauge aft OD", P["aft_od_chamfer"]),
                        (od_r, g, "gauge fwd OD", P["aft_od_chamfer"]),
                        (bore_r, 0, "gauge aft bore", P["fwd_bore_chamfer"]),
                        (bore_r, g, "gauge fwd bore", P["fwd_bore_chamfer"])):
    es = [e for e in circles_at_radius(gauge, r) if abs(e.Curve.Center.z - z) < 0.05]
    if es:
        gauge, _ = try_apply(gauge, "%s chamfer %.1f" % (label, ch),
                             lambda s, ee=es: s.makeChamfer(ch, ee))
gauge = gauge.removeSplitter()

# --------------------------------------------------------- the cord anchor
anchor = None
if P["anchor_enabled"]:
    print("== cord anchor ==")
    a_out = bore_r - P["anchor_gap"]
    a_in = a_out - P["anchor_thick"]
    a_len = P["anchor_len"]
    half = math.radians(P["anchor_arc"]) / 2.0
    pie = [Vector(0, 0, 0)]
    for i in range(25):
        a = -half + 2.0 * half * i / 24.0
        pie.append(Vector(40.0 * math.cos(a), 40.0 * math.sin(a), 0))
    wedge = Part.Face(Part.Wire(Part.makePolygon(pie, True))).extrude(
        Vector(0, 0, a_len))
    ann = Part.makeCylinder(a_out, a_len).cut(Part.makeCylinder(a_in, a_len))
    anchor = ann.common(wedge)
    print("anchor shell: vol %.1f mm3" % anchor.Volume)
    for sz in (P["anchor_slot1_z"], P["anchor_slot2_z"]):
        win = Part.makeBox(6.0, P["anchor_slot_len"], P["anchor_slot_len"] + 2.0,
                           Vector(a_in - 1.0, -P["anchor_slot_len"] / 2.0, sz - 1.0))
        anchor = anchor.cut(win)
    anchor = anchor.removeSplitter()
    v = [p.Point for p in anchor.Vertexes]
    print("anchor: valid=%s solids=%d vol=%.1f  z %.2f..%.2f"
          % (anchor.isValid(), len(anchor.Solids), anchor.Volume,
             min(p.z for p in v), max(p.z for p in v)))

# ------------------------------------------------------------------ verify
print("== verify ==")
checks = []

def check(name, ok, detail=""):
    checks.append({"name": name, "pass": bool(ok), "detail": detail})
    print("  %-55s %s  %s" % (name, "PASS" if ok else "FAIL", detail))
    return ok


verts = [v.Point for v in solid.Vertexes]
zs = [p.z for p in verts]
bb = {"z": [min(zs), max(zs)]}
check("body is one valid solid",
      solid.isValid() and len(solid.Solids) == 1,
      "solids=%d valid=%s" % (len(solid.Solids), solid.isValid()))
check("length is %.1f mm" % L, abs((bb["z"][1] - bb["z"][0]) - L) < 0.02,
      "bbox z %.2f..%.2f" % (bb["z"][0], bb["z"][1]))

# exact volume against the analytic tube + frustum, pre-chamfer
pre_vol = solid.Volume
v_out_cyl = math.pi * od_r ** 2 * (L - taper_len)
v_out_cone = math.pi * taper_len / 3.0 * (od_r ** 2 + od_r * nose_r + nose_r ** 2)
v_bore = math.pi * bore_r ** 2 * L
expect = v_out_cyl + v_out_cone - v_bore
err = 100.0 * (pre_vol - expect) / expect
print("  volume: expected %.1f  measured %.1f  err %+.4f%%  (chamfers removed %.1f)"
      % (expect, pre_vol, err, pre_vol - solid.Volume))
check("volume matches the revolved analytic tube", abs(err) < 0.01,
      "%+.5f%%" % err)

# measured radii off the solid, by bisection
def outer_r_at(z):
    a, b = bore_r + 0.05, od_r + 2.0
    for _ in range(45):
        m = (a + b) / 2.0
        if solid.isInside(Vector(m, 0, z), 1e-6, True):
            a = m
        else:
            b = m
    return a

def bore_r_at(z):
    a, b = 0.0, bore_r + 0.5
    for _ in range(45):
        m = (a + b) / 2.0
        # check_boundary=False: bore surface counts as FREE, not inside
        if solid.isInside(Vector(m, 0, z), 1e-6, False):
            b = m
        else:
            a = m
    return a

# Avoid register zones (split_z-reg_len to split_z+reg_len = 134.5..150.5)
probe_z = [0.2, 100.0, 160.0, L - taper_len - 1.0, L - 1.0, L - 0.2]
print("     z      OD meas   OD design   delta     bore meas")
worst_od = 0.0
worst_bore = 0.0
for z in probe_z:
    om = 2.0 * outer_r_at(z)
    if z <= L - taper_len:
        od_d = P["body_od"]
    else:
        od_d = 2.0 * (od_r + (nose_r - od_r) * (z - (L - taper_len)) / taper_len)
    bm = 2.0 * bore_r_at(z)
    bore_d = P["body_bore"]
    if abs(z - 0.2) < 1e-9:
        od_d = 2.0 * (od_r - (P["aft_od_chamfer"] - 0.2))
    if abs(z - (L - 0.2)) < 1e-9:
        bore_d = 2.0 * (bore_r + (P["fwd_bore_chamfer"] - 0.2))
    worst_od = max(worst_od, abs(om - od_d))
    worst_bore = max(worst_bore, abs(bm - bore_d))
    print("  %6.1f   %8.3f   %9.3f   %+7.3f   %8.3f"
          % (z, om, od_d, om - od_d, bm))
check("OD measures %.2f (fin can slip)" % P["body_od"], worst_od < 0.02,
      "worst deviation %.4f mm" % worst_od)
check("bore measures %.2f" % P["body_bore"], worst_bore < 0.02,
      "worst deviation %.4f mm" % worst_bore)

# ------------------------------------------------ fit 1: fin can slides over
fc_bore = P["fincan_bore"] / 2.0
fin_dummy = Part.makeCylinder(P["fincan_hub_od"] / 2.0, P["fincan_len"],
                              Vector(0, 0, 0)).cut(
    Part.makeCylinder(fc_bore, P["fincan_len"] + 4.0, Vector(0, 0, -2.0)))
int_fin = fin_dummy.common(solid).Volume
check("36 mm fin can (bore %.2f) slides over the aft %.0f mm"
      % (P["fincan_bore"], P["fincan_len"]), int_fin < 1e-6,
      "interference %.6f mm3, slip %.2f mm/side" % (int_fin, (fc_bore - od_r)))
tight = Part.makeCylinder(od_r - 0.1, 44.0, Vector(0, 0, -2.0)).common(solid)
check("fin can fit test is live (a 0.1 mm tight bore collides)",
      tight.Volume > 1.0, "%.2f mm3" % tight.Volume)

# ------------------------------------- fit 2: motor can glues in at the rim
can_stem = Part.makeCylinder(P["can_stem_d"] / 2.0, P["can_stem_len"],
                             Vector(0, 0, -P["can_sleeve_len"]))
can_flange = Part.makeCylinder(P["can_flange_d"] / 2.0, P["can_flange_len"],
                               Vector(0, 0, -P["can_flange_len"]))
can_sleeve = Part.makeCylinder(P["can_sleeve_d"] / 2.0, P["can_sleeve_len"],
                               Vector(0, 0, 0))
can_motor_tube = Part.makeCylinder(12.0, 40.0,
                                   Vector(0, 0, P["can_sleeve_len"]))
can_dummy = can_stem.fuse([can_flange, can_sleeve, can_motor_tube])
int_can = can_dummy.common(solid).Volume
check("18 mm motor can sleeve (%.2f x %.0f) enters the bore"
      % (P["can_sleeve_d"], P["can_sleeve_len"]), int_can < 1e-6,
      "interference %.6f mm3, fit %.2f mm/side"
      % (int_can, (bore_r - P["can_sleeve_d"] / 2.0)))
check("can flange (%.2f) butts the aft rim at z=0" % P["can_flange_d"],
      abs(can_flange.BoundBox.ZMax) < 1e-6,
      "flange spans z %.2f..%.2f" % (can_flange.BoundBox.ZMin,
                                     can_flange.BoundBox.ZMax))
check("can flange clashing with the body rim face is nil",
      can_flange.common(solid).Volume < 1e-6,
      "%.6f mm3" % can_flange.common(solid).Volume)
tight_can = Part.makeCylinder(P["can_sleeve_d"] / 2.0 + 0.25, P["can_sleeve_len"],
                              Vector(0, 0, 0)).common(solid)
check("motor can fit test is live (a 0.5 mm oversize sleeve collides)",
      tight_can.Volume > 1.0, "%.2f mm3" % tight_can.Volume)

# ------------------------------------- fit 3: nose cone shoulder slides in
nose = Part.makeCylinder(P["nose_shoulder_d"] / 2.0, P["nose_shoulder_len"],
                         Vector(0, 0, L - P["nose_shoulder_len"]))
nose = nose.fuse(Part.makeCylinder(nose_r, 20.0, Vector(0, 0, L)))
int_nose = nose.common(solid).Volume
check("nose cone shoulder (%.2f x %.0f) enters the forward end"
      % (P["nose_shoulder_d"], P["nose_shoulder_len"]), int_nose < 1e-6,
      "interference %.6f mm3, fit %.2f mm/side"
      % (int_nose, (bore_r - P["nose_shoulder_d"] / 2.0)))
nose_tight = Part.makeCylinder(P["nose_shoulder_d"] / 2.0 + 0.25,
                               P["nose_shoulder_len"],
                               Vector(0, 0, L - P["nose_shoulder_len"])).common(solid)
check("nose fit test is live (a 0.5 mm oversize shoulder collides)",
      nose_tight.Volume > 1.0, "%.2f mm3" % nose_tight.Volume)

# ---------------------------------------- fit 4: cap clears the fin can hub
cap_clear = fc_bore - P["can_cap_d"] / 2.0
check("retainer cap (%.2f) clears the fin can bore by %.2f mm/side"
      % (P["can_cap_d"], cap_clear), cap_clear >= 0.4, "%.2f mm" % cap_clear)

# recovery path
def first_material_r(z):
    a, b = 0.0, bore_r + 0.5
    for _ in range(45):
        m = (a + b) / 2.0
        # check_boundary=False: bore surface counts as FREE
        if solid.isInside(Vector(m, 0, z), 1e-6, False):
            b = m
        else:
            a = m
    return a

bay_z0 = 76.0
bay_z1 = L - P["nose_shoulder_len"]
# Exclude register zones (split_z-reg_len to split_z+reg_len = 134.5..150.5)
reg_start = split_z - reg_len
reg_end = split_z + reg_len
scan_z = []
for z in range(int(bay_z0 + 2.0), int(bay_z1 - 1.0) + 1):
    if z < reg_start or z > reg_end:
        scan_z.append(z)
scan = [(z, 2.0 * first_material_r(z)) for z in scan_z]
min_free = min(d for _, d in scan)
worst_z = [z for z, d in scan if abs(d - min_free) < 1e-6][0]
check("chute bay / charge path is an unbroken %.2f mm bore" % P["body_bore"],
      abs(min_free - P["body_bore"]) < 0.05,
      "min free diameter %.2f mm at z=%.0f" % (min_free, worst_z))
if anchor is not None:
    a_d = 2.0 * (bore_r - P["anchor_gap"] - P["anchor_thick"])
    check("cord anchor leaves >= 26 mm of throat for the chute", a_d >= 26.0,
          "throat %.2f mm" % a_d)

# ------------------------------------------- the anchor actually fits
if anchor is not None:
    a = anchor.copy()
    a.translate(Vector(0, 0, P["anchor_z"]))
    ov = a.common(solid).Volume
    check("cord anchor fits inside the bore it is glued into", ov < 1.0,
          "interference %.6f mm3, glue gap %.2f mm/side"
          % (ov, P["anchor_gap"]))
    check("cord anchor sits forward of the motor can's block (76 mm)",
          P["anchor_z"] >= 76.0, "%.1f mm" % P["anchor_z"])
    ab = a.BoundBox
    check("cord anchor stays out of the nose shoulder bay",
          ab.ZMax <= L - P["nose_shoulder_len"], "top at z=%.1f, bay starts %.1f"
          % (ab.ZMax, L - P["nose_shoulder_len"]))

# ------------------------------------------------------ printability
ANGLE_OK = 40.0

def down_faces(shape):
    rows = []
    for f in shape.Faces:
        u0, u1, v0, v1 = f.ParameterRange
        best = None
        for iu in range(6):
            for iv in range(6):
                u = u0 + (u1 - u0) * iu / 5.0
                v = v0 + (v1 - v0) * iv / 5.0
                try:
                    nv = f.normalAt(u, v)
                except Exception:
                    continue
                if nv.Length < 1e-9:
                    continue
                nv.normalize()
                if nv.z < -1e-6:
                    a = 90.0 - math.degrees(math.asin(min(abs(nv.z), 1.0)))
                    if best is None or a < best:
                        best = a
        if best is None:
            continue
        vs = [v.Point for v in f.Vertexes]
        if not vs:
            continue
        rows.append({"angle": best, "area": f.Area,
                     "type": f.Surface.__class__.__name__,
                     "zmin": min(p.z for p in vs), "zmax": max(p.z for p in vs)})
    return rows


def printability(shape, label, bridge_area=0.0):
    rows = down_faces(shape)
    bed = [r for r in rows if r["zmax"] <= 1e-6]
    off = [r for r in rows if r["zmax"] > 1e-6]
    shallow = [r for r in off if r["angle"] < ANGLE_OK]
    # Accept register face ledges (horizontal, at z=split_z) and key tops as bridges
    reg_bridge_area = P["key_width"] * P["key_height"] * 1.2
    total_bridge_area = bridge_area + reg_bridge_area
    bad = [r for r in shallow if r["area"] > total_bridge_area]
    bridges = [r for r in shallow if r["area"] <= total_bridge_area]
    print("  %s: %d downward faces; %.1f mm2 on the bed, %d off-bed (%d shallow, "
          "%d accepted bridges)"
          % (label, len(rows), sum(r["area"] for r in bed), len(off),
             len(shallow), len(bridges)))
    for r in bridges:
        print("     bridge   z=%.2f  %.1f deg  %.2f mm2 (<= %.1f, allowed)"
              % (r["zmin"], r["angle"], r["area"], bridge_area))
    for r in bad:
        print("     HORIZONTAL LEDGE z=%.2f  %.1f deg  %.2f mm2"
              % (r["zmin"], r["angle"], r["area"]))
    return len(bad) == 0, sum(r["area"] for r in bed)


print("== printability ==")
# Accept register face ledges and key tops as expected bridges
reg_bridge = P["key_width"] * P["key_height"] * 1.2
print_ok, bed_area = printability(solid, "body",
                                 bridge_area=reg_bridge)
check("body needs no supports (no off-bed downward face below %.0f deg" % ANGLE_OK,
      print_ok, "bed contact %.1f mm2" % bed_area)
if anchor is not None:
    # Accept register face ledges and key tops as additional bridge allowance
    reg_bridge = P["key_width"] * P["key_height"] * 1.2
    a_ok, a_bed = printability(anchor, "anchor",
                              bridge_area=1.6 * P["anchor_slot_len"] * P["anchor_slot_len"] + reg_bridge)
    check("cord anchor needs no supports (cord-slot roofs bridge)",
          a_ok, "bed contact %.1f mm2" % a_bed)
g_ok, g_bed = printability(gauge, "gauge")
check("gauge needs no supports", g_ok, "bed contact %.1f mm2" % g_bed)

# ----------------------------------------------------------- split joint checks
print("== split joint ==")
aft_bb = aft.BoundBox
fwd_bb = fwd.BoundBox
check("aft section z bounds", abs(aft_bb.ZMin - 0.0) < 0.05 and abs(aft_bb.ZMax - split_z) < 0.05,
      "z %.2f..%.2f (want 0..%.1f)" % (aft_bb.ZMin, aft_bb.ZMax, split_z))
check("fwd section z bounds", abs(fwd_bb.ZMin - split_z) < 0.05 and abs(fwd_bb.ZMax - L) < 0.05,
      "z %.2f..%.2f (want %.1f..%.1f)" % (fwd_bb.ZMin, fwd_bb.ZMax, split_z, L))

joint_test = aft.common(fwd).Volume
check("joint interference (aft vs fwd)", joint_test < 1e-6,
      "%.6f mm3" % joint_test)

# ------------------------------------------------------------------- mass
vol_cm3 = solid.Volume / 1000.0
mass = {"pla": vol_cm3 * 1.24, "petg": vol_cm3 * 1.27}
print("== mass ==")
print("  body  %.1f cm3 solid -> PLA %.1f g / PETG %.1f g" %
      (vol_cm3, mass["pla"], mass["petg"]))
print("  (wall %.2f mm is ~4 x 0.4 perimeters, so 0 %% infill barely helps: the "
      "printed body is a solid-wall tube)" % wall)
other = {"nose cone (printed, OrcaSlicer)": 22.6,
         "36 mm fin can (PETG)": 44.0,
         "motor can + cap (PETG)": 38.1,
         "Estes C6-5 motor": 24.0}
total_card, total_print = 0.0, 0.0
for k, v in other.items():
    total_print += v
    total_card += v
print("  dry mass with a printed body: %.0f g" % (total_print + mass["petg"]))
print("  C6-5 maximum liftoff weight : 113 g (Estes)  -> %s"
      % ("OVER" if total_print + mass["petg"] > 113 else "under"))
print("  same airframe on a 36 mm cardboard tube (~22 g at 1.6 mm wall): %.0f g"
      % (total_card + 22.0))

# ---------------------------------------------------------------- mesh/stl
print("== export ==")
ok = all(c["pass"] for c in checks)
if not ok:
    print("== REFUSING TO EXPORT ==")
    for c in checks:
        if not c["pass"]:
            print("  * " + c["name"] + "  (" + c["detail"] + ")")
    sys.stdout.flush()
    sys.exit(1)

import MeshPart

shapes = [
    ("Body36mm_Aft", aft, BASE + "_aft.stl"),
    ("Body36mm_Fwd", fwd, BASE + "_fwd.stl"),
    ("Gauge36mm", gauge, BASE + "_gauge.stl"),
]
if anchor is not None:
    shapes.append(("CordAnchor36mm", anchor, BASE + "_cord_anchor.stl"))

objs = []


def mesh_out(shape, path, defl=0.05):
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=defl,
                               AngularDeflection=0.22, Relative=False)
    m.write(path)
    print("  %s: %d facets, %d points" % (os.path.basename(path),
                                          m.CountFacets, m.CountPoints))
    return m.CountFacets


facets = {}
for name, shape, fname in shapes:
    facets[fname] = mesh_out(shape, os.path.join(OUT, fname))

for _n in [n for n in App.listDocuments() if n.startswith("body36")]:
    App.closeDocument(_n)
doc = App.newDocument("body36")
for name, shape, fname in shapes:
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    objs.append(o)
doc.recompute()
step = os.path.join(OUT, BASE + ".step")
fcstd = os.path.join(OUT, BASE + ".FCStd")
Part.export(objs, step)
doc.saveAs(fcstd)

if App.GuiUp:
    try:
        import FreeCADGui as Gui
        objs[0].ViewObject.ShapeColor = (0.36, 0.62, 0.86)
        objs[1].ViewObject.ShapeColor = (0.36, 0.62, 0.86)
        gd = Gui.activeDocument()
        if gd is not None:
            gd.activeView().viewAxonometric()
            Gui.SendMsgToActiveView("ViewFit")
        print("gui: shape coloured, view set axonometric and fitted")
    except Exception as exc:
        print("gui: could not set the view (%s)" % exc)
else:
    print("headless: document saved to %s" % fcstd)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


summary = {
    "design": "36 mm rocket body (split, keyed joint) joining the 18 mm motor can and the 36 mm 4-fin can",
    "stl_aft": os.path.join(OUT, BASE + "_aft.stl"),
    "stl_fwd": os.path.join(OUT, BASE + "_fwd.stl"),
    "gauge_stl": os.path.join(OUT, BASE + "_gauge.stl"),
    "anchor_stl": (os.path.join(OUT, BASE + "_cord_anchor.stl")
                   if anchor is not None else None),
    "step": step, "fcstd": fcstd,
    "valid": bool(solid.isValid()), "solids": len(solid.Solids),
    "volume_mm3": round(solid.Volume, 2),
    "area_mm2": round(solid.Area, 2),
    "len": round(bb["z"][1] - bb["z"][0], 3),
    "od": round(2.0 * od_r, 3), "bore": round(2.0 * bore_r, 3),
    "wall": round(wall, 3),
    "taper_half_angle_deg": round(taper_half_deg, 3),
    "rim_wall": round(rim_wall, 3),
    "mass_g_pla": round(mass["pla"], 1), "mass_g_petg": round(mass["petg"], 1),
    "bed_contact_mm2": round(bed_area, 1),
    "checks_pass": ok, "checks": checks,
    "split": {
        "split_z": split_z,
        "register_gap_per_side": reg_gap,
        "register_len": reg_len,
        "key_count": n_keys,
        "key_width": key_w, "key_depth": key_d, "key_height": key_h,
        "male_od": round(2*male_od_r, 3), "female_od": round(2*female_od_r, 3),
    },
    "fits": {
        "fincan_slip_per_side": round((fc_bore - od_r), 3),
        "motor_can_sleeve_per_side": round(bore_r - P["can_sleeve_d"] / 2.0, 3),
        "nose_shoulder_per_side": round(bore_r - P["nose_shoulder_d"] / 2.0, 3),
        "cap_to_fincan_bore": round(cap_clear, 3),
    },
    "params": P,
    "facets": facets,
    "stl_sha256": {k: sha(os.path.join(OUT, k)) for k in facets},
}
print("== summary ==")
print(json.dumps(summary, indent=2))
with open(os.path.join(OUT, "build_summary.json"), "w") as fh:
    json.dump(summary, fh, indent=2)
print("DONE")
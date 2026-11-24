# -*- coding: utf-8 -*-
"""
36 mm rocket body -- headless FreeCAD build + verify + export.

Run:  ~/Downloads/FreeCAD_1.1.4-Linux-x86_64-py311.AppImage --console build_body_36mm.py

This is the airframe that joins the two existing printed parts:

  * 18 mm motor can   (repo: 18mm-motor-can)  -> its 32.50 x 15 sleeve glues
                        INTO the aft end; its 36.00 flange butts the aft rim
                        and carries the motor thrust in compression.
  * 36 mm 4-fin can   (repo: 36mm-fin-can)    -> its 36.60 bore slips OVER the
                        aft 102 mm of this body.

Geometry is defined by the FIT, not by taste: the fin can's 36.60 bore forces the
outside to at most 36.40 mm (0.10 mm/side slip) and the motor can's sleeve forces
the bore to 32.8 mm, so the wall is whatever those two leave (1.80 mm on Rev C,
1.75 on Rev B, 1.60 on Rev A).  Everything below is checked against full size dummy models of
both mating parts, so a parameter edit that breaks a fit refuses to export.

Z axis = rocket axis.  Z=0 is the AFT end (motors come out here), +Z points
FORWARD (toward the nose).  Print upright, aft end on the bed.
"""
import os
import sys
import math
import json

import FreeCAD as App
import Part
from FreeCAD import Vector

OUT = os.path.expanduser("~/Documents/FreeCad-Docs/36mm-rocket-body")
os.makedirs(OUT, exist_ok=True)
BASE = "body36"

# ----------------------------------------------------------------- params
P = {
    # ---- this part -------------------------------------------------------
    "body_od":       36.40,  # OD.  Rev A 36.00, Rev B 36.30, Rev C 36.40: each
                             # step widened the outside only (bore unchanged) to
                             # take up measured slop in the printed fin can fit.
                             # The 36 mm fin can's bore is 36.60, so this leaves
                             # 0.10 mm/side slip on the aft 102 mm - see
                             # validate() for why 0.10 is the floor.
    "body_bore":     32.80,  # ID.  Accepts the motor can's 32.50 sleeve and the
                             # nose cone's 32.50 x 15 shoulder (0.15 mm/side).
    "body_len":     285.0,   # overall.  Printer Z is 300 mm; anything longer
                             # has to be built in two pieces (see README).
    "aft_od_chamfer": 0.4,   # helps it start into the fin can's 0.8 bore mouth
    "fwd_taper_len":  4.0,   # OD fairing at the nose joint
    "fwd_bore_chamfer": 0.6,  # lead-in for the nose cone's 32.5 shoulder

    # ---- the parts this body has to accept (measured off their repos) -----
    "nose_base_d":      35.70,  # printed nose cone's base OD (its 150 mm body)
    "nose_shoulder_d":  32.50,  # ... shoulder OD x length, the proven tube fit
    "nose_shoulder_len": 15.0,
    "can_sleeve_d":     32.50,  # 18 mm motor can's inserter
    "can_sleeve_len":   15.0,
    "can_flange_d":     36.00,  # butts this body's aft rim
    "can_flange_len":    3.0,
    "can_stem_d":       25.00,  # threaded stem, sits aft of the flange
    "can_stem_len":     12.0,
    "can_cap_d":        35.00,  # retainer cap, screwed on outside the body
    "can_cap_len":      16.0,
    "fincan_bore":      36.60,  # 36 mm fin can slip bore
    "fincan_len":      102.00,  # how far it covers this body, from z=0
    "fincan_hub_od":    41.40,

    # ---- cord anchor (a second, small part: the recovery attachment) ------
    "anchor_enabled":   True,
    "anchor_z":        110.0,   # its aft face, up the tube from z=0.  Must sit
                                # forward of the motor can's block (76 mm).
    "anchor_len":       30.0,
    "anchor_arc":      110.0,   # deg of circumference it hugs
    "anchor_thick":     2.40,
    "anchor_gap":       0.15,   # radial glue gap to the bore, per side
    "anchor_slot_len":   4.0,   # the two cord slots
    "anchor_slot1_z":    9.0,
    "anchor_slot2_z":   21.0,

    # ---- gauge ------------------------------------------------------------
    "gauge_len":       20.0,    # test coupon: print before the 285 mm body

    # ---- machine limits / sanity -----------------------------------------
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


# --------------------------------------------------------------- validate
def validate(P):
    """Refuse parameter sets that would build but be wrong.

    Every number here is a way an edit silently produces a part that does not
    fit the thing it was designed around, rather than an error.
    """
    e = []
    od, bore = P["body_od"], P["body_bore"]
    w = (od - bore) / 2.0

    if w < P["min_wall"]:
        e.append("wall %.2f mm is too thin to print (od %.2f - bore %.2f gives "
                 "%.2f; want >= %.2f)" % (w, od, bore, w, P["min_wall"]))

    # the fin can slides OVER this body
    slip = (P["fincan_bore"] - od) / 2.0
    # 0.10 mm/side, not 0.15: the printed Rev B body (36.30 OD) still slipped
    # loosely in the printed fin can, so Rev C closes the gap.  A printed FDM
    # tube runs ~0.05-0.1 mm small on the OD and the can's bore runs wide, so
    # 0.10 of CAD slip is still clearance in the hand, not a press fit.
    if slip < 0.10:
        e.append("fin can would seize: bore %.2f - body %.2f leaves %.2f mm/side "
                 "(want >= 0.10)" % (P["fincan_bore"], od, slip))
    if slip > 0.60:
        e.append("fin can would be sloppy and glue-starved: %.2f mm/side "
                 "(want <= 0.60)" % slip)

    # the motor can's sleeve glues INTO the bore
    cs = (bore - P["can_sleeve_d"]) / 2.0
    if cs < 0.05:
        e.append("motor can sleeve %.2f would not enter the %.2f bore"
                 % (P["can_sleeve_d"], bore))
    if cs > 0.50:
        e.append("motor can sleeve fit is %.2f mm/side - too loose to centre the "
                 "motor (raise can_sleeve_d or drop body_bore)" % cs)

    # the nose cone's shoulder slides into the same bore, and comes out again
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

    # thrust path: the flange butts the aft rim
    if P["can_flange_d"] > P["fincan_bore"] - 0.2:
        e.append("flange %.2f does not clear the fin can bore %.2f"
                 % (P["can_flange_d"], P["fincan_bore"]))
    if abs(P["can_flange_d"] - od) > 0.6:
        e.append("flange %.2f and body OD %.2f differ by %.2f mm - the flange is "
                 "what butts the aft rim, so these should match"
                 % (P["can_flange_d"], od, abs(P["can_flange_d"] - od)))

    # the cap is screwed on outside the body, inside the fin can's mouth
    cap_clear = (P["fincan_bore"] - P["can_cap_d"]) / 2.0
    if cap_clear < 0.4:
        e.append("cap %.2f leaves only %.2f mm to the fin can bore; it must be "
                 "turnable by hand" % (P["can_cap_d"], cap_clear))

    # length
    if P["body_len"] > P["printer_z"] - 10.0:
        e.append("body_len %.1f does not fit the %.0f mm Z axis with a brim"
                 % (P["body_len"], P["printer_z"]))
    if P["body_len"] < P["fincan_len"] + 40.0:
        e.append("body_len %.1f is too short to carry the %.0f mm fin can and "
                 "still have a chute bay" % (P["body_len"], P["fincan_len"]))

    # forward fairing
    if taper_len < 0.0:
        e.append("fwd_taper_len must be >= 0")
    if taper_len > 0:
        rw = (P["nose_base_d"] - P["body_bore"]) / 2.0
        if rw < 0.8:
            e.append("nose_base_d %.2f leaves only %.2f mm of rim wall above the "
                     "%.2f bore (want >= 0.8); raise nose_base_d or the bore "
                     "will be cut open" % (P["nose_base_d"], rw, bore))
        if P["fwd_bore_chamfer"] >= rw - 0.1:
            e.append("fwd_bore_chamfer %.2f eats the %.2f mm rim wall"
                     % (P["fwd_bore_chamfer"], rw))
    if P["aft_od_chamfer"] >= wall - 0.4:
        e.append("aft_od_chamfer %.2f leaves %.2f mm of bed ring"
                 % (P["aft_od_chamfer"], wall - P["aft_od_chamfer"]))

    # cord anchor
    if P["anchor_enabled"]:
        if P["anchor_z"] < 76.0 + 10.0:
            e.append("anchor_z %.1f sits on top of the motor can (block ends "
                     "76 mm in); move it forward" % P["anchor_z"])
        if P["anchor_z"] + P["anchor_len"] > L - P["nose_shoulder_len"] - 10.0:
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
    # FreeCAD's console-mode runner calls _exit on SystemExit, which throws away
    # anything still sitting in stdout's buffer -- flush first or a rejected
    # parameter set prints nothing at all and just exits 1.
    sys.stdout.flush()
    sys.exit(1)
print("params ok: od %.2f  bore %.2f  wall %.2f  len %.1f  taper %.1f deg "
      "(%.1f mm run)" % (P["body_od"], P["body_bore"], wall, L,
                         90.0 - taper_half_deg, taper_len))


# ------------------------------------------------------------------ helpers
def circles_at_radius(shape, radius, tol=0.03, full_only=True):
    """Full circles of the given radius, matched by CURVE TYPE not by length.

    Length matching is a trap: a straight seam edge on the same cylinder has
    the same length as the circle once the part gets long.
    """
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


# ------------------------------------------------------------------- build
print("== building ==")
raw = tube(od_r, bore_r, L, taper_len, nose_r)
pre_vol = raw.Volume
print("pre-chamfer: valid=%s solids=%d vol=%.1f mm3"
      % (raw.isValid(), len(raw.Solids), pre_vol))

solid = raw
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
    print("  %-52s %s  %s" % (name, "PASS" if ok else "FAIL", detail))
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
v_out_cyl = math.pi * od_r ** 2 * (L - taper_len)
v_out_cone = math.pi * taper_len / 3.0 * (od_r ** 2 + od_r * nose_r + nose_r ** 2)
v_bore = math.pi * bore_r ** 2 * L
expect = v_out_cyl + v_out_cone - v_bore
err = 100.0 * (pre_vol - expect) / expect
print("  volume: expected %.1f  measured %.1f  err %+.4f%%  (chamfers removed %.1f)"
      % (expect, pre_vol, err, pre_vol - solid.Volume))
check("volume matches the revolved analytic tube", abs(err) < 0.01,
      "%+.5f%%" % err)

# measured radii off the solid, by bisection -- the STL cannot show these
def outer_r_at(z):
    """OD radius at z: bisect between material (a) and outside (b).

    Do NOT bisect 0..OD+6: the solid is an ANNULUS, so the axis is outside too
    and a monotone search from r=0 walks back down into the bore and returns 0.
    """
    a, b = bore_r + 0.05, od_r + 2.0
    for _ in range(45):
        m = (a + b) / 2.0
        if solid.isInside(Vector(m, 0, z), 1e-6, True):
            a = m
        else:
            b = m
    return a


def bore_r_at(z):
    """Bore radius at z: the last free radius walking outward from the axis."""
    a, b = 0.0, bore_r + 0.5
    for _ in range(45):
        m = (a + b) / 2.0
        if solid.isInside(Vector(m, 0, z), 1e-6, True):
            b = m
        else:
            a = m
    return a


probe_z = [0.2, L * 0.5, L - taper_len - 1.0, L - 1.0, L - 0.2]
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
    if abs(z - 0.2) < 1e-9:                      # inside the aft OD chamfer
        od_d = 2.0 * (od_r - (P["aft_od_chamfer"] - 0.2))
    if abs(z - (L - 0.2)) < 1e-9:                # inside the fwd bore chamfer
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
# live test: a bore 0.1 mm undersize on the body must collide
tight = Part.makeCylinder(P["fincan_hub_od"] / 2.0, 40.0).cut(
    Part.makeCylinder(od_r - 0.1, 44.0, Vector(0, 0, -2.0))).common(solid)
check("fin can fit test is live (a 0.1 mm tight bore collides)",
      tight.Volume > 1.0, "%.2f mm3" % tight.Volume)

# ------------------------------------- fit 2: motor can glues in at the rim
# Can frame: its own z=0 is the stem's aft face; flange 12..15, sleeve 15..30.
# Installed, the flange butts this body's aft rim, so body_z = can_z - 15.
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
# the flange is the thrust path: its forward face must land exactly on the rim
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

# recovery path: the charge has to reach the nose, so nothing may intrude on
# the bore between the motor can's block and the nose shoulder bay.  The cord
# anchor is the only thing that does, and only by its own thickness; report the
# worst free diameter the chute has to pass.
def first_material_r(z):
    a, b = 0.0, bore_r + 0.5
    for _ in range(45):
        m = (a + b) / 2.0
        if solid.isInside(Vector(m, 0, z), 1e-6, True):
            b = m
        else:
            a = m
    return a


bay_z0 = 76.0                                    # forward face of the can's block
bay_z1 = L - P["nose_shoulder_len"]              # aft face of the nose shoulder
scan = [(z, 2.0 * first_material_r(z))
        for z in [bay_z0 + 2.0 + 1.0 * i for i in range(
            int((bay_z1 - bay_z0 - 3.0) / 1.0))]]
min_free = min(d for _, d in scan)
worst_z = [z for z, d in scan if abs(d - min_free) < 1e-6][0]
check("chute bay / charge path is an unbroken %.2f mm bore" % P["body_bore"],
      abs(min_free - P["body_bore"]) < 0.05,
      "min free diameter %.2f mm at z=%.0f" % (min_free, worst_z))
if anchor is not None:
    # the anchor is a separate glue-in part, so this is arithmetic on its own
    # geometry, not a scan of the body
    a_d = 2.0 * (bore_r - P["anchor_gap"] - P["anchor_thick"])
    check("cord anchor leaves >= 26 mm of throat for the chute", a_d >= 26.0,
          "throat %.2f mm" % a_d)

# ------------------------------------------- the anchor actually fits
if anchor is not None:
    a = anchor.copy()
    a.translate(Vector(0, 0, P["anchor_z"]))
    ov = a.common(solid).Volume
    check("cord anchor fits inside the bore it is glued into", ov < 1e-6,
          "interference %.6f mm3, glue gap %.2f mm/side"
          % (ov, P["anchor_gap"]))
    check("cord anchor sits forward of the motor can's block (76 mm)",
          P["anchor_z"] >= 76.0, "%.1f mm" % P["anchor_z"])
    ab = a.BoundBox
    check("cord anchor stays out of the nose shoulder bay",
          ab.ZMax <= L - P["nose_shoulder_len"], "top at z=%.1f, bay starts %.1f"
          % (ab.ZMax, L - P["nose_shoulder_len"]))

# ------------------------------------------------------ printability: faces
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
    """bridge_area > 0 accepts small horizontal ceilings as bridges.

    A cord slot is a through-window: its roof is an unavoidable 0 degrees ledge.
    At 4 mm span it is a bridge, not a support, so it is allowed up to that
    area and reported instead of failing.
    """
    rows = down_faces(shape)
    bed = [r for r in rows if r["zmax"] <= 1e-6]
    off = [r for r in rows if r["zmax"] > 1e-6]
    shallow = [r for r in off if r["angle"] < ANGLE_OK]
    bad = [r for r in shallow if r["area"] > bridge_area]
    bridges = [r for r in shallow if r["area"] <= bridge_area]
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
print_ok, bed_area = printability(solid, "body")
check("body needs no supports (no off-bed downward face below %.0f deg" % ANGLE_OK,
      print_ok, "bed contact %.1f mm2" % bed_area)
if anchor is not None:
    a_ok, a_bed = printability(anchor, "anchor",
                              bridge_area=1.6 * P["anchor_slot_len"]
                              * P["anchor_slot_len"])
    check("cord anchor needs no supports (cord-slot roofs bridge)",
          a_ok, "bed contact %.1f mm2" % a_bed)
g_ok, g_bed = printability(gauge, "gauge")
check("gauge needs no supports", g_ok, "bed contact %.1f mm2" % g_bed)

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
shapes = [("Body36mm", solid, BASE + ".stl"),
          ("Gauge36mm", gauge, BASE + "_gauge.stl")]
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
        gd = Gui.activeDocument()
        if gd is not None:
            gd.activeView().viewAxonometric()
            Gui.SendMsgToActiveView("ViewFit")
        print("gui: shape coloured, view set axonometric and fitted")
    except Exception as exc:
        print("gui: could not set the view (%s)" % exc)
else:
    print("headless: document saved to %s" % fcstd)

import hashlib


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


summary = {
    "design": "36 mm rocket body joining the 18 mm motor can and the 36 mm 4-fin can",
    "stl": os.path.join(OUT, BASE + ".stl"),
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
    "mass_g_pla": round(mass["pla"], 1),
    "mass_g_petg": round(mass["petg"], 1),
    "bed_contact_mm2": round(bed_area, 1),
    "checks_pass": ok,
    "checks": checks,
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
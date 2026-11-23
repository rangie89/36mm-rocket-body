# 36 mm rocket body — the airframe that joins the 18 mm motor can and the 36 mm 4-fin can

The body that makes `18mm-motor-can` and `36mm-fin-can` one rocket. The 18 mm
motor can glues **into** its aft end; the 36 mm 4-fin can slips **over** the aft
102 mm; the printed nose cone's shoulder slides into its forward end. End to end
that is a 435 mm rocket on a 36 mm airframe.

Nothing here is a matter of taste: the two existing printed parts fix the
diameter from both sides, and everything else follows.

**Rev B (2026-11-24): OD 36.00 → 36.30 mm.** +0.30 mm on the outside only, so
the wall went 1.60 → 1.75 mm and the bore stayed at 32.80. Rev A (36.00) and
Rev B (36.30) are told apart with calipers on the OD; the gauge and the launch
lug (`36mm-launch-lug`) both track it. Two consequences to know before printing:

* the fin can now has **0.15 mm/side** slip instead of 0.30 — the tight end of
  the allowed range (`validate()` refuses below 0.15), so dry-fit Rev B in the
  fin can before you commit a 285 mm print;
* the 18 mm motor can's 36.00 flange is now 0.30 mm inside the body's OD, so the
  aft rim stands 0.15 mm proud of the flange, and the forward fairing to the
  nose cone's 35.70 base is a 0.30 mm radial step over 4 mm (4.3°, was 2.1°).

![interface section](interface_section.png)

## The three fits

| mating part | what it needs | what this body gives | clearance |
|---|---|---|---|
| 36 mm 4-fin can (`36mm-fin-can`) | bore 36.60 over a **36.30 OD** tube | OD 36.30 | **0.15 mm/side** slip |
| 18 mm motor can (`18mm-motor-can`) | 32.50 × 15 sleeve into the tube **and** a 36.00 flange on the rim | bore 32.80, OD 36.30 | **0.15 mm/side**, flange 0.30 mm inside the OD |
| printed nose cone (v1) | 32.50 × 15 shoulder, 35.70 base | bore 32.80, forward rim faired to 35.70 | **0.15 mm/side** |
| 18 mm motor can's retainer cap | OD 35.00, it must be turnable inside the fin can's mouth | fin can bore 36.60 | 0.80 mm |

That table is the whole design. The bore is not free: 32.80 is the *narrowest*
bore the motor can's sleeve and the nose cone's shoulder both still enter
(0.15 mm/side), and 36.30 OD is the *widest* the fin can still slips over at the
0.15/side floor (`fincan_bore` 36.60 − 2 × 0.15). Subtract them and the wall is
**1.75 mm** — with the bore pinned by the can and the nose cone, and the OD
pinned by the fin can, it has no choice. Rev B sits exactly on that ceiling; a
third of a millimetre more and `validate()` refuses to build.

The 18 mm motor can's flange is 36.00 against this body's 36.30 OD. It is still
the thrust path — the flange butts the aft rim, so the motor pushes the rim in
compression instead of pulling on four square millimetres of glue — but on Rev B
the flange no longer covers the rim's full width: it presses on the annulus
32.80 → 36.00 and the outer 0.15 mm ring of the rim is left uncovered. The
contact area is 3.20 mm × 113 mm around instead of 1.60 mm; the rim face itself
is 1.75 mm wide by 113 mm around.

## Read this before you print it: mass

| | mass |
|---|---|
| printed body, 1.75 mm solid wall (this file) | **67 g PLA / 68.6 g PETG** |
| same tube in cardboard, 285 mm | ~20-22 g |
| nose cone as printed | 22.6 g |
| 36 mm fin can (PETG) | ~44 g |
| 18 mm motor can + cap (PETG) | 38.1 g |
| Estes C6-5 | 24 g |
| **flying mass with the printed body** | **~197 g** |
| **Estes C6-5 maximum liftoff weight** | **113 g** |

The wall is 1.75 mm, which is four 0.4 mm perimeters plus a sliver — the slicer
will gap-fill the remainder, or set 5 × 0.35 mm lines and get it exactly — so
**0 % infill does not help**. A printed body of this size is a solid-wall tube
and there is no infill trick that changes it. At ~197 g the printed version is
174 % of the C6-5 limit and will not fly safely; even swapping in a cardboard
tube leaves ~151 g, still over.

So be clear about what this part is for:

* it is a **fit-and-assembly master**: print it, glue the two cans on, and you
  have a complete rocket to mock up, load and photograph;
* it is **not** a C6-5 airframe. That rocket needs a motor with more thrust than
  a C6 (check the motor's own published maximum liftoff weight against the
  ~160-200 g you actually weigh), or a lighter airframe.

If you want to fly it on a C6, use the cardboard tube instead. The bore/OD pair
in the table above is the spec to buy or roll to (36.30 OD, 32.80 ID, 1.75 wall,
285 long) — the two printed cans and the nose cone drop straight onto it, and
this repo already carries the fit gauge to check the tube in your hand before
you commit a 285 mm cut.

## Files

| file | what |
|---|---|
| `build_body_36mm.py` | the source of truth: parametric, validates, builds, verifies against both mating parts, exports |
| `body36.stl` | the body, **in print orientation** — aft face at z=0, 285 mm tall, drop it on the plate unrotated |
| `body36_cord_anchor.stl` | shock-cord anchor, print upright as modelled (2.4 g) |
| `body36_gauge.stl` | 20 mm test coupon: one end has the aft rim, the other the forward rim. 4.3 g, ~20 min — **print this first** |
| `body36.step` | all three parts, design orientation (aft face at z=0, +Z toward the nose) |
| `body36.FCStd` | the FreeCAD document |
| `build_summary.json` | every dimension, every check result and the sha256 of each STL from the last build |
| `build.sh` / `check_build.sh` | rebuild + report; and "are the committed STLs what the script produces?" |
| `preview_body.py` / `preview_body.png`, `interface_section.py` / `.svg` / `.png` | the render sheet and the dimensioned fit drawing (both read the built model) |

Rebuild:

```bash
cd ~/Documents/FreeCad-Docs/36mm-rocket-body
./build.sh
```

`check_build.sh` is the one worth knowing: the STLs are committed but generated,
so it rebuilds and compares sha256. `IN SYNC` means the printable files are
exactly what the script produces; `OUT OF SYNC` prints both hashes. The meshes
are byte-reproducible across rebuilds (verified — two consecutive builds give
identical hashes), which is what makes the check meaningful.

## Geometry (design orientation, aft face at z=0, +Z toward the nose)

| z (mm) | feature | OD / bore |
|---|---|---|
| 0 | **aft rim** — the motor can's flange butts here, the fin can slides on here | OD 36.30 / bore 32.80, 0.4 mm OD chamfer |
| 0 – 15 | where the motor can's 32.5 sleeve is glued in | bore 32.80 |
| 0 – 102 | covered by the 36 mm fin can | OD 36.30 |
| 0 – 76 | inside: the motor can's block ends 76 mm in | — |
| 110 – 140 | cord anchor glues in (see Recovery) | bore 32.80, anchor throat 27.70 |
| 270 – 285 | nose cone shoulder bay (fits the 32.5 × 15 shoulder) | bore 32.80 |
| 281 – 285 | forward rim fairing 36.30 → 35.70 to meet the nose cone's base | rim wall 1.45 |
| 285 | forward rim, 0.6 mm bore lead-in | OD 35.70 |

Overall 285 mm, 36.30 OD, 32.80 bore, 1.75 wall. Volume 54.07 cm³, area 621.5 cm².

## Printing

* **Body:** upright, aft face on the bed, **no supports anywhere**. 0.2 mm
  layers, 4 perimeters (the wall is four lines plus a gap-fill sliver — that is
  the part), 0 % infill, 4-5 top/bottom layers, 5 mm brim (bed contact is a
  1.75 mm annulus, 144.8 mm²). ~3-4 h.
  PETG for preference, or ASA/ABS: the aft 100 mm wraps the motor.
* **Print the gauge first.** 20 minutes and 4.3 g tells you whether the fin can
  slips on and whether the motor can's sleeve and the nose shoulder enter,
  before you spend hours on the body. If the gauge is wrong, the fix is one
  number (`body_od` or `body_bore`) and a rebuild, not a reprint.
* **Cord anchor:** upright as modelled, 2.4 mm walls, 20 % infill, brim.
* Vertical print = hoop strength. The extrusion runs circumferentially, so the
  body's ejection-pressure load is carried **in-layer**, not across layer bonds.
  That is the good direction, and it is why a printed tube is acceptable as a
  pressure vessel here even though it is a poor material choice for mass.

## Fitting and assembly

1. **Gauge.** It should slide over the fin can's bore and accept the motor can's
   sleeve and the nose cone's shoulder. If any are tight, stop and adjust.
2. **Motor can.** Dry-fit first: the sleeve enters the aft end and the 36.00
   flange lands on the rim. Then epoxy (5-minute) the sleeve into the bore —
   roughen both surfaces. Do **not** glue the flange face; it is the thrust
   seat. The motor can must go in **before** the fin can, or you cannot reach
   the joint.
3. **Fin can.** Slides over the aft 102 mm from the aft end, aft face flush with
   the body's aft rim. On Rev B that is only **0.15 mm/side** — a firm push fit,
   not the loose 0.30 of Rev A. Check the body actually mics 36.30 first (the
   gauge did that), sand the tube lightly if it drags, epoxy it.
4. **Cord anchor.** Glue at 110 mm up the tube (its aft face), 0.15 mm/side glue
   gap. Thread the shock cord in one 4 mm slot and out the other, over the 8 mm
   bridge, and knot it aft of the anchor. The cord then runs forward through the
   anchor's 27.70 mm throat into the chute bay.
5. **Recovery.** Chute and wadding in the bay 140 → 270 mm, nose cone friction
   fit on its 32.5 × 15 shoulder. The bore is unbroken from the motor can's
   block at 76 mm all the way to the nose, so the ejection charge has a clear
   path (checked: min free diameter 32.80 mm through the whole bay).
6. Tape or glue the cord anchor before the first flight, and pull-test it — it
   is the only thing holding the two halves together.

The body wall is the airframe's airtight surface (there is no cardboard seam to
leak), which is what the ejection charge needs to push the nose off.

## Changing any dimension

Edit the `P` dict at the top of `build_body_36mm.py` and re-run `./build.sh`
(~30 s). `validate()` runs first and refuses to build a combination that would
not fit, printing why and exporting nothing — a bore that the sleeve cannot
enter, a fin can that would seize, a wall too thin to print, a body too long for
the printer, a cord slot too close to its neighbour.

The interface numbers on the right-hand side of `P` (`can_sleeve_d`,
`fincan_bore`, `nose_shoulder_d`, …) are **measurements of the other repos**.
They are there so the fit checks know what they are checking against; if you
re-dimension the fin can, change `fincan_bore` here too and the checks will tell
you whether the body still works.

### If you only have the 35.0 mm v1 tube

Then this body does not apply as drawn: the fin can was designed for a 36.00 OD
tube and its 36.60 bore leaves 0.80 mm/side on a 35.0 tube — glueable but sloppy,
and it changes the forward fairing's step. Two honest options, in order of
preference:

1. get the 36.30 OD / 32.80 bore tube (the spec above), or print this body;
2. re-dimension the fin can (`build_fincan_36mm.py`: `tube_od` 36.0 → 35.0)
   and print a new can. The motor can and nose cone already fit that tube.

### Rev history

| rev | OD | bore | wall | note |
|---|---|---|---|---|
| A | 36.00 | 32.80 | 1.60 | as first printed; 0.30 mm/side fin-can slip |
| **B** | **36.30** | 32.80 | **1.75** | +0.30 mm outside for the printed tube's fit; fin-can slip now 0.15/side. Gauge, STLs and the launch lug all rebuilt |

## What was verified

22 checks, all passing on every build (`build_summary.json` carries them all
with their details). The interesting ones:

* **volume exact** — 54067.3 mm³ expected from the revolved tube + frustum minus
  the bore, against 54067.3 measured, **+0.00000 %**;
* **OD and bore measured off the built solid**, by bisection at five heights:
  36.300 and 32.800 everywhere, including the 4.3° forward fairing
  (35.850 at z=284, 35.730 at 284.8) — the STL cannot show a taper, the solid
  can;
* **fin can fit, full size**: a 36.60 bore × 102 dummy slides over with
  **0.000000 mm³** interference, 0.15 mm/side, and the test is live — a bore
  0.1 mm tight collides for 450.92 mm³;
* **motor can fit, full size**: the 32.50 × 15 sleeve enters with **0.000000
  mm³**, a 0.5 mm oversize sleeve collides for 155.04 mm³, and the 36.00 flange
  spans z −3.00…0.00, i.e. its forward face is exactly on the rim;
* **nose cone fit**: the 32.50 × 15 shoulder enters with **0.000000 mm³**, a
  0.5 mm oversize shoulder collides for 149.35 mm³;
* **charge path**: a 1 mm scan of the bore from the motor can's block (76 mm) to
  the nose bay (270 mm) never finds material — min free diameter 32.80;
* **printability from the solid's faces, not assumed**: the body has exactly
  two downward-facing faces (the bed ring; 144.8 mm² of contact) and **no
  off-bed downward face at all**, so no supports. The cord anchor's only
  shallow faces are the two cord-slot roofs, 9.63 mm² each, which bridge.

## Build notes worth keeping

Traps that cost time here, all now handled in the script:

* **A tube is an annulus, so monotone bisection lies.** Probing the OD by
  bisecting 0 → OD+6 returns **0**: the axis is *outside* the solid too, so the
  search walks back down into the bore and never finds material. Start the
  bisection inside the wall instead. (`bore_r_at` is fine from the axis — the
  bore is monotone inward — which is why the bore read correctly while the OD
  read 0.000 and looked like a broken model.)
* **FreeCAD's console runner calls `_exit` on `SystemExit`, throwing away
  buffered stdout.** A rejected parameter set printed *nothing at all* and just
  exited 1, which reads exactly like FreeCAD failing to start. `sys.stdout.flush()`
  before every `sys.exit()`.
* **Radius vs diameter in the validator.** `nose_base_d` is a diameter; mixing it
  with `bore` reported a −14.95 mm rim wall. The validator is the last place to
  be sloppy — it is what you trust when you edit a number.
* **A glue-in part is not in the solid.** The cord anchor is a *separate* part,
  so a bore scan of the body correctly shows a clear 32.80 throat and proves
  nothing about the anchor; its throat has to be checked arithmetically from its
  own parameters.
* **A cord slot is a through-window, and its roof is a 0° ledge.** That is a
  bridge, not a support: 9.63 mm² over a 4 mm span. The printability check takes
  an explicit bridge allowance rather than failing the part or silently
  ignoring ledges.
* **Stale bytecode** — `FreeCAD --console script.py` imports the script, so a
  same-second, same-size edit can run old code. `build.sh` deletes
  `__pycache__` before every build.

## Licence

None chosen yet — a repository with no licence is all rights reserved. The code
is the author's own. If this ever goes public, pick a licence for the design
files first: CC BY-NC-SA 4.0 to keep it non-commercial and share-alike, or
CERN-OHL-S / CC BY-SA 4.0 to allow commercial use.

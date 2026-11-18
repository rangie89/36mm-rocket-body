# -*- coding: utf-8 -*-
"""Minimal numpy software renderer: binary STL -> shaded PNG (no external deps).

Usage: python3 stl_render.py part.stl out.png [panel_azim,panel_elev ...]
"""
import sys, os, struct, zlib, math
import numpy as np


def read_binary_stl(path):
    with open(path, "rb") as fh:
        head = fh.read(84)
        n = struct.unpack("<I", head[80:84])[0]
        data = np.frombuffer(fh.read(n * 50), dtype=np.uint8).reshape(n, 50)
    tri = data[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(np.float64)
    return tri


def write_png(path, rgb):
    H, W, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(H))

    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    hdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", hdr)
           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


def cam_basis(azim_deg, elev_deg):
    a, e = math.radians(azim_deg), math.radians(elev_deg)
    view = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    world_up = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(world_up, view)) > 0.999:
        world_up = np.array([0.0, 1.0, 0.0])
    right = np.cross(world_up, view); right /= np.linalg.norm(right)
    up = np.cross(view, right); up /= np.linalg.norm(up)
    return view, right, up


def render(tri, azim, elev, W, H, ss=2, bg=(18, 20, 24), base=(0.36, 0.62, 0.86)):
    W, H = W * ss, H * ss
    view, right, up = cam_basis(azim, elev)

    flat = tri.reshape(-1, 3)
    sx = flat @ right
    sy = flat @ up
    sz = flat @ view
    minsx, maxsx = sx.min(), sx.max()
    minsy, maxsy = sy.min(), sy.max()
    span = max(maxsx - minsx, maxsy - minsy)
    pad = 0.06
    scale = (1.0 - 2 * pad) * min(W, H) / span
    cx, cy = (minsx + maxsx) / 2, (minsy + maxsy) / 2
    px = (sx - cx) * scale + W / 2
    py = H / 2 - (sy - cy) * scale
    px = px.reshape(-1, 3); py = py.reshape(-1, 3); pz = sz.reshape(-1, 3)
    tri_n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(tri_n, axis=1, keepdims=True); ln[ln == 0] = 1
    tri_n = tri_n / ln

    light = np.array([-0.35, -0.55, 0.76]); light /= np.linalg.norm(light)
    facing = tri_n @ view
    n_out = np.where(facing[:, None] < 0, tri_n, -tri_n)
    lam = np.clip(n_out @ light, 0, 1)
    shade = 0.24 + 0.76 * lam
    col = (np.array(base)[None, :] * shade[:, None] * 255).astype(np.uint8)

    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[:, :] = bg
    zbuf = np.full((H, W), -1e9)

    order = np.argsort(pz.mean(axis=1))
    for t in order:
        x0, x1 = px[t].min(), px[t].max()
        y0, y1 = py[t].min(), py[t].max()
        ix0, ix1 = max(int(math.floor(x0)), 0), min(int(math.ceil(x1)) + 1, W)
        iy0, iy1 = max(int(math.floor(y0)), 0), min(int(math.ceil(y1)) + 1, H)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        xs = np.arange(ix0, ix1) + 0.5
        ys = np.arange(iy0, iy1) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        ax, ay = px[t, 0], py[t, 0]
        bx, by = px[t, 1], py[t, 1]
        cx2, cy2 = px[t, 2], py[t, 2]
        d = (by - cy2) * (ax - cx2) + (cx2 - bx) * (ay - cy2)
        if abs(d) < 1e-12:
            continue
        w0 = ((by - cy2) * (gx - cx2) + (cx2 - bx) * (gy - cy2)) / d
        w1 = ((cy2 - ay) * (gx - cx2) + (ax - cx2) * (gy - cy2)) / d
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not inside.any():
            continue
        z = w0 * pz[t, 0] + w1 * pz[t, 1] + w2 * pz[t, 2]
        sub = zbuf[iy0:iy1, ix0:ix1]
        upd = inside & (z > sub)
        sub[upd] = z[upd]
        img[iy0:iy1, ix0:ix1][upd] = col[t]

    # box downsample (supersample resolve)
    img = img.reshape(H // ss, ss, W // ss, ss, 3).astype(np.uint16).mean(axis=(1, 3)).astype(np.uint8)
    return img


def labelled(img, W, H, text, scale=2):
    # 5x7 bitmap font, uppercase, minimal glyph set
    F = {
        "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
        "B": ["11110", "10001", "11110", "10001", "10001", "10001", "11110"],
        "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
        "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
        "E": ["11111", "10000", "11110", "10000", "10000", "10000", "11111"],
        "F": ["11111", "10000", "11110", "10000", "10000", "10000", "10000"],
        "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
        "H": ["10001", "10001", "11111", "10001", "10001", "10001", "10001"],
        "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
        "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
        "M": ["10001", "11011", "10101", "10001", "10001", "10001", "10001"],
        "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
        "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
        "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
        "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
        "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
        "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
        "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
        "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
        "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
        "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
        "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
        " ": ["00000"] * 7,
        "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
        "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
        "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
        "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
        "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
        "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
        "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
        "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
        "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
        "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
        ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
        ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
        "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
        "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
        "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
        ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
        "=": ["00000", "11111", "00000", "11111", "00000", "00000", "00000"],
        "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
        "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
        "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    }
    txt = text.upper()
    cw = 6 * scale
    x0, y0 = 8 * scale, 8 * scale
    for i, ch in enumerate(txt):
        g = F.get(ch, F[" "])
        for r, row in enumerate(g):
            for c, bit in enumerate(row):
                if bit == "1":
                    yy = y0 + r * scale
                    xx = x0 + i * cw + c * scale
                    if 0 <= yy < H - scale and 0 <= xx < W - scale:
                        img[yy:yy + scale, xx:xx + scale] = (235, 238, 242)
    return img


if __name__ == "__main__":
    stl = sys.argv[1]
    out = sys.argv[2]
    tri = read_binary_stl(stl)
    print("triangles:", len(tri))

    panels = [(35, 22, "3/4 VIEW"), (0, 0, "SIDE - BORE ON"), (0, 89.9, "TOP DOWN - 4 FINS"),
              (12, 3, "FIN CHAMFERS EDGE ON")]
    PW, PH = 560, 620
    imgs = []
    for az, el, lab in panels:
        im = render(tri, az, el, PW, PH, ss=2)
        im = labelled(im, PW, PH, lab)
        imgs.append(im)
    sheet = np.concatenate(imgs, axis=1)
    write_png(out, sheet)
    print("wrote", out, sheet.shape)

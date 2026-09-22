#!/usr/bin/env python3
"""Generate CubeOS boot animation frames (part0 intro, part1 loop, part2 outro).

Usage:
    ./make-cubeos-frames.py out && (cd out && COPYFILE_DISABLE=1 \\
        tar --format ustar -cf ../bootanimation.tar part0 part1 part2)
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1620, 540
SS = 2  # supersampling factor for anti-aliasing
FPS = 60
STROKE = 12
CUBE_R = 125  # half edge length in px (before projection)
PITCH = math.atan(1 / math.sqrt(2))  # isometric elevation
ISO_YAW = math.pi / 4

VERTS = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
EDGES = [(a, b) for a in range(8) for b in range(a + 1, 8)
         if sum(VERTS[a][i] != VERTS[b][i] for i in range(3)) == 1]


def _trace_order():
    """Order edges outward from the corner nearest the viewer, each edge
    oriented so it grows out of an already-drawn vertex."""
    # nearest-to-viewer vertex at the isometric pose
    start = min(range(8), key=lambda i: project(VERTS[i], ISO_YAW, 0, 0, 1)[2])
    seen, order, frontier = {start}, [], [start]
    while frontier:
        nxt = []
        for v in frontier:
            for a, b in EDGES:
                if v in (a, b):
                    o = b if a == v else a
                    if (v, o) not in order and (o, v) not in order:
                        order.append((v, o))
                        if o not in seen:
                            seen.add(o)
                            nxt.append(o)
        frontier = nxt
    return order

FONT = ImageFont.load_default(size=150 * SS)  # Aileron (CC0)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def project(v, yaw, cx, cy, scale):
    x, y, z = v
    # yaw around vertical (y) axis
    x, z = x * math.cos(yaw) + z * math.sin(yaw), -x * math.sin(yaw) + z * math.cos(yaw)
    # pitch around x axis
    y, z = y * math.cos(PITCH) - z * math.sin(PITCH), y * math.sin(PITCH) + z * math.cos(PITCH)
    s = CUBE_R * scale * SS
    return (cx * SS + x * s, cy * SS - y * s, z)


def draw_cube(d, yaw, cx=W / 2, cy=H / 2, scale=1.0, progress=1.0, alpha=1.0):
    pts = [project(v, yaw, cx, cy, scale) for v in VERTS]
    n = len(EDGES)
    items = []
    for i, (a, b) in enumerate(EDGES):
        # each edge draws over its own slice of the overall progress
        p = ease((progress * n - i * 0.6) / 1.6) if progress < 1 else 1.0
        if p <= 0:
            continue
        pa, pb = pts[a], pts[b]
        end = (pa[0] + (pb[0] - pa[0]) * p, pa[1] + (pb[1] - pa[1]) * p)
        depth = (pa[2] + pb[2]) / 2  # -ve = towards viewer
        items.append((depth, (pa[0], pa[1]), end))
    items.sort(key=lambda it: -it[0])  # far edges first
    for depth, s, e in items:
        shade = 0.35 + 0.65 * (1 - (depth + 1.2) / 2.4)
        c = int(255 * max(0.35, min(1.0, shade)) * alpha)
        w = STROKE * SS
        d.line([s, e], fill=(c, c, c), width=w)
        r = w / 2
        for px, py in (s, e):
            d.ellipse([px - r, py - r, px + r, py + r], fill=(c, c, c))


def new_frame():
    img = Image.new("RGB", (W * SS, H * SS), (0, 0, 0))
    return img, ImageDraw.Draw(img)


def save(img, path):
    img.resize((W, H), Image.LANCZOS).save(path, optimize=True)


def main(out):
    global EDGES
    EDGES = _trace_order()
    idx = 0

    def emit(img, part):
        nonlocal idx
        save(img, os.path.join(out, part, f"{idx:03d}.png"))
        idx += 1

    for p in ("part0", "part1", "part2"):
        os.makedirs(os.path.join(out, p), exist_ok=True)

    # part0: edges draw in at the isometric pose (1s)
    for f in range(60):
        img, d = new_frame()
        draw_cube(d, ISO_YAW, progress=f / 59 if f < 59 else 1.0)
        emit(img, "part0")

    # part1: seamless loop, a 90° turn (cube is symmetric) over 1.5s
    for f in range(90):
        img, d = new_frame()
        t = f / 90
        draw_cube(d, ISO_YAW + ease(t) * math.pi / 2)
        emit(img, "part1")

    # part2: cube slides left and shrinks, "CubeOS" fades in (1.25s)
    text = "CubeOS"
    tw = FONT.getlength(text) / SS
    gap = 70
    small = 0.72
    cube_w = CUBE_R * small * 2 * 1.2
    total = cube_w + gap + tw
    end_cx = W / 2 - total / 2 + cube_w / 2
    tx = end_cx + cube_w / 2 + gap
    for f in range(75):
        img, d = new_frame()
        t = ease(f / 45)
        cx = W / 2 + (end_cx - W / 2) * t
        draw_cube(d, ISO_YAW, cx=cx, scale=1 + (small - 1) * t)
        a = ease((f - 20) / 40)
        if a > 0:
            c = int(255 * a)
            d.text((tx * SS + (1 - a) * 30 * SS, H / 2 * SS), text,
                   font=FONT, fill=(c, c, c), anchor="lm")
        emit(img, "part2")


if __name__ == "__main__":
    main(sys.argv[1])

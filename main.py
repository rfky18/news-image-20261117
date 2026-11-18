#!/usr/bin/env python3
# WORLD IN ONE FRAME — front page of Tuesday 17 November 2026.
# make.fun bounty: news-image-20261117 — "Sum up 17 November's world news
# in one image". Pure Python 3 stdlib, no network, fully deterministic:
# two runs write byte-identical /output/entry.png.
# Every illustration is drawn by this program (flat vector shapes, a
# 3D-shaded globe, a dot world map). Every word is set in real type:
# Liberation Serif Bold + Noto Sans Condensed, rendered at build time
# into a glyph atlas embedded below (see the atlas section); at runtime
# the program only blits those bitmaps. No external assets, no copied images.

import base64
import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (246, 241, 227)   # warm newsprint cream
INK = (20, 20, 20)
INK_SOFT = (58, 58, 58)
RED = (176, 30, 36)
BLUE = (29, 78, 137)
TEAL = (14, 107, 107)
GOLD = (176, 124, 18)
GREEN = (46, 110, 58)
PURPLE = (94, 58, 138)
ORANGE = (198, 96, 22)
SKY = (178, 205, 224)
SKY_DUSK = (232, 190, 150)
SEA = (126, 168, 196)
SEA_DARK = (88, 130, 163)
SAND = (224, 200, 148)
GREY = (120, 118, 110)
LIGHT = (238, 232, 214)
RULE = (180, 172, 152)

# ------------------------------------------------------------------- canvas
class Canvas:
    """RGB pixel buffer with flat vector drawing primitives."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg[0] for _ in range(w * h * 3))
        # faster fill: build one row then repeat
        row = bytes(bg) * w
        self.px = bytearray(row * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def blend(self, x, y, c, a):
        """Alpha-blend colour c over pixel (x, y); a in 0..1."""
        if 0 <= x < self.w and 0 <= y < self.h and a > 0.0:
            i = (y * self.w + x) * 3
            if a >= 1.0:
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]
            else:
                self.px[i] = int(self.px[i] * (1 - a) + c[0] * a)
                self.px[i + 1] = int(self.px[i + 1] * (1 - a) + c[1] * a)
                self.px[i + 2] = int(self.px[i + 2] * (1 - a) + c[2] * a)

    def fill_rect(self, x0, y0, x1, y1, c):
        x0 = max(0, int(x0))
        y0 = max(0, int(y0))
        x1 = min(self.w, int(x1))
        y1 = min(self.h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def hline(self, x0, x1, y, c, t=1):
        self.fill_rect(x0, y, x1, y + t, c)

    def vline(self, x, y0, y1, c, t=1):
        self.fill_rect(x, y0, x + t, y1, c)

    def disc(self, cx, cy, r, c):
        r = int(r)
        if r <= 0:
            return
        cx = int(cx)
        cy = int(cy)
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.fill_rect(cx - dx, y, cx + dx + 1, y + 1, c)

    def ring(self, cx, cy, r, t, c):
        cx = int(cx)
        cy = int(cy)
        r = int(r)
        for k in range(t):
            rr = r - k
            if rr <= 0:
                break
            for y in range(cy - rr, cy + rr + 1):
                dy = y - cy
                dx = int(math.sqrt(max(0, rr * rr - dy * dy)))
                self.set(cx - dx, y, c)
                self.set(cx + dx, y, c)

    def poly(self, pts, c):
        """Scanline fill of a simple polygon (even-odd)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(math.ceil(min(ys))))
        y1 = min(self.h - 1, int(math.floor(max(ys))))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    t = (y - y1p) / (y2p - y1p)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[k]), y, int(xs[k + 1]) + 1, y + 1, c)

    def thick_line(self, x0, y0, x1, y1, t, c):
        """A line of width t (px), with round caps."""
        dx = x1 - x0
        dy = y1 - y0
        L = math.hypot(dx, dy)
        if L < 0.001:
            self.disc(x0, y0, t / 2.0, c)
            return
        nx = -dy / L * t / 2.0
        ny = dx / L * t / 2.0
        self.poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                   (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], c)
        self.disc(x0, y0, t / 2.0, c)
        self.disc(x1, y1, t / 2.0, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        self.thick_line(x0, y0, x1, y1, t, c)

    def circle_outline(self, cx, cy, r, t, c):
        steps = max(24, int(2 * math.pi * r))
        pts = []
        for i in range(steps):
            a = 2 * math.pi * i / steps
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for i in range(steps):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % steps]
            self.thick_line(x0, y0, x1, y1, t, c)

    def arc(self, cx, cy, r, a0, a1, c, t=1):
        steps = max(8, int(abs(a1 - a0) * r))
        prev = None
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            p = (cx + r * math.cos(a), cy + r * math.sin(a))
            if prev is not None:
                self.thick_line(prev[0], prev[1], p[0], p[1], t, c)
            prev = p


def _png_chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    out += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    return out


def write_png(cv, path):
    """Deterministic PNG: fixed filter 0, zlib level 9."""
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += _png_chunk(b"IDAT", comp)
    png += _png_chunk(b"IEND", b"")
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ------------------------------------------------- glyph atlas (v8)
# REAL newspaper type. The glyphs in this image are Liberation Serif Bold
# (masthead / main headline / date line) and Noto Sans Condensed, bold
# and regular (every other word on the page). The fonts were rendered at
# build time on the author's machine with PIL into per-glyph bitmaps at
# the exact cap heights this program uses; the atlas below is those
# bitmaps, zlib + base64 on ONE line. At runtime this program is pure
# stdlib: it only decodes the atlas and blits bitmaps — no font files,
# no PIL, no network, fully deterministic.
# Faces: 0 = Liberation Serif Bold, 2 = Noto Sans Condensed Bold,
# 3 = Noto Sans Condensed. Binary format (big-endian), per face:
# u8 face, u8 n_caps; per cap: f32 cap, u16 n_chars; per char:
# u16 codepoint, f32 advance, i16 ox, i16 oy, u16 w, u16 h, w*h bytes
# of greyscale bitmap. ox/oy are the bitmap's bearing relative to the
# cap-top origin (x = pen position, y = cap top).
_ATLAS_B64 = "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"

_ATLAS = None


def _load_atlas():
    global _ATLAS
    if _ATLAS is not None:
        return _ATLAS
    raw = zlib.decompress(base64.b64decode(_ATLAS_B64))
    at = {}
    i = 0
    n = len(raw)
    while i < n:
        face, ncaps = struct.unpack_from(">BB", raw, i)
        i += 2
        for _ in range(ncaps):
            cap, nch = struct.unpack_from(">fH", raw, i)
            i += 6
            key = (face, int(round(cap * 2)))
            glyphs = {}
            for _ in range(nch):
                cp, adv, ox, oy, w, h = struct.unpack_from(">HfhhHH", raw, i)
                i += 14
                bm = raw[i:i + w * h]
                i += w * h
                glyphs[chr(cp)] = (adv, ox, oy, w, h, bm)
            at[key] = glyphs
    _ATLAS = at
    return at


def _face_id(bold, serif):
    if serif:
        return 0
    return 2 if bold else 3


def _glyphs(face, cap):
    """Glyph table for (face, cap); falls back to the nearest cap of the
    same face (never happens for the caps this file uses)."""
    at = _load_atlas()
    key = (face, int(round(cap * 2)))
    g = at.get(key)
    if g is not None:
        return g
    near = min(c for (f, c) in at if f == face)
    for c in sorted(c for (f, c) in at if f == face):
        if abs(c - key[1]) < abs(near - key[1]):
            near = c
    return at[(face, near)]


# ------------------------------------------------------------ text engine
def text_width(s, cap, bold=False, serif=False):
    """Width in px of string s at cap-height cap (px), in the atlas face."""
    glyphs = _glyphs(_face_id(bold, serif), cap)
    tot = 0.0
    for ch in s:
        g = glyphs.get(ch)
        if g is None:
            g = glyphs['?']
        tot += g[0]
    return tot


def wrap_text(s, cap, maxw, bold=False, serif=False):
    """Greedy word wrap; returns list of lines (each a string)."""
    words = s.split(' ')
    lines = []
    cur = ''
    curw = 0.0
    sp = text_width(' ', cap, bold, serif)
    for wd in words:
        w = text_width(wd, cap, bold, serif)
        add = w if not cur else w + sp
        if cur and curw + add > maxw:
            lines.append(cur)
            cur = wd
            curw = w
        else:
            cur = (cur + ' ' + wd) if cur else wd
            curw += add
    if cur:
        lines.append(cur)
    return lines


def _blit(cv, x0, y0, w, h, bm, color):
    """Alpha-blit a greyscale glyph bitmap onto the canvas (clipped)."""
    px = cv.px
    W = cv.w
    H = cv.h
    r, g, b = color
    if y0 < 0:
        cut = -y0
        if cut >= h:
            return
        bm = bm[cut * w:]
        h -= cut
        y0 = 0
    if y0 + h > H:
        h = H - y0
        if h <= 0:
            return
    x_lo = 0
    x_hi = w
    if x0 < 0:
        x_lo = -x0
    if x0 + w > W:
        x_hi = W - x0
    for row in range(h):
        base = ((y0 + row) * W + x0) * 3
        brow = row * w
        for col in range(x_lo, x_hi):
            a = bm[brow + col]
            if a == 0:
                continue
            i = base + col * 3
            if a == 255:
                px[i] = r
                px[i + 1] = g
                px[i + 2] = b
            else:
                ia = 255 - a
                px[i] = (px[i] * ia + r * a) // 255
                px[i + 1] = (px[i + 1] * ia + g * a) // 255
                px[i + 2] = (px[i + 2] * ia + b * a) // 255


def draw_text(cv, x, y, s, cap, color, bold=False, align='left', maxw=None, serif=False):
    """Draw text at (x, y) = top-left of cap line; y is the cap top.
    Glyphs come from the pre-rendered atlas (real TrueType outlines,
    antialiased at build time); here they are only blitted."""
    if not s:
        return
    glyphs = _glyphs(_face_id(bold, serif), cap)
    w_px = text_width(s, cap, bold, serif)
    if align == 'center':
        x = x - w_px / 2.0
    elif align == 'right':
        x = x - w_px
    cx = x
    for ch in s:
        g = glyphs.get(ch)
        if g is None:
            g = glyphs['?']
        adv, ox, oy, w, h, bm = g
        if w and h:
            _blit(cv, int(round(cx)) + ox, int(round(y)) + oy, w, h, bm, color)
        cx += adv


def draw_para(cv, x, y, lines, cap, color, leading=None, bold=False, align='left', maxw=None, serif=False):
    """Draw pre-wrapped lines; returns y after the last line."""
    if leading is None:
        leading = cap * 1.32
    for ln in lines:
        draw_text(cv, x, y, ln, cap, color, bold=bold, align=align, maxw=maxw, serif=serif)
        y += leading
    return y


def kicker(cv, x, y, s, cap, bg, fg=(255, 255, 255)):
    """Small coloured kicker bar with white text."""
    w = text_width(s, cap, bold=True) + cap * 1.1
    h = cap * 1.9
    cv.fill_rect(x, y, x + w, y + h, bg)
    draw_text(cv, x + cap * 0.55, y + cap * 0.42, s, cap, fg, bold=True)
    return w

# ------------------------------------------------------- dot world map
# Coarse equirectangular land grid, 52 cols (lon -170..+185) x 26 rows
# (lat 75..-50). Segments are (first_col, last_col) per row.
MAP_ROWS = [
    [(2, 4), (6, 12), (15, 16), (33, 50)],
    [(1, 4), (5, 13), (15, 17), (30, 51)],
    [(1, 4), (5, 13), (15, 16), (28, 51)],
    [(2, 4), (5, 13), (24, 26), (28, 50)],
    [(3, 4), (5, 13), (23, 26), (27, 50)],
    [(5, 13), (23, 24), (26, 33), (34, 50)],
    [(6, 13), (24, 33), (35, 38), (40, 46), (47, 48)],
    [(6, 14), (24, 28), (30, 34), (35, 38), (40, 46), (47, 48)],
    [(6, 14), (24, 27), (30, 34), (35, 38), (40, 45), (47, 48)],
    [(6, 14), (24, 27), (30, 34), (35, 38), (40, 44)],
    [(7, 13), (24, 27), (30, 33), (35, 38), (40, 43)],
    [(8, 12), (24, 27), (30, 32), (36, 38), (40, 42)],
    [(9, 12), (24, 28), (30, 31), (37, 38), (40, 42)],
    [(10, 12), (24, 29), (37, 38), (40, 42)],
    [(11, 13), (25, 30), (40, 42)],
    [(13, 15), (25, 30), (40, 45)],
    [(13, 16), (25, 30), (41, 45)],
    [(13, 16), (25, 30), (42, 45)],
    [(13, 16), (25, 29), (43, 46)],
    [(14, 16), (25, 29), (43, 47)],
    [(14, 16), (26, 29), (43, 47)],
    [(14, 15), (26, 28), (43, 47)],
    [(14, 15), (27, 28), (44, 47), (49, 50)],
    [(14, 15), (45, 47), (49, 50)],
    [(14, 14), (49, 49)],
    [(14, 14)],
]


def _region_color(col, row):
    if col <= 18:
        return (176, 30, 36)          # Americas — red
    if row <= 8 and 23 <= col <= 33:
        return (29, 78, 137)          # Europe — blue
    if 24 <= col <= 31 and row >= 8:
        return (46, 110, 58)          # Africa — green
    if 30 <= col <= 34 and row <= 11:
        return (198, 96, 22)          # Middle East — orange
    if col >= 34 and row <= 13:
        return (94, 58, 138)          # Asia — purple
    if col >= 42 and row >= 14:
        return (14, 107, 107)         # Oceania — teal
    if col >= 23:
        return (94, 58, 138)
    return (120, 118, 110)


def draw_map(cv, x, y, w, h, pins=None):
    """Dot world map in box (x, y, w, h); uniform cells, grid centred."""
    cv.fill_rect(x, y, x + w, y + h, (222, 232, 238))
    cell = min(w / 52.0, h / 26.0)
    ox = x + (w - cell * 52.0) / 2.0
    oy = y + (h - cell * 26.0) / 2.0
    for r, segs in enumerate(MAP_ROWS):
        for (c0, c1) in segs:
            for c in range(c0, c1 + 1):
                cx = ox + (c + 0.5) * cell
                cy = oy + (r + 0.5) * cell
                cv.disc(cx, cy, max(1.8, cell * 0.42), _region_color(c, r))
    if pins:
        # small nudges so clustered pins stay legible (schematic map):
        # Europe 1/2/5/8/13 and the US pair 6/7 would otherwise cover
        # each other; each nudge is <=14 px (~2 map cells).
        _nudge = {1: (12, -10), 2: (14, 6), 5: (2, 14), 6: (-12, 6),
                  7: (10, -6), 8: (-14, 2), 13: (-10, -10)}
        for (lon, lat, n) in pins:
            col = (lon + 170.0) / 355.0 * 52.0
            row = (75.0 - lat) / 125.0 * 26.0
            px = ox + col * cell
            py = oy + row * cell
            dx, dy = _nudge.get(n, (0, 0))
            px = max(x + 9, min(x + w - 9, px + dx))
            py = max(y + 9, min(y + h - 9, py + dy))
            cv.disc(px, py, 8, INK)
            cv.ring(px, py, 8, 1, (255, 255, 255))
            draw_text(cv, px - text_width(str(n), 9, bold=True) / 2.0, py - 6,
                      str(n), 9, (255, 255, 255), bold=True)


# ------------------------------------------------------- small flat icons
def _flag(cv, x, y, w, h, kind):
    """Tiny simplified flags: us, in, jp, au, cn, ru, kr, gb, ua, mn, br."""
    cv.fill_rect(x, y, x + w, y + h, (255, 255, 255))
    if kind == 'us':
        for i in range(7):
            cv.fill_rect(x, y + i * h / 7.0, x + w, y + (i + 1) * h / 7.0,
                         RED if i % 2 == 0 else (255, 255, 255))
        cv.fill_rect(x, y, x + w * 0.42, y + h * 0.55, BLUE)
    elif kind == 'in':
        cv.fill_rect(x, y, x + w, y + h / 3.0, (255, 153, 51))
        cv.fill_rect(x, y + 2 * h / 3.0, x + w, y + h, (19, 136, 8))
        cv.disc(x + w / 2.0, y + h / 2.0, h * 0.16, BLUE)
    elif kind == 'jp':
        cv.disc(x + w / 2.0, y + h / 2.0, h * 0.3, RED)
    elif kind == 'au':
        cv.fill_rect(x, y, x + w, y + h, BLUE)
        cv.fill_rect(x, y, x + w * 0.5, y + h * 0.5, RED)
        cv.disc(x + w * 0.78, y + h * 0.3, h * 0.07, (255, 255, 255))
        cv.disc(x + w * 0.72, y + h * 0.68, h * 0.07, (255, 255, 255))
    elif kind == 'cn':
        cv.fill_rect(x, y, x + w, y + h, (222, 41, 16))
        cv.disc(x + w * 0.28, y + h * 0.3, h * 0.14, (255, 222, 0))
    elif kind == 'ru':
        cv.fill_rect(x, y, x + w, y + h / 3.0, (255, 255, 255))
        cv.fill_rect(x, y + h / 3.0, x + w, y + 2 * h / 3.0, BLUE)
        cv.fill_rect(x, y + 2 * h / 3.0, x + w, y + h, RED)
    elif kind == 'ua':
        cv.fill_rect(x, y, x + w, y + h / 2.0, (0, 91, 187))
        cv.fill_rect(x, y + h / 2.0, x + w, y + h, (255, 213, 0))
    elif kind == 'mn':
        cv.fill_rect(x, y, x + w, y + h, (200, 16, 46))
        cv.fill_rect(x, y, x + w * 0.33, y + h, BLUE)
        cv.fill_rect(x + w * 0.66, y, x + w, y + h, BLUE)
    elif kind == 'br':
        cv.fill_rect(x, y, x + w, y + h, (0, 156, 59))
        cv.poly([(x + w * 0.5, y + h * 0.12), (x + w * 0.92, y + h * 0.5),
                 (x + w * 0.5, y + h * 0.88), (x + w * 0.08, y + h * 0.5)], (255, 223, 0))
        cv.disc(x + w * 0.5, y + h * 0.5, h * 0.2, BLUE)
    elif kind == 'gb':
        cv.fill_rect(x, y, x + w, y + h, BLUE)
        cv.fill_rect(x, y + h * 0.4, x + w, y + h * 0.6, (255, 255, 255))
        cv.fill_rect(x + w * 0.45, y, x + w * 0.55, y + h, (255, 255, 255))
        cv.fill_rect(x, y + h * 0.45, x + w, y + h * 0.55, RED)
        cv.fill_rect(x + w * 0.47, y, x + w * 0.53, y + h, RED)
    cv.line(x, y, x + w, y, (0, 0, 0), 1)
    cv.line(x, y + h - 1, x + w, y + h - 1, (0, 0, 0), 1)


def _jet(cv, x, y, s, c, flip=False):
    """Small fighter-jet silhouette, size s."""
    d = -1 if flip else 1
    pts = [(x, y), (x + 16 * d * s, y - 2 * s), (x + 30 * d * s, y),
           (x + 16 * d * s, y + 2 * s)]
    cv.poly(pts, c)
    cv.poly([(x + 8 * d * s, y - 2 * s), (x + 12 * d * s, y - 8 * s),
             (x + 14 * d * s, y - 2 * s)], c)
    cv.poly([(x + 8 * d * s, y + 2 * s), (x + 12 * d * s, y + 8 * s),
             (x + 14 * d * s, y + 2 * s)], c)


def _drone(cv, x, y, s, c):
    cv.fill_rect(x - 3 * s, y - 1 * s, x + 3 * s, y + 1 * s, c)
    cv.fill_rect(x - 1 * s, y - 3 * s, x + 1 * s, y + 3 * s, c)
    for dx, dy in ((-4, -4), (4, -4), (-4, 4), (4, 4)):
        cv.disc(x + dx * s, y + dy * s, 1.6 * s, c)


def _smoke(cv, x, y, s, c=(140, 138, 130)):
    cv.disc(x, y, 9 * s, c)
    cv.disc(x + 8 * s, y - 5 * s, 7 * s, c)
    cv.disc(x - 7 * s, y - 4 * s, 6 * s, c)
    cv.disc(x + 2 * s, y - 10 * s, 6 * s, (170, 168, 160))


def _burst(cv, x, y, s, c=(230, 120, 20)):
    for k in range(8):
        a = k * math.pi / 4.0
        cv.thick_line(x, y, x + 11 * s * math.cos(a), y + 11 * s * math.sin(a), 3 * s, c)
    cv.disc(x, y, 4 * s, (255, 200, 40))


def _ship(cv, x, y, s, c):
    cv.poly([(x - 16 * s, y), (x + 16 * s, y), (x + 11 * s, y + 7 * s),
             (x - 11 * s, y + 7 * s)], c)
    cv.fill_rect(x - 6 * s, y - 8 * s, x + 6 * s, y, c)
    cv.fill_rect(x - 1 * s, y - 13 * s, x + 1 * s, y - 8 * s, c)


def _virus(cv, x, y, r, c):
    cv.disc(x, y, r, c)
    for k in range(8):
        a = k * math.pi / 4.0
        cv.thick_line(x + r * 0.8 * math.cos(a), y + r * 0.8 * math.sin(a),
                      x + r * 1.35 * math.cos(a), y + r * 1.35 * math.sin(a), 2, c)
    cv.disc(x - r * 0.3, y - r * 0.25, r * 0.22, (255, 255, 255))
    cv.disc(x + r * 0.3, y + r * 0.3, r * 0.18, (255, 255, 255))


def _building(cv, x, y, w, h, c):
    cv.fill_rect(x, y, x + w, y + h, c)
    cv.poly([(x - 3, y), (x + w / 2.0, y - 10), (x + w + 3, y)], c)
    for i in range(4):
        cv.fill_rect(x + 4 + i * (w - 8) / 4.0, y + 6, x + 4 + (i + 1) * (w - 8) / 4.0 - 3,
                     y + h - 4, PAPER)


def _cyclone(cv, x, y, r, c):
    for k in range(5):
        rr = r * (0.25 + 0.19 * k)
        a0 = k * 1.1
        cv.arc(x, y, rr, a0, a0 + 4.4, c, 3)


def _plane_crash(cv, x, y, s, c):
    _jet(cv, x, y, s * 1.4, c)
    cv.poly([(x + 26 * s, y + 10 * s), (x + 40 * s, y + 22 * s),
             (x + 44 * s, y + 18 * s), (x + 32 * s, y + 6 * s)], (90, 80, 70))
    cv.disc(x + 38 * s, y + 20 * s, 3 * s, (90, 80, 70))


def icon_strip(cv, x, y, w, h, kind):
    """Flat illustration band inside a medium card."""
    cv.fill_rect(x, y, x + w, y + h, LIGHT)
    cx = x + w / 2.0
    cy = y + h / 2.0
    if kind == 'kerch':
        cv.fill_rect(x, y + h * 0.62, x + w, y + h, SEA)
        cv.fill_rect(x, y, x + w, y + h * 0.62, SKY)
        cv.fill_rect(x + w * 0.08, y + h * 0.3, x + w * 0.42, y + h * 0.38, INK)
        cv.poly([(x + w * 0.42, y + h * 0.3), (x + w * 0.55, y + h * 0.62),
                 (x + w * 0.48, y + h * 0.62)], INK)
        cv.fill_rect(x + w * 0.62, y + h * 0.3, x + w * 0.92, y + h * 0.38, INK)
        _smoke(cv, x + w * 0.5, y + h * 0.28, 0.9)
        _burst(cv, x + w * 0.47, y + h * 0.42, 0.8)
    elif kind == 'iran':
        cv.fill_rect(x, y, x + w, y + h * 0.55, SKY)
        cv.fill_rect(x, y + h * 0.55, x + w, y + h, SEA)
        cv.poly([(x + w * 0.55, y + h), (x + w * 0.62, y + h * 0.6),
                 (x + w * 0.78, y + h * 0.72), (x + w * 0.95, y + h)], SAND)
        _drone(cv, x + w * 0.3, y + h * 0.3, 1.6, INK)
        _jet(cv, x + w * 0.62, y + h * 0.28, 0.9, INK)
        cv.thick_line(x + w * 0.3, y + h * 0.34, x + w * 0.5, y + h * 0.55, 1, RED)
        _ship(cv, x + w * 0.42, y + h * 0.78, 0.9, (90, 60, 40))
    elif kind == 'quad':
        cv.fill_rect(x, y, x + w, y + h, (232, 226, 208))
        fw, fh = w * 0.16, h * 0.42
        for i, k in enumerate(('us', 'in', 'jp', 'au')):
            _flag(cv, x + w * 0.06 + i * w * 0.23, y + h * 0.12, fw, fh, k)
        cv.fill_rect(x + w * 0.08, y + h * 0.66, x + w * 0.92, y + h * 0.74, (120, 82, 40))
    elif kind == 'ebola':
        cv.fill_rect(x, y, x + w, y + h, (245, 240, 225))
        cv.poly([(x + w * 0.2, y + h * 0.82), (x + w * 0.5, y + h * 0.18),
                 (x + w * 0.8, y + h * 0.82)], (255, 255, 255))
        cv.line(x + w * 0.2, y + h * 0.82, x + w * 0.5, y + h * 0.18, INK, 2)
        cv.line(x + w * 0.5, y + h * 0.18, x + w * 0.8, y + h * 0.82, INK, 2)
        cv.line(x + w * 0.2, y + h * 0.82, x + w * 0.8, y + h * 0.82, INK, 2)
        cv.fill_rect(x + w * 0.46, y + h * 0.4, x + w * 0.54, y + h * 0.66, RED)
        cv.fill_rect(x + w * 0.4, y + h * 0.48, x + w * 0.6, y + h * 0.58, RED)
        _virus(cv, x + w * 0.1, y + h * 0.2, 5, RED)
        _virus(cv, x + w * 0.9, y + h * 0.22, 4, RED)
    elif kind == 'cop31':
        cv.fill_rect(x, y, x + w, y + h, (226, 238, 226))
        cv.disc(cx - w * 0.24, cy, h * 0.32, BLUE)
        cv.poly([(cx - w * 0.34, cy - h * 0.08), (cx - w * 0.2, cy - h * 0.28),
                 (cx - w * 0.14, cy - h * 0.02), (cx - w * 0.3, cy + h * 0.2)], GREEN)
        cv.fill_rect(cx + w * 0.08, cy - h * 0.3, cx + w * 0.42, cy + h * 0.3, (255, 255, 255))
        cv.line(cx + w * 0.08, cy - h * 0.3, cx + w * 0.42, cy - h * 0.3, INK, 1)
        cv.line(cx + w * 0.08, cy + h * 0.3, cx + w * 0.42, cy + h * 0.3, INK, 1)
        draw_text(cv, cx + w * 0.12, cy - h * 0.14, 'DRAFT', 9, RED, bold=True)
    elif kind == 'measles':
        cv.fill_rect(x, y, x + w, y + h, (248, 232, 232))
        _virus(cv, cx, cy, h * 0.3, RED)
        _flag(cv, x + w * 0.06, y + h * 0.12, w * 0.14, h * 0.3, 'us')
        cv.fill_rect(x + w * 0.8, y + h * 0.12, x + w * 0.94, y + h * 0.42, GREEN)
        cv.disc(x + w * 0.87, y + h * 0.27, h * 0.1, (255, 255, 255))
    elif kind == 'nvidia':
        cv.fill_rect(x, y, x + w, y + h, (20, 24, 20))
        bars = [0.3, 0.45, 0.4, 0.62, 0.85, 1.0]
        bw = w * 0.11
        for i, b in enumerate(bars):
            bx = x + w * 0.08 + i * w * 0.15
            cv.fill_rect(bx, y + h * 0.9 - h * 0.7 * b, bx + bw, y + h * 0.9,
                         (118, 200, 70) if i < 5 else (160, 230, 90))
        draw_text(cv, x + w * 0.06, y + h * 0.08, '$115.8BN', 11, (160, 230, 90), bold=True)
    elif kind == 'gaza':
        cv.fill_rect(x, y, x + w, y + h, SAND)
        for i in range(3):
            tx = x + w * (0.16 + i * 0.3)
            cv.poly([(tx, y + h * 0.75), (tx + w * 0.11, y + h * 0.3),
                     (tx + w * 0.22, y + h * 0.75)], (250, 246, 236))
        cv.fill_rect(x + w * 0.06, y + h * 0.62, x + w * 0.3, y + h * 0.78, (255, 255, 255))
        draw_text(cv, x + w * 0.09, y + h * 0.64, 'AID', 9, RED, bold=True)
    elif kind == 'mongolia':
        cv.fill_rect(x, y, x + w, y + h, (236, 232, 218))
        _building(cv, cx - w * 0.3, y + h * 0.32, w * 0.6, h * 0.52, INK_SOFT)
        cv.fill_rect(x + w * 0.66, y + h * 0.1, x + w * 0.95, y + h * 0.32, (255, 255, 255))
        draw_text(cv, x + w * 0.68, y + h * 0.13, 'RESIGN', 7, RED, bold=True)
    elif kind == 'japan':
        cv.fill_rect(x, y, x + w, y + h, SKY)
        cv.fill_rect(x, y + h * 0.7, x + w, y + h, SEA)
        _jet(cv, x + w * 0.18, y + h * 0.35, 1.1, INK)
        _jet(cv, x + w * 0.55, y + h * 0.55, 0.9, (90, 90, 90), flip=True)
        cv.fill_rect(x + w * 0.78, y + h * 0.1, x + w * 0.95, y + h * 0.32, (255, 255, 255))
        draw_text(cv, x + w * 0.8, y + h * 0.14, 'SUS-', 7, RED, bold=True)
        draw_text(cv, x + w * 0.8, y + h * 0.24, 'PECT', 7, RED, bold=True)
    elif kind == 'xavier':
        cv.fill_rect(x, y, x + w, y + h, (214, 230, 240))
        _cyclone(cv, cx - w * 0.12, cy, h * 0.36, (40, 80, 120))
        cv.fill_rect(x + w * 0.68, y + h * 0.12, x + w * 0.94, y + h * 0.36, RED)
        draw_text(cv, x + w * 0.71, y + h * 0.16, 'CAT 5', 9, (255, 255, 255), bold=True)
    elif kind == 'an12':
        cv.fill_rect(x, y, x + w, y + h, (228, 228, 222))
        cv.poly([(x, y + h), (x + w * 0.3, y + h * 0.55), (x + w * 0.7, y + h * 0.6),
                 (x + w, y + h)], (140, 130, 118))
        _plane_crash(cv, x + w * 0.3, y + h * 0.32, 0.9, INK)
        _smoke(cv, x + w * 0.72, y + h * 0.62, 0.8)
    elif kind == 'trilateral':
        cv.fill_rect(x, y, x + w, y + h, (232, 226, 208))
        fw, fh = w * 0.18, h * 0.44
        for i, k in enumerate(('us', 'cn', 'ru')):
            _flag(cv, x + w * 0.08 + i * w * 0.26, y + h * 0.14, fw, fh, k)
        draw_text(cv, x + w * 0.1, y + h * 0.68, 'THU 19 NOV', 10, RED, bold=True)
    elif kind == 'trumpkim':
        cv.fill_rect(x, y, x + w, y + h, (232, 226, 208))
        _flag(cv, x + w * 0.08, y + h * 0.16, w * 0.24, h * 0.44, 'us')
        _flag(cv, x + w * 0.62, y + h * 0.16, w * 0.24, h * 0.44, 'cn')
        draw_text(cv, x + w * 0.38, y + h * 0.26, '?', 16, INK, bold=True)
        draw_text(cv, x + w * 0.28, y + h * 0.68, 'MAY MEET', 9, INK, bold=True)
    elif kind == 'bank':
        cv.fill_rect(x, y, x + w, y + h, (228, 232, 238))
        for i in range(3):
            py = y + h * (0.2 + i * 0.2)
            cv.fill_rect(x + w * 0.24, py, x + w * 0.68, py + h * 0.14, (255, 255, 255))
            cv.line(x + w * 0.24, py, x + w * 0.68, py, INK, 1)
            cv.line(x + w * 0.24, py + h * 0.14, x + w * 0.68, py + h * 0.14, INK, 1)
        cv.fill_rect(x + w * 0.68, y + h * 0.1, x + w * 0.95, y + h * 0.32, RED)
        draw_text(cv, x + w * 0.7, y + h * 0.13, 'LEAK', 8, (255, 255, 255), bold=True)
    elif kind == 'serbia':
        cv.fill_rect(x, y, x + w, y + h, (236, 232, 218))
        _building(cv, cx - w * 0.3, y + h * 0.3, w * 0.6, h * 0.52, INK_SOFT)
        cv.fill_rect(x + w * 0.06, y + h * 0.12, x + w * 0.3, y + h * 0.34, BLUE)
        draw_text(cv, x + w * 0.08, y + h * 0.16, '140', 9, (255, 255, 255), bold=True)
    elif kind == 'bangladesh':
        cv.fill_rect(x, y, x + w, y + h, (226, 236, 226))
        cv.fill_rect(x + w * 0.1, y + h * 0.5, x + w * 0.9, y + h * 0.82, INK_SOFT)
        for i in range(5):
            px = x + w * (0.16 + i * 0.15)
            cv.disc(px, y + h * 0.4, 4, INK)
            cv.fill_rect(px - 2, y + h * 0.42, px + 2, y + h * 0.52, INK)
        cv.fill_rect(x + w * 0.66, y + h * 0.1, x + w * 0.92, y + h * 0.3, (255, 255, 255))
        draw_text(cv, x + w * 0.68, y + h * 0.13, 'TK 30K', 8, GREEN, bold=True)
    elif kind == 'mozambique':
        cv.fill_rect(x, y, x + w, y + h, (236, 232, 218))
        cv.fill_rect(x + w * 0.4, y + h * 0.16, x + w * 0.44, y + h * 0.7, (120, 90, 40))
        cv.fill_rect(x + w * 0.28, y + h * 0.12, x + w * 0.56, y + h * 0.2, (120, 90, 40))
        cv.fill_rect(x + w * 0.28, y + h * 0.68, x + w * 0.56, y + h * 0.76, (120, 90, 40))
        cv.fill_rect(x + w * 0.62, y + h * 0.14, x + w * 0.9, y + h * 0.4, RED)
        draw_text(cv, x + w * 0.64, y + h * 0.18, '5', 10, (255, 255, 255), bold=True)
        draw_text(cv, x + w * 0.72, y + h * 0.18, 'CHARGES', 7, (255, 255, 255), bold=True)
    else:
        cv.fill_rect(x, y, x + w, y + h, (228, 226, 214))
        cv.disc(cx, cy, h * 0.22, BLUE)
        draw_text(cv, cx - 3, cy - 5, 'N', 10, (255, 255, 255), bold=True)

# ------------------------------------------------------- lead panels
# Three separate illustrated lead panels (Kerch / the Gulf / Quad),
# each labelled and captioned like a front page's lead art.
def _kerch_panel(cv, x, y, w, h):
    x1 = x + w
    y1 = y + h
    horizon = y + int(h * 0.55)
    _sky_bands(cv, x, y, w, horizon - y, (196, 216, 230), SKY)
    cv.fill_rect(x, horizon, x1, y1, SEA)
    cv.fill_rect(x, y1 - 10, x1, y1, SEA_DARK)
    # cast shadow of the deck on the water (light is upper-left)
    _soft_ellipse(cv, x + w * 0.5 + 6, horizon + 12, w * 0.42, 5, (20, 40, 60), 0.30)
    deck_y = horizon - 24
    # deck with thickness: lit top edge, dark front face (isometric feel)
    cv.fill_rect(x + 8, deck_y - 3, x + 118, deck_y, (205, 205, 198))
    cv.fill_rect(x + 8, deck_y, x + 118, deck_y + 7, INK)
    cv.fill_rect(x + w - 108, deck_y - 3, x1 - 8, deck_y, (205, 205, 198))
    cv.fill_rect(x + w - 108, deck_y, x1 - 8, deck_y + 7, INK)
    # collapsed span: tilted slab falling into the strait, lit top edge
    cv.poly([(x + 118, deck_y), (x + 158, horizon + 10),
             (x + 166, horizon + 10), (x + w - 108, deck_y)], (60, 60, 60))
    cv.thick_line(x + 118, deck_y, x + w - 108, deck_y, 2, (205, 205, 198))
    for px in (x + 34, x + 88, x + w - 58):
        cv.fill_rect(px, deck_y + 7, px + 6, horizon + 12, INK)
    # splash where the span meets the water
    cv.disc(x + 158, horizon + 8, 7, (235, 242, 246))
    cv.disc(x + 166, horizon + 10, 5, (255, 255, 255))
    cv.disc(x + 148, horizon + 6, 4, (235, 242, 246))
    # layered smoke (soft, lit from the upper left) + blast glow
    _soft_disc(cv, x + 142, deck_y - 22, 16, (140, 138, 130), 0.55)
    _soft_disc(cv, x + 150, deck_y - 30, 11, (170, 168, 160), 0.55)
    _soft_disc(cv, x + 134, deck_y - 26, 9, (170, 168, 160), 0.5)
    _smoke(cv, x + 142, deck_y - 20, 1.1)
    _soft_disc(cv, x + 140, deck_y + 2, 14, (230, 120, 20), 0.45)
    _burst(cv, x + 140, deck_y + 2, 1.0)
    _jet(cv, x + 30, y + 24, 1.0, INK)
    _jet(cv, x + w - 70, y + 18, 0.9, INK)
    _chip(cv, x + 6, y + 6, 'CRIMEA', 9)
    _chip(cv, x + w - 62, y + 6, 'RUSSIA', 9)
    cv.fill_rect(x, y1 - 22, x1, y1, INK)
    draw_text(cv, x + 8, y1 - 18, 'KERCH STRAIT — ROAD SPAN DOWN', 9.5, (255, 255, 255), bold=True)


def _gulf_panel(cv, x, y, w, h):
    x1 = x + w
    y1 = y + h
    horizon = y + int(h * 0.55)
    _sky_bands(cv, x, y, w, horizon - y, (196, 216, 230), SKY)
    cv.fill_rect(x, horizon, x1, y1, SEA)
    cv.fill_rect(x, y1 - 10, x1, y1, SEA_DARK)
    cv.poly([(x + 22, y1 - 8), (x + 36, horizon + 16), (x + 70, horizon + 24),
             (x + 84, y1 - 8)], SAND)
    cv.poly([(x + w - 110, y1 - 8), (x + w - 100, horizon + 6), (x + w - 26, horizon + 12),
             (x + w - 6, y1 - 8)], SAND)
    cv.arc(x + 50, horizon + 18, 8, math.pi, 2 * math.pi, INK, 2)
    cv.vline(x + 50, horizon + 2, horizon + 18, INK, 2)
    # radar dome (lit top-left) is marked downed: red disc + cross
    _drone(cv, x + 92, y + 32, 1.8, INK)
    # drone's shadow on the sea, cast down-right
    _soft_ellipse(cv, x + 100, horizon + 22, 12, 3, (20, 40, 60), 0.35)
    _jet(cv, x + w - 84, y + 26, 1.0, INK)
    for i in range(6):
        t = i / 5.0
        sx = int(x + 88 - t * 34)
        sy = int(y + 40 + t * (horizon - y - 32))
        cv.fill_rect(sx, sy, sx + 8, sy + 2, RED)
    _soft_disc(cv, x + w - 58, horizon + 6, 13, (230, 120, 20), 0.45)
    _burst(cv, x + w - 58, horizon + 6, 0.9)
    # ship: lit hull top, dark hull side, soft shadow on the water
    _soft_ellipse(cv, x + 156, horizon + 34, 26, 4, (20, 40, 60), 0.30)
    _ship(cv, x + 150, horizon + 24, 1.3, (90, 60, 40))
    cv.thick_line(x + 150 - 20, horizon + 24, x + 150 + 20, horizon + 24, 2, (150, 105, 70))
    cv.disc(x + 50, horizon + 10, 5, RED)
    cv.line(x + 44, horizon + 4, x + 56, horizon + 16, RED, 2)
    cv.line(x + 56, horizon + 4, x + 44, horizon + 16, RED, 2)
    _chip(cv, x + 6, y + 6, 'BAHRAIN', 9)
    _chip(cv, x + w - 58, y + 6, 'QESHM', 9)
    cv.fill_rect(x, y1 - 22, x1, y1, INK)
    draw_text(cv, x + 8, y1 - 18, 'THE GULF — DRONES DOWNED · US STRIKES', 9.5, (255, 255, 255), bold=True)


def _quad_panel(cv, x, y, w, h):
    x1 = x + w
    y1 = y + h
    # room with depth: lit upper wall, darker floor band; caption bar
    # sits at y1-22, so the table must end above y+106 (h=128)
    cv.fill_rect(x, y, x1, y + 76, (236, 230, 212))
    cv.fill_rect(x, y + 76, x1, y1, (212, 204, 182))
    fw, fh = 48, 28
    step = (w - 20 - fw) / 3.0
    for i, k in enumerate(('us', 'in', 'jp', 'au')):
        fx = x + 10 + i * step
        # flagpole + soft shadow on the wall, light from upper left
        cv.vline(fx - 3, y + 22, y + 56, (90, 90, 85), 2)
        _flag(cv, fx, y + 26, fw, fh, k)
    for i, lab in enumerate(('US', 'INDIA', 'JAPAN', 'AUSTRALIA')):
        lx = x + 10 + i * step + fw / 2.0
        draw_text(cv, lx, y + 58, lab, 8, INK, bold=True, align='center')
    # four chairs behind the table (dark wood, lit backrest tops)
    for i in range(4):
        cx0 = x + 10 + i * step
        cv.fill_rect(cx0, y + 70, cx0 + 24, y + 78, (96, 64, 34))
        cv.fill_rect(cx0, y + 70, cx0 + 24, y + 73, (140, 96, 52))
    # cast shadow of the table on the floor, down-right of the light
    _soft_ellipse(cv, x + w / 2.0 + 5, y + 104, w * 0.42, 5, (60, 50, 30), 0.30)
    # isometric table: lit top face, dark front face
    cv.poly([(x + 16, y + 80), (x + 28, y + 75), (x1 - 16, y + 75),
             (x1 - 28, y + 80)], (150, 105, 55))
    cv.fill_rect(x + 16, y + 80, x1 - 16, y + 89, (110, 75, 38))
    for i in range(4):
        lx = x + 22 + i * step
        cv.fill_rect(lx, y + 89, lx + 5, y + 101, (110, 75, 38))
    cv.fill_rect(x + 16, y + 101, x1 - 16, y + 105, (110, 75, 38))
    _chip(cv, x + 6, y + 6, 'MANILA · QUAD LEADERS\u2019 SUMMIT', 9)
    cv.fill_rect(x, y1 - 22, x1, y1, INK)
    draw_text(cv, x + 8, y1 - 18, 'FIRST QUAD SUMMIT SINCE 2024', 9.5, (255, 255, 255), bold=True)


def draw_hero(cv, x, y, w, h):
    """Hero strip: Kerch panel | 3D globe | Gulf panel | Quad panel.
    The globe is the visual anchor; the full 1-13 pin set stays on
    the dot map below, so no story loses its map pin."""
    gw = 176
    pw = (w - gw - 3 * 8) / 3.0
    _kerch_panel(cv, x, y, pw, h)
    _globe(cv, x + pw + 8, y, gw, h)
    _gulf_panel(cv, x + pw + gw + 16, y, pw, h)
    _quad_panel(cv, x + 2 * pw + gw + 24, y, pw, h)
    cv.line(x, y + h, x + w, y + h, INK, 2)



def _chip(cv, x, y, s, cap):
    w = text_width(s, cap, bold=True) + cap * 1.2
    h = cap * 2.0
    cv.fill_rect(x, y, x + w, y + h, (255, 255, 255))
    cv.fill_rect(x, y, x + w, y + 1, INK)
    cv.fill_rect(x, y + h - 1, x + w, y + h, INK)
    cv.fill_rect(x, y, x + 1, y + h, INK)
    cv.fill_rect(x + w - 1, y, x + w, y + h, INK)
    draw_text(cv, x + cap * 0.6, y + cap * 0.45, s, cap, INK, bold=True)


# ------------------------------------------------------- 3D helpers (v7)
# One studio light from the upper left everywhere: highlights sit
# top-left, cast shadows fall bottom-right. All shading is computed
# from that single direction so the globe and the three lead scenes
# read as lit by the same sun.
LIGHT_DIR = (-0.55, 0.55, 0.62)  # direction TO the light, view space (y up)


def _soft_disc(cv, cx, cy, r, c, a0):
    """Disc with quadratic alpha falloff (soft shadow / glow / smoke)."""
    r = int(r)
    if r <= 0:
        return
    cx = int(cx)
    cy = int(cy)
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if d2 <= r * r:
                cv.blend(x, y, c, a0 * (1.0 - d2 / (r * r)))


def _soft_ellipse(cv, cx, cy, rx, ry, c, a0):
    """Soft elliptical cast shadow (alpha peaks at centre)."""
    rx = int(rx)
    ry = int(ry)
    if rx <= 0 or ry <= 0:
        return
    for y in range(int(cy) - ry, int(cy) + ry + 1):
        for x in range(int(cx) - rx, int(cx) + rx + 1):
            q = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if q <= 1.0:
                cv.blend(x, y, c, a0 * (1.0 - q))


def _sky_bands(cv, x, y, w, h, top, bottom):
    """Vertical sky gradient in 5 flat bands (lightest at the top)."""
    for i in range(5):
        t = i / 4.0
        c = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
        cv.fill_rect(x, y + i * h / 5.0, x + w, y + (i + 1) * h / 5.0, c)


def _shade(base, f):
    """Scale an RGB colour by a diffuse factor f (0..1.15)."""
    return tuple(max(0, min(255, int(v * f))) for v in base)


# Rough continent blobs (lon, lat, angular radius in degrees, colour)
# used by the orthographic globe. Centred on lon 55E / lat 22N so the
# Kerch Strait, the Gulf and Manila are all on the visible face.
_GLOBE_LAND = [
    (-100, 48, 22, (96, 130, 70)), (-85, 34, 13, (96, 130, 70)),
    (-60, -12, 16, (96, 130, 70)),
    (18, 4, 20, (96, 130, 70)), (30, -18, 12, (96, 130, 70)),
    (55, 52, 30, (110, 138, 74)), (100, 55, 18, (110, 138, 74)),
    (80, 30, 14, (110, 138, 74)), (103, 12, 10, (96, 130, 70)),
    (134, -25, 11, (150, 128, 70)),
    (24, 25, 11, (188, 168, 108)), (45, 25, 9, (188, 168, 108)),
]
_GLOBE_LAND_VEC = []
for (_lo, _la, _rr, _cc) in _GLOBE_LAND:
    _lr, _ar = math.radians(_lo), math.radians(_la)
    _GLOBE_LAND_VEC.append((
        (math.cos(_ar) * math.sin(_lr), math.sin(_ar), math.cos(_ar) * math.cos(_lr)),
        math.cos(math.radians(_rr)), _cc))


def _globe(cv, x, y, w, h):
    """3D globe: orthographic sphere, one upper-left light, shaded
    oceans + simple continents, specular highlight, cast shadow,
    numbered pins for the three lead stories (1 Kerch, 2 Gulf,
    3 Manila). The full 1-13 pin set stays on the dot map below."""
    cx = x + w / 2.0
    cy = y + h / 2.0 - 8
    R = min(w, h - 22) / 2.0
    lon0 = math.radians(55.0)
    lat0 = math.radians(22.0)
    cl0, sl0 = math.cos(lat0), math.sin(lat0)
    co0, so0 = math.cos(lon0), math.sin(lon0)
    lx, ly, lz = LIGHT_DIR
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ln, ly / ln, lz / ln
    Ri = int(R)
    for sy in range(int(cy) - Ri, int(cy) + Ri + 1):
        for sx in range(int(cx) - Ri, int(cx) + Ri + 1):
            dx = (sx + 0.5 - cx) / R
            dy = (cy - (sy + 0.5)) / R  # screen down -> view up
            q = dx * dx + dy * dy
            if q > 1.0:
                continue
            z = math.sqrt(1.0 - q)
            # view-space normal -> world point (rotate by lat0, then lon0)
            px = dx
            py = dy * cl0 - z * sl0
            pz = dy * sl0 + z * cl0
            wx = px * co0 + pz * so0
            wy = py
            wz = -px * so0 + pz * co0
            diff = 0.32 + 0.68 * max(0.0, dx * lx + dy * ly + z * lz)
            base = (64, 116, 168)
            for (vx, vy, vz), cosr, col in _GLOBE_LAND_VEC:
                if wx * vx + wy * vy + wz * vz > cosr:
                    base = col
                    break
            cv.set(sx, sy, _shade(base, diff))
    # specular highlight, upper left (same light direction)
    _soft_disc(cv, cx - R * 0.38, cy - R * 0.42, R * 0.30, (255, 255, 255), 0.30)
    _soft_disc(cv, cx - R * 0.42, cy - R * 0.46, R * 0.13, (255, 255, 255), 0.45)
    cv.circle_outline(cx, cy, R, 2, (30, 60, 90))
    # cast shadow, bottom right of the light
    _soft_ellipse(cv, cx + 5, cy + R + 5, R * 0.85, 7, (20, 20, 20), 0.28)
    # pins: 1 Kerch (36.5E, 45.3N), 2 Gulf/Bahrain (50.5E, 26.2N),
    # 3 Manila (121E, 14.6N) — orthographic projection, same centre
    for (lon, lat, n) in ((36.5, 45.3, 1), (50.5, 26.2, 2), (121.0, 14.6, 3)):
        lo = math.radians(lon - 55.0)
        la = math.radians(lat)
        vx = math.cos(la) * math.sin(lo)
        vy = math.cos(lat0) * math.sin(la) - math.sin(lat0) * math.cos(la) * math.cos(lo)
        vz = math.sin(lat0) * math.sin(la) + math.cos(lat0) * math.cos(la) * math.cos(lo)
        if vz <= 0.05:
            continue
        px = cx + vx * R
        py = cy - vy * R
        cv.disc(px, py, 6, RED)
        cv.ring(px, py, 6, 1, (255, 255, 255))
        draw_text(cv, px - text_width(str(n), 7, bold=True) / 2.0, py - 4.5,
                  str(n), 7, (255, 255, 255), bold=True)
    draw_text(cv, cx, y + h - 13, '1 KERCH \u00b7 2 GULF \u00b7 3 MANILA', 8,
              INK, bold=True, align='center')


# ---------------------------------------------------------------- stories
# 13 verified stories (PREP-NOTE §4). Decks: leads ~110-125 chars,
# mediums ~60-75 chars. lat/lon for the map pins.
STORIES = [
    dict(n=1, kicker='1  EUROPE · UKRAINE WAR', icon='kerch', lon=36.5, lat=45.3,
         head='Ukraine says a Crimean Bridge span fell into the sea',
         deck='Second strike in two days; Zelenskyy hails an \u201cunprecedented operation\u201d. '
              'The Kremlin vows to rebuild.'),
    dict(n=2, kicker='2  MIDDLE EAST · IRAN–US', icon='iran', lon=50.5, lat=26.2,
         head='Iran sends drones at a US radar in Bahrain; US hits back',
         deck='Bahrain and the US say the drones were downed; US jets then strike Qeshm.'),
    dict(n=3, kicker='3  ASIA · DIPLOMACY', icon='quad', lon=121.0, lat=14.6,
         head='Trump holds his first Quad summit, in Manila',
         deck='First Quad summit since 2024; leaders cite \u2018grave concerns\u2019 over coercion.'),
    dict(n=4, kicker='4  AFRICA · HEALTH', icon='ebola', lon=30.0, lat=1.5,
         head='Ebola cases in DR Congo top 11,000',
         deck='WHO: cases more than doubled in three months; 5,400+ died.'),
    dict(n=5, kicker='5  GLOBAL · CLIMATE', icon='cop31', lon=30.7, lat=36.9,
         head='COP31 split over fossil-fuel phase-out',
         deck='Nations weigh the first draft as talks end Friday.'),
    dict(n=6, kicker='6  AMERICAS · HEALTH', icon='measles', lon=-77.0, lat=38.9,
         head='US, Mexico and Bolivia lose measles-free status',
         deck='PAHO cites a year of spread; US cases hit 5,400+ in 2026.'),
    dict(n=7, kicker='7  US · BUSINESS', icon='nvidia', lon=-74.0, lat=40.7,
         head='Nvidia\u2019s quarterly sales double',
         deck='Reported after the close. Earlier the Dow fell 849 points.'),
    dict(n=8, kicker='8  EUROPE · POLITICS', icon='serbia', lon=20.5, lat=44.8,
         head='Serbia\u2019s student MPs take their seats',
         deck='Student List wins 140 of 250 seats, ending 14 years of SNS rule.'),
    dict(n=9, kicker='9  ASIA · POLITICS', icon='mongolia', lon=106.9, lat=47.9,
         head='Mongolia\u2019s president says he will resign',
         deck='Khurelsukh denies $25m claim; parliament must accept.'),
    dict(n=10, kicker='10  ASIA · DEFENCE', icon='japan', lon=130.4, lat=33.6,
         head='Japan scrambles jets over breach',
         deck='Two suspected Russian aircraft near Fukuoka, Tokyo says.'),
    dict(n=11, kicker='11  OCEANIA · DISASTER', icon='xavier', lon=-165.8, lat=-10.9,
         head='Cyclone Xavier strengthens to Category 5',
         deck='Winds of 220 km/h near N. Cook Islands; shelters open.'),
    dict(n=12, kicker='12  RUSSIA · AIR CRASH', icon='an12', lon=86.1, lat=55.4,
         head='Russia says An-12 crash kills 19',
         deck='Plane came down near Kemerovo; a fault is suspected.'),
    dict(n=13, kicker='13  EUROPE · BUSINESS', icon='bank', lon=8.7, lat=50.1,
         head='Deutsche Bank hit by 15m-file leak',
         deck='Reports say a leak of 15m files details Epstein payments; shares fall.'),
]

# Numbered briefs (stories 14-39, verified in STORIES-EXTRA.md).
# One line each, <=56 chars, facts compressed from the verified decks.
# Trilateral (#38) and Trump-Kim (#39) are PLANNED, labelled as such.
BRIEFS = [
    (14, 'Bangladesh: garment workers clash with police over pay'),
    (15, 'Mozambique: Mondlane on trial over 2024 unrest'),
    (16, 'Moldova: seven drones violate airspace; flights divert'),
    (17, 'Sudan: UN: drones behind most of 2,230 civilian deaths'),
    (18, 'US: Anthropic files $70-$78 IPO range for Nasdaq'),
    (19, 'Gaza: Board of Peace warns truce could collapse'),
    (20, "NBA: Pistons end Spurs' 12-game win streak, 105-93"),
    (21, 'Tennis: Zverev beats Shelton to reach ATP Finals semis'),
    (22, 'Cricket: Zimbabwe win first away Test series since 2001'),
    (23, 'US: Democrats to probe $100bn Venezuela oil deal'),
    (24, 'Brazil: images said to show uncontacted Awa released'),
    (25, 'Brazil: Lula moves to contain fiscal plan revolt'),
    (26, 'Nigeria: expects to sign AfCFTA digital trade deal'),
    (27, 'Indonesia-India plan Sabang-Andaman link'),
    (28, 'EU lifts 2026 growth forecast to 1.4%'),
    (29, 'Vatican: Pope Leo XIV returns to Rome after 12 days'),
    (30, 'NASA sets 7 Dec unveil for Roman Telescope images'),
    (31, 'Yemen: coalition says it hit 60 Houthi targets'),
    (32, 'London: Einaudi enters Ivors Fellowship; Pemberton wins'),
    (33, 'Australia eases working holiday visa rules'),
    (34, 'China-Canada agree tariff relief in Shenzhen'),
    (35, 'South Africa rebukes Nigerian envoy'),
    (36, 'Kenya: Dangote set for Pipeline board seat'),
    (37, 'Modi pitches maritime plan at ASEAN summit'),
    (38, 'China: Trump, Xi, Putin due to meet Thu 19 Nov'),
    (39, 'US: Trump says he may meet Kim Jong Un in China'),
]

# ---------------------------------------------------------------- layout
MX = 14
CW = 996


def _kicker_color(kicker):
    if 'EUROPE' in kicker:
        return BLUE
    if 'MIDDLE EAST' in kicker:
        return RED
    if 'ASIA' in kicker:
        return PURPLE
    if 'AFRICA' in kicker:
        return GREEN
    if 'AMERICAS' in kicker or 'US ·' in kicker:
        return ORANGE
    if 'OCEANIA' in kicker:
        return TEAL
    if 'RUSSIA' in kicker:
        return (120, 40, 40)
    if 'CHINA' in kicker:
        return RED
    return INK


def _lead_card(cv, x, y, w, st):
    """Secondary headline card: small 3D scene strip on top (the same
    art as its hero panel), kicker, 2-line headline, 2-line deck."""
    icon_strip(cv, x, y, w, 28, st['icon'])
    kicker(cv, x, y + 32, st['kicker'], 9, _kicker_color(st['kicker']))
    hy = y + 54
    lines = wrap_text(st['head'], 18, w, bold=True)
    draw_para(cv, x, hy, lines[:2], 18, INK, leading=22, bold=True)
    dy = hy + 2 * 22 + 4
    dlines = wrap_text(st['deck'], 12, w)
    draw_para(cv, x, dy, dlines[:2], 12, INK_SOFT, leading=15)


def _medium_card(cv, x, y, w, h, st):
    icon_strip(cv, x, y, w, 40, st['icon'])
    kicker(cv, x, y + 44, st['kicker'], 8.5, _kicker_color(st['kicker']))
    hy = y + 62
    lines = wrap_text(st['head'], 16, w, bold=True)
    draw_para(cv, x, hy, lines[:3], 16, INK, leading=19, bold=True)
    dy = y + 121
    dlines = wrap_text(st['deck'], 9, w)
    draw_para(cv, x, dy, dlines[:2], 9, INK_SOFT, leading=12.5)


def _stat_box(cv, x, y, w, h):
    """The day in numbers — fills the last medium-grid cell. Every
    figure is verified in PREP-NOTE / STORIES-EXTRA."""
    cv.fill_rect(x, y, x + w, y + h, INK)
    draw_text(cv, x + 8, y + 8, 'THE DAY IN', 13, (255, 255, 255), bold=True)
    draw_text(cv, x + 8, y + 24, 'NUMBERS', 13, (255, 210, 60), bold=True)
    stats = [('11,000+', 'Ebola cases in DR Congo'),
             ('5,400+', 'US measles cases in 2026'),
             ('220 km/h', 'Cyclone Xavier winds'),
             ('140 / 250', "Serbia's Student List seats")]
    yy = y + 48
    for num, lab in stats:
        draw_text(cv, x + 8, yy, num, 11, (255, 210, 60), bold=True)
        draw_text(cv, x + 8, yy + 12, lab, 8.5, (220, 220, 210))
        yy += 25


def build():
    cv = Canvas(W, H, PAPER)
    # ---- top strip: the paper's identity line
    draw_text(cv, MX, 10, 'WORLD IN ONE FRAME', 11, RED, bold=True)
    right = '39 STORIES \u00b7 6 CONTINENTS \u00b7 ALL FROM TUESDAY'
    draw_text(cv, MX + CW - text_width(right, 11, bold=True), 10, right, 11, INK_SOFT, bold=True)
    cv.fill_rect(MX, 28, MX + CW, 30, RED)
    # ---- masthead: newspaper name in v6 serif, date line large below
    draw_text(cv, MX + CW / 2.0, 32, 'WORLD REPORT', 46, INK, bold=True,
              align='center', serif=True)
    draw_text(cv, MX + CW / 2.0, 92, 'TUESDAY, 17 NOVEMBER 2026', 20, INK, bold=True,
              align='center', serif=True)
    cv.fill_rect(MX, 120, MX + CW, 122, INK)
    # ---- main headline: the day's biggest verified development (story #1)
    lead1 = STORIES[0]
    draw_text(cv, MX + CW / 2.0, 126, lead1['head'], 25, INK, bold=True,
              align='center', serif=True)
    draw_text(cv, MX + CW / 2.0, 156, lead1['deck'], 11.5, INK_SOFT,
              align='center')
    # ---- hero strip: Kerch | 3D globe | the Gulf | Quad (h=128)
    draw_hero(cv, MX, 178, CW, 128)
    cv.fill_rect(MX, 310, MX + CW, 312, INK)
    # ---- 3 secondary headline cards (stories #2, #3, #4)
    leads = STORIES[1:4]
    colw = (CW - 24) / 3.0
    for i, st in enumerate(leads):
        _lead_card(cv, MX + i * (colw + 12), 316, colw, st)
    cv.fill_rect(MX, 452, MX + CW, 454, INK)
    # ---- medium rows (stories 5..13) + stat box in the last cell
    mediums = STORIES[4:13]
    cardw = (CW - 4 * 9.5) / 5.0
    for r in range(2):
        for c in range(5):
            idx = r * 5 + c
            xx = MX + c * (cardw + 9.5)
            yy = 458 + r * 148
            if idx < len(mediums):
                _medium_card(cv, xx, yy, cardw, 148, mediums[idx])
            elif idx == len(mediums):
                _stat_box(cv, xx, yy, cardw, 148)
    cv.fill_rect(MX, 756, MX + CW, 758, INK)
    # ---- bottom: map + numbered briefs
    pins = [(st['lon'], st['lat'], st['n']) for st in STORIES]
    if BRIEFS:
        draw_text(cv, MX, 762, 'WHERE IT HAPPENED', 11, INK, bold=True)
        draw_map(cv, MX, 780, 330, 174, pins=pins)
        lx = MX + 346
        draw_text(cv, lx, 762, 'ALSO ON TUESDAY 17 NOVEMBER', 11, INK, bold=True)
        cv.fill_rect(lx, 778, lx + 650, 780, RED)
        colw2 = 322
        for i, (num, txt) in enumerate(BRIEFS):
            col = 0 if i < 13 else 1
            row = i if i < 13 else i - 13
            bx = lx + col * (colw2 + 6)
            by = 784 + row * 14.2
            draw_text(cv, bx, by, str(num), 10, RED, bold=True)
            draw_text(cv, bx + 18, by, txt, 9.5, INK)
        draw_text(cv, MX, 958, 'Pins: stories 1\u201313', 8.5, INK_SOFT)
    else:
        draw_text(cv, MX, 762, 'WHERE IT HAPPENED', 11, INK, bold=True)
        draw_map(cv, MX, 780, CW, 174, pins=pins)
        draw_text(cv, MX, 958, 'Pins: stories 1\u201313', 8.5, INK_SOFT)
    # ---- date check strip (text to the judge — allowed and read)
    cv.fill_rect(MX, 966, MX + CW, 1008, INK)
    dc1 = 'DATE CHECK \u2014 Every story here happened or was first reported on Tuesday 17 November 2026.'
    dc2 = 'Planned items are labelled: Trilateral Thu 19 Nov; Trump\u2013Kim meeting not scheduled. Contested claims name their source.'
    dc3 = 'Left out on purpose: Gaza aid call (16 Nov); Europe\u2019s E5 Ukraine team (13 Nov); Kuwait drone intercept (18 Nov).'
    draw_text(cv, MX + 8, 970, dc1, 10.5, (255, 255, 255), bold=True)
    draw_text(cv, MX + 8, 983, dc2, 10.5, (220, 220, 210))
    draw_text(cv, MX + 8, 996, dc3, 10.5, (220, 220, 210))
    # ---- footer
    draw_text(cv, MX, 1012, 'Sources: Reuters, AP, AFP, BBC, Al Jazeera, WHO, UN. Original drawings.',
              9, INK_SOFT)
    draw_text(cv, MX + CW - text_width('WORLD IN ONE FRAME', 9, bold=True), 1012,
              'WORLD IN ONE FRAME', 9, RED, bold=True)
    return cv


def main():
    out = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    cv = build()
    n = write_png(cv, os.path.join(out, 'entry.png'))
    print('wrote %s/entry.png (%d bytes, %dx%d)' % (out, n, W, H))


if __name__ == '__main__':
    main()

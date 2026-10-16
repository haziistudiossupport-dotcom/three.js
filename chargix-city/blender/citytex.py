"""Procedural, tileable PBR textures for the CHARGIX miniature city (numpy + PIL, no Blender needed).

Usage: python3 citytex.py            -> writes site/assets/cx-tex-*.webp
Every texture tiles seamlessly (noise is built in the frequency domain, patterns are periodic).
Albedo maps are sRGB; normal maps are OpenGL convention (+Y up), linear.
"""
import numpy as np
from PIL import Image
import os, math

OUT = '/home/claude/chargix-city/site/assets'
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20261015)


def fnoise(n, cutoff, seed=None, aniso=(1.0, 1.0)):
    """Tileable band-limited noise in [-1, 1]. cutoff = number of features across the tile."""
    r = np.random.default_rng(seed) if seed is not None else rng
    w = r.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None] * n * aniso[1]
    fx = np.fft.fftfreq(n)[None, :] * n * aniso[0]
    f = np.sqrt(fx ** 2 + fy ** 2)
    filt = np.exp(-(f / cutoff) ** 2)
    out = np.real(np.fft.ifft2(np.fft.fft2(w) * filt))
    out -= out.mean()
    return out / (np.abs(out).max() + 1e-9)


def fbm(n, base, octaves=5, gain=0.5, seed=0, aniso=(1.0, 1.0)):
    acc = np.zeros((n, n)); amp = 1.0; tot = 0
    for o in range(octaves):
        acc += amp * fnoise(n, base * 2 ** o, seed + o * 17, aniso)
        tot += amp; amp *= gain
    return acc / tot


def height_to_normal(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    nz = np.ones_like(h)
    nrm = np.stack([-dx, dy, nz], -1)  # image rows go down, so +dy flips for OpenGL
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return nrm * 0.5 + 0.5


def save(arr, name, q=86):
    a = np.clip(arr, 0, 1)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    img = Image.fromarray((a * 255 + 0.5).astype(np.uint8))
    img.save(f'{OUT}/cx-tex-{name}.webp', 'WEBP', quality=q, method=6)


def srgb(hexs):
    h = hexs.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def cells(n, cols, rows, stagger=0.5, joint=0.01, seed=0):
    """Running-bond blocks. Returns (block_id, joint_mask 0..1 soft, uv-within-block)."""
    yy, xx = np.mgrid[0:n, 0:n] / n
    row = np.floor(yy * rows)
    xo = xx * cols + (row % 2) * stagger
    col = np.floor(xo) % cols
    fx = xo - np.floor(xo); fy = yy * rows - row
    jx = joint * cols; jy = joint * rows
    edge = np.minimum(np.minimum(fx, 1 - fx) / jx, np.minimum(fy, 1 - fy) / jy)
    jm = np.clip(1 - edge, 0, 1)  # 1 at the joint centre
    bid = (row * 131 + col * 17).astype(int)
    return bid, jm, fx, fy


N = 1024

# ------------------------------------------------------------- plaster (2 m tile, tinted per building)
mott = fbm(N, 3, 5, 0.55, 1)
grain = fnoise(N, 220, 2)
streak = fbm(N, 6, 3, 0.5, 3, aniso=(1.0, 0.12))
alb = 0.86 + 0.05 * mott + 0.018 * grain - 0.03 * np.clip(streak, 0, 1)
save(alb, 'plaster-a')
h = 0.6 * fnoise(N, 140, 4) + 0.4 * fnoise(N, 60, 5) + 0.15 * mott
save(height_to_normal(h, 2.2), 'plaster-n', 92)

# ------------------------------------------------------------- cantera / rusticated base (2.4 m tile: 6 courses)
# Roma ground floors: deep horizontal V-grooves every 40 cm, faint vertical joints, warm weathered stone.
bid, jm, fx, fy = cells(N, 2, 6, 0.5, 0.004)
yy = (np.mgrid[0:N, 0:N][0] / N * 6) % 1
groove = np.clip(1 - np.minimum(yy, 1 - yy) / 0.035, 0, 1) ** 1.5          # horizontal channel
vjoint = np.clip(1 - np.minimum(fx, 1 - fx) / 0.006, 0, 1) * (1 - groove)  # hairline verticals
base = srgb('#c4ab9c')
vals = np.random.default_rng(7).uniform(-1, 1, (4000, 3))
v = vals[bid % 4000]
tint = base[None, None, :] * (1 + 0.035 * v[..., :1]) + np.array([0.01, -0.003, -0.008]) * v[..., 1:2]
pores = (fnoise(N, 380, 8) > 0.55).astype(float) * 0.2 + (fnoise(N, 200, 9) > 0.62) * 0.1
cloud = fbm(N, 10, 4, 0.5, 10)
dirt = np.clip(fbm(N, 5, 4, 0.55, 31, aniso=(1.0, 0.35)), 0, 1)
# grime collects on the lower lip of each groove
lip = np.clip(1 - (yy - 0.035) / 0.08, 0, 1) * (yy > 0.035)
alb = tint * (1 + 0.05 * cloud[..., None] - pores[..., None] * 0.5 - 0.1 * dirt[..., None]
              - 0.08 * lip[..., None]) * (1 - 0.5 * groove[..., None] - 0.18 * vjoint[..., None])
save(alb, 'cantera-a')
h = -groove * 1.2 - vjoint * 0.25 + 0.07 * fnoise(N, 260, 11) - pores * 0.12 + 0.05 * cloud
save(height_to_normal(h, 3.5), 'cantera-n', 92)

# ------------------------------------------------------------- sidewalk concrete (2.4 m tile, 2 x 2 poured panels)
# saw-cut joints, broom texture, a replaced panel, gum and water stains
bid, jm, fx, fy = cells(N, 2, 2, 0.0, 0.0022)
vals = np.random.default_rng(12).uniform(-1, 1, 4000)
v = vals[bid % 4000]
patch = (bid % 4 == 1).astype(float)
stain = np.clip(fbm(N, 5, 5, 0.6, 13), 0, 1)
agg = fnoise(N, 420, 14)
broom = fnoise(N, 260, 17, aniso=(0.08, 1.0))
gum = (fnoise(N, 90, 18) > 0.8).astype(float)
alb = srgb('#ada69a')[None, None, :] * (1 + 0.04 * v[..., None] + 0.05 * fbm(N, 8, 4, 0.5, 15)[..., None]
                                       - 0.16 * stain[..., None] + 0.035 * agg[..., None] + 0.02 * broom[..., None]
                                       + 0.07 * patch[..., None] - 0.25 * gum[..., None]) * (1 - 0.55 * jm[..., None])
alb = alb * np.array([1.0, 0.99, 0.965])[None, None, :]
save(alb, 'sidewalk-a')
h = -jm * 0.9 + 0.05 * agg + 0.04 * broom + 0.03 * fbm(N, 20, 3, 0.5, 16)
save(height_to_normal(h, 3.0), 'sidewalk-n', 92)

# ------------------------------------------------------------- asphalt (4 m tile)
agg = fnoise(N, 420, 21)
spk = (agg > 0.45).astype(float) * 0.5 + (agg < -0.55) * -0.3
wear = fbm(N, 3, 5, 0.55, 22)
crack = np.abs(fbm(N, 5, 4, 0.5, 23)) < 0.012
alb = 0.215 + 0.03 * wear + 0.05 * spk - 0.06 * crack
alb = np.stack([alb * 0.98, alb, alb * 1.03], -1)
save(alb, 'asphalt-a')
h = 0.5 * agg + 0.2 * wear - 0.8 * crack
save(height_to_normal(h, 2.0), 'asphalt-n', 92)

# ------------------------------------------------------------- roof coating (3 m tile, tinted: red elastomeric or grey)
alb = 0.8 + 0.06 * fbm(N, 4, 5, 0.6, 31) - 0.08 * np.clip(fbm(N, 7, 4, 0.5, 32), 0, 1) + 0.02 * fnoise(N, 300, 33)
seams = np.minimum(np.abs((np.mgrid[0:N, 0:N][1] / N * 3) % 1 - 0.5), 1) < 0.004
alb = alb - 0.06 * seams
save(alb, 'roof-a')
save(height_to_normal(0.4 * fnoise(N, 180, 34) + 0.4 * seams, 2.0), 'roof-n', 90)

# ------------------------------------------------------------- hydraulic "pasta" floor tiles (0.8 m tile, 4 x 4 tiles of 20 cm)
yy, xx = np.mgrid[0:N, 0:N] / N
tx = (xx * 4) % 1; ty = (yy * 4) % 1
cx, cy = tx - 0.5, ty - 0.5
r = np.sqrt(cx ** 2 + cy ** 2)
ang = np.arctan2(cy, cx)
petal = (np.abs(np.cos(ang * 2)) * 0.32 > r).astype(float)
ring = ((r > 0.36) & (r < 0.41)).astype(float)
corner = (np.minimum(np.minimum(tx, 1 - tx), np.minimum(ty, 1 - ty)) < 0.05).astype(float)
c_bg, c_a, c_b = srgb('#e6dccb'), srgb('#2f4a44'), srgb('#b5523b')
alb = c_bg * (1 - petal[..., None]) + c_a * petal[..., None]
alb = alb * (1 - ring[..., None]) + c_b * ring[..., None]
alb = alb * (1 - corner[..., None] * 0.9) + c_a * corner[..., None] * 0.9
grout = (np.minimum(np.minimum(tx, 1 - tx), np.minimum(ty, 1 - ty)) < 0.006).astype(float)
alb = alb * (1 + 0.04 * fbm(N, 6, 4, 0.5, 41)[..., None]) * (1 - 0.35 * grout[..., None])
save(alb, 'tiles-a')
save(height_to_normal(-grout + 0.03 * fnoise(N, 200, 42), 2.5), 'tiles-n', 90)

# ------------------------------------------------------------- roll-up steel shutter (1 m tile, 20 ribs)
yy = np.mgrid[0:N, 0:N][0] / N
rib = np.sin(yy * 2 * math.pi * 20)
h = np.sign(rib) * np.abs(rib) ** 0.6 + 0.04 * fnoise(N, 120, 51)
save(height_to_normal(h, 6.0), 'shutter-n', 92)
alb = 0.62 + 0.05 * fbm(N, 5, 4, 0.5, 52) + 0.05 * rib - 0.1 * np.clip(fbm(N, 3, 4, 0.5, 53, aniso=(1, 0.2)), 0, 1)
save(alb, 'shutter-a')

# ------------------------------------------------------------- warm wood (1 m tile, vertical grain)
g = fbm(N, 14, 5, 0.55, 61, aniso=(1.0, 0.08))
ringw = np.sin((np.mgrid[0:N, 0:N][1] / N * 40 + g * 3) * 2 * math.pi) * 0.5 + 0.5
alb = srgb('#7a5236')[None, None, :] * (0.85 + 0.15 * ringw[..., None] + 0.08 * g[..., None])
save(alb, 'wood-a')
save(height_to_normal(0.3 * ringw + 0.2 * g, 1.5), 'wood-n', 90)

# ------------------------------------------------------------- facade detail: window interior atlas (8 x 4 cells, 0.5 m-ish rooms)
# each cell is a tiny "room" seen through glass: back wall, ceiling line, curtain or blind, a lamp shape
W = 1024
img = np.zeros((W // 2, W, 3))
cw, ch = W // 8, W // 8
r3 = np.random.default_rng(71)
walls = [srgb(h) for h in ('#d8cbb4', '#c9b9a0', '#b9c1bf', '#e2d6c2', '#cdbba8', '#a7a49a')]
for i in range(8):
    for j in range(4):
        y0, x0 = j * ch, i * cw
        yy, xx = np.mgrid[0:ch, 0:cw] / np.array([ch, cw]).reshape(2, 1, 1)
        wall = walls[r3.integers(len(walls))]
        cell = wall[None, None, :] * (0.55 + 0.25 * yy[..., None])  # darker up top (ceiling shadow)
        kind = r3.integers(4)
        if kind == 0:  # curtains both sides
            cur = srgb(['#efe7da', '#c7b39a', '#9fa69b'][r3.integers(3)])
            m = ((xx < 0.22 + 0.04 * np.sin(yy * 30)) | (xx > 0.78 - 0.04 * np.sin(yy * 27))).astype(float)
            cell = cell * (1 - m[..., None]) + cur * (0.75 + 0.1 * np.sin(xx * 60))[..., None] * m[..., None]
        elif kind == 1:  # venetian blind half down
            m = (yy < 0.45).astype(float) * (0.85 + 0.15 * np.sin(yy * 200))
            cell = cell * (1 - (yy < 0.45)[..., None]) + srgb('#e9e4d8') * m[..., None]
        elif kind == 2:  # shelf / furniture silhouette
            m = ((yy > 0.62) & (xx > 0.15) & (xx < 0.7)).astype(float)
            cell = cell * (1 - 0.55 * m[..., None])
        # lamp spot
        lx, ly = r3.uniform(0.3, 0.7), r3.uniform(0.15, 0.3)
        spot = np.exp(-((xx - lx) ** 2 + (yy - ly) ** 2) / 0.02)
        cell = cell + 0.08 * spot[..., None]
        img[y0:y0 + ch, x0:x0 + cw] = cell
save(img, 'rooms-a', 88)

print('textures written to', OUT)

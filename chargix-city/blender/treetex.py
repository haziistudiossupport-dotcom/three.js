"""Leaf-cluster atlas (alpha cutout) and bark texture for street trees (trueno / Ligustrum style)."""
import math, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
OUT = sys.argv[1] if len(sys.argv) > 1 else '../site/assets'
SS = 2  # supersample

def leaf_cluster(seed, size=512):
    rr = random.Random(seed)
    S = size * SS
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # twigs: a main stem from bottom centre with side shoots
    twig = (92, 74, 54, 255)
    leaves = []
    def stem(x, y, ang, L, w, depth):
        pts = [(x, y)]
        for i in range(10):
            ang += rr.uniform(-0.12, 0.12)
            x += math.cos(ang) * L / 10; y -= math.sin(ang) * L / 10
            pts.append((x, y))
        d.line(pts, fill=twig, width=max(2, int(w)))
        # leaves along the stem, alternating
        for i, (px, py) in enumerate(pts[2:], 2):
            if rr.random() < 0.85:
                side = 1 if i % 2 else -1
                la = ang + side * rr.uniform(0.6, 1.1)
                leaves.append((px, py, la, rr.uniform(0.75, 1.15)))
        leaves.append((x, y, ang + rr.uniform(-0.2, 0.2), 1.1))
        if depth < 2:
            n = rr.randint(3, 4) if depth == 0 else rr.randint(1, 2)
            for k in range(n):
                t = 0.18 + 0.62 * (k + rr.uniform(0.2, 0.8)) / n; i = int(t * 10)
                bx, by = pts[i]
                side = 1 if (k + seed) % 2 else -1
                stem(bx, by, ang + side * rr.uniform(0.55, 0.95), L * rr.uniform(0.42, 0.58), w * 0.6, depth + 1)
    stem(S * 0.5, S * 0.98, math.pi / 2 + rr.uniform(-0.08, 0.08), S * 0.82, 7 * SS, 0)
    # draw leaves back to front with shading
    greens = [(46, 72, 34), (58, 86, 40), (70, 98, 46), (52, 80, 36), (82, 108, 52), (40, 64, 30)]
    rr.shuffle(leaves)
    for (px, py, la, sc) in leaves:
        L = 30 * SS * sc * 1.5; W = L * rr.uniform(0.38, 0.48)
        base = np.array(rr.choice(greens), float) * rr.uniform(0.85, 1.15)
        # petiole
        cx = px + math.cos(la) * L * 0.62; cy = py - math.sin(la) * L * 0.62
        d.line([(px, py), (px + math.cos(la) * L * 0.14, py - math.sin(la) * L * 0.14)], fill=twig, width=2 * SS)
        # leaf polygon (ovate, pointed tip)
        poly = []
        for k in range(28):
            t = k / 27 * 2 * math.pi
            u = math.cos(t); v = math.sin(t)
            w = W / 2 * (1 - 0.35 * u) * (abs(v) ** 0.9) * (1 if v >= 0 else -1)
            lx = u * L / 2; ly = w
            poly.append((cx + lx * math.cos(la) - ly * math.sin(la), cy - (lx * math.sin(la) + ly * math.cos(la))))
        col = tuple(int(c) for c in np.clip(base, 0, 255))
        d.polygon(poly, fill=col + (255,))
        # light half (cupped leaf catches light on one side) and a midrib
        half = [poly[i] for i in range(0, 15)] + [(cx - L / 2 * math.cos(la), cy + L / 2 * math.sin(la))]
        lc = tuple(int(c) for c in np.clip(base * 1.22 + 6, 0, 255))
        d.polygon(half, fill=lc + (255,))
        d.line([(cx - L * 0.48 * math.cos(la), cy + L * 0.48 * math.sin(la)), (cx + L * 0.45 * math.cos(la), cy - L * 0.45 * math.sin(la))],
               fill=tuple(int(c) for c in np.clip(base * 1.45 + 10, 0, 255)) + (255,), width=max(1, SS))
    img = img.resize((size, size), Image.LANCZOS)
    a = np.array(img).astype(np.float32)
    # dilate colour under transparent pixels so mips don't fringe dark
    rgb = a[..., :3]; al = a[..., 3:4] / 255
    blur = np.array(Image.fromarray(np.uint8(rgb * al)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32)
    wb = np.array(Image.fromarray(np.uint8(al[..., 0] * 255)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32)[..., None] / 255
    fill = blur / np.maximum(wb, 1e-3)
    rgb = rgb * al + fill * (1 - al)
    return np.concatenate([np.clip(rgb, 0, 255), a[..., 3:4]], -1).astype(np.uint8)

atlas = np.concatenate([leaf_cluster(11), leaf_cluster(29)], 1)
Image.fromarray(atlas, 'RGBA').save(f'{OUT}/cx-tex-leaves-a.webp', quality=90, method=6)

# bark: vertical fissures
rng = np.random.default_rng(3)
N = 512
def fnoise(shape, beta, sx=1, sy=1):
    f = np.fft.fftfreq(shape[0])[:, None] * sy; g = np.fft.fftfreq(shape[1])[None, :] * sx
    k = np.sqrt(f * f + g * g); k[0, 0] = 1
    spec = (rng.normal(size=shape) + 1j * rng.normal(size=shape)) / k ** beta
    n = np.real(np.fft.ifft2(spec)); return (n - n.mean()) / n.std()
h = fnoise((N, N), 1.6, sx=1.0, sy=6.0)
cracks = np.clip(1 - np.abs(fnoise((N, N), 1.4, sx=1.0, sy=8.0)) * 1.6, 0, 1) ** 4
v = 0.5 + 0.18 * h - 0.45 * cracks + 0.06 * fnoise((N, N), 0.8)
base = np.array([96, 86, 74], float)
rgb = np.clip(base[None, None] * (0.55 + 0.75 * v[..., None]), 0, 255).astype(np.uint8)
Image.fromarray(rgb).save(f'{OUT}/cx-tex-bark-a.webp', quality=88)
hh = v
gy, gx = np.gradient(hh)
n = np.stack([-gx * 3, -gy * 3, np.ones_like(hh)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(f'{OUT}/cx-tex-bark-n.webp', quality=90)
print('ok')

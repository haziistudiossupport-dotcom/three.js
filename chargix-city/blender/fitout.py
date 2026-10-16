"""Shop fit-outs for the two story storefronts, in each shop's local frame
(x along the facade, y into the building from the facade at y=0, z up from the sidewalk).
Each returned piece is a separate named object so the runtime can build it in during the story."""
import math, random
from mathutils import Vector, Matrix, noise
from citykit import MB


def cookie(mb, mat, x, y, z, r=0.045, rr=None):
    """A slightly irregular cookie: low dome with a cracked top."""
    rr = rr or random.Random(int(x * 1000 + y * 77 + z * 13))
    s = rr.random() * 10
    with mb.xf(Matrix.Translation((x, y, z)) @ Matrix.Rotation(rr.uniform(0, 6.28), 4, 'Z')):
        mb.sphere(mat, (0, 0, 0.004), r, 12, 5, (1.0, 1.0 - rr.uniform(0, 0.08), 0.24),
                  noise_fn=lambda d, s=s: 0.08 * noise.noise(d * 4 + Vector((s, s, 0))))


def kraft_box(mb, x0, y0, z0, w=0.24, d=0.24, h=0.085, label=True):
    mb.box('kraft', x0, y0, z0, x0 + w, y0 + d, z0 + h)
    mb.box('kraft_lid', x0 - 0.004, y0 - 0.004, z0 + h - 0.02, x0 + w + 0.004, y0 + d + 0.004, z0 + h + 0.002)
    if label:
        mb.box('label_cream', x0 + w * 0.3, y0 - 0.006, z0 + h * 0.2, x0 + w * 0.7, y0 - 0.004, z0 + h * 0.75)


def jar(mb, cx, cy, z0, h=0.22, r=0.07, fill='cookie_oat'):
    mb.cyl('jar_glass', cx, cy, z0, z0 + h, r, 16, (False, False))
    mb.cyl('brass', cx, cy, z0 + h, z0 + h + 0.03, r * 1.04, 16, (False, True))
    for k in range(int(h / 0.016) - 2):
        cookie(mb, fill, cx + 0.006 * math.sin(k * 2.1), cy + 0.006 * math.cos(k * 1.7), z0 + 0.01 + k * 0.016, r * 0.8)


def stool(mb, x, y, h=0.74):
    mb.cyl('oak', x, y, h - 0.04, h, 0.18, 20, (True, True))
    for a in range(4):
        ang = a * math.pi / 2 + math.pi / 4
        mb.tube('iron', (x + 0.13 * math.cos(ang), y + 0.13 * math.sin(ang), h - 0.04), (x + 0.2 * math.cos(ang), y + 0.2 * math.sin(ang), 0.0), 0.012, 6)
    with mb.xf(Matrix.Translation((x, y, 0.26))):
        mb.cyl('iron', 0, 0, 0, 0.012, 0.17, 20, (True, True))


def pendant(mb, x, y, z, ceil):
    mb.tube('iron', (x, y, z + 0.16), (x, y, ceil), 0.004, 5)
    mb.cyl('brass', x, y, z + 0.13, z + 0.17, 0.03, 12)
    mb.cyl('brass', x, y, z, z + 0.13, 0.17, 24, (False, False), r1=0.035)
    mb.sphere('bulb', (x, y, z + 0.02), 0.045, 10, 6)


def potted_plant(mb, x, y, h=1.3, seed=1):
    r = random.Random(seed)
    mb.cyl('ceramic', x, y, 0.0, 0.42, 0.2, 20, (False, True), r1=0.24)
    mb.cyl('soil', x, y, 0.36, 0.4, 0.22, 20, (False, True))
    tips = []
    for k in range(5):
        a = k * 1.26 + r.uniform(-.3, .3)
        top = Vector((x + math.cos(a) * 0.25, y + math.sin(a) * 0.25, h * r.uniform(0.75, 1.0)))
        mb.tube('bark', (x, y, 0.38), tuple(top), 0.012, 5)
        tips.append(top)
    for k in range(70):
        t = tips[k % len(tips)]
        c = t + Vector((r.gauss(0, .16), r.gauss(0, .16), r.gauss(-0.08, .14)))
        n = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0.3, 1))).normalized()
        up = Vector((0, 0, 1)); u = up.cross(n).normalized() if abs(n.z) < 0.95 else Vector((1, 0, 0))
        v = n.cross(u).normalized(); s = r.uniform(0.22, 0.32); cell = r.randrange(2)
        P = [c - u * s / 2, c + u * s / 2, c + u * s / 2 + v * s, c - u * s / 2 + v * s]
        mb.poly('plant_leaves', [tuple(p) for p in P],
                uvmode=lambda p, n, P=P, cell=cell: (0.5 * cell + 0.004 + 0.492 * ((p - P[0]).dot(u) / s), 0.004 + 0.992 * ((p - P[0]).dot(v) / s)))


def miga_fitout(ox0, ox1, depth, ceil=3.9):
    """Miga: warm artisan cookie shop. Returns [(suffix, MB)] in build order."""
    rnd = random.Random(7)
    flavours = ['cookie_choc', 'cookie_red', 'cookie_matcha', 'cookie_oat']
    out = []

    # back bar: oak cabinets, white stone top, countertop oven, stand mixer, cooling racks
    b = MB()
    by0, by1 = depth - 0.62, depth
    b.box('oak', ox0 + 0.2, by0, 0.0, ox1 - 0.2, by1, 0.88)
    for k in range(7):
        xx = ox0 + 0.2 + (ox1 - ox0 - 0.4) * k / 7
        b.box('oak_dark', xx + 0.005, by0 - 0.004, 0.08, xx + 0.012, by0, 0.86)
    b.box('stone_white', ox0 + 0.18, by0 - 0.03, 0.88, ox1 - 0.18, by1, 0.92)
    ov0 = ox1 - 1.25
    b.box('steel_brushed', ov0, by0 + 0.06, 0.92, ov0 + 0.82, by1 - 0.02, 1.48)
    b.box('oven_glass', ov0 + 0.06, by0 + 0.055, 0.98, ov0 + 0.62, by0 + 0.06, 1.42)
    b.box('steel', ov0 + 0.66, by0 + 0.05, 1.0, ov0 + 0.78, by0 + 0.06, 1.4)
    b.box('steel', ov0 + 0.08, by0 + 0.02, 1.4, ov0 + 0.6, by0 + 0.04, 1.42)
    mx = ox0 + 0.75
    b.box('mixer', mx - 0.1, by0 + 0.12, 0.92, mx + 0.1, by0 + 0.42, 0.97)
    b.box('mixer', mx - 0.06, by0 + 0.34, 0.97, mx + 0.06, by0 + 0.44, 1.3)
    b.box('mixer', mx - 0.07, by0 + 0.1, 1.24, mx + 0.07, by0 + 0.44, 1.36)
    b.cyl('steel_brushed', mx, by0 + 0.2, 0.97, 1.15, 0.09, 16, (True, False), r1=0.11)
    for k in range(3):
        rx0 = ox0 + 1.3 + k * 0.62
        b.box('steel_light', rx0, by0 + 0.08, 0.95, rx0 + 0.5, by0 + 0.5, 0.955)
        for i in range(4):
            for j in range(3):
                cookie(b, flavours[(k + i) % 4], rx0 + 0.07 + i * 0.12, by0 + 0.15 + j * 0.13, 0.958, 0.042, rnd)
    out.append(('backbar', b))

    # shelves on the back wall: jars and stacked boxes
    s = MB()
    for zi, z in enumerate((1.62, 2.06, 2.5)):
        s.box('oak', ox0 + 0.35, depth - 0.26, z, ox0 + 3.6, depth, z + 0.035)
        for bx in (ox0 + 0.5, ox0 + 3.4):
            s.box('iron', bx, depth - 0.24, z - 0.12, bx + 0.012, depth, z)
        x = ox0 + 0.45
        while x < ox0 + 3.4:
            if rnd.random() < 0.45:
                jar(s, x + 0.08, depth - 0.13, z + 0.035, rnd.uniform(0.18, 0.24), 0.07, rnd.choice(flavours)); x += 0.2
            else:
                n = rnd.randint(1, 3)
                for k in range(n):
                    kraft_box(s, x, depth - 0.25, z + 0.035 + k * 0.087, 0.22, 0.22, 0.085, label=(k == n - 1))
                x += 0.27
    out.append(('shelves', s))

    # serving counter facing the door: oak slats, white stone top
    c = MB()
    cx0, cx1, cy0, cy1 = ox0 + 0.9, ox0 + 3.9, 3.35, 3.98
    c.box('oak', cx0, cy0 + 0.03, 0.0, cx1, cy1, 0.98)
    n = int((cx1 - cx0) / 0.055)
    for k in range(n):
        xx = cx0 + 0.01 + k * (cx1 - cx0 - 0.02) / n
        c.box('oak_dark' if k % 2 else 'oak', xx, cy0, 0.06, xx + 0.042, cy0 + 0.03, 0.96)
    c.box('iron', cx0, cy0 - 0.01, 0.0, cx1, cy0 + 0.04, 0.06)
    c.box('stone_white', cx0 - 0.04, cy0 - 0.05, 0.98, cx1 + 0.04, cy1 + 0.02, 1.02)
    out.append(('counter', c))

    # glass display case with two trays of cookies, laptop and a card terminal
    d = MB()
    dx0, dx1, dy0, dy1, dz0, dz1 = cx0 + 0.15, cx0 + 1.95, cy0 + 0.05, cy1 - 0.08, 1.02, 1.42
    for (a, b2) in ((dx0, dx1),):
        d.box('glass_clear', a, dy0, dz0, b2, dy0 + 0.004, dz1)
        d.box('glass_clear', a, dy0, dz1 - 0.004, b2, dy1, dz1)
        d.box('glass_clear', a, dy0, dz0, a + 0.004, dy1, dz1)
        d.box('glass_clear', b2 - 0.004, dy0, dz0, b2, dy1, dz1)
    for (x_, y_) in ((dx0, dy0), (dx1, dy0), (dx0, dy1), (dx1, dy1)):
        d.box('brass', x_ - 0.008, y_ - 0.008, dz0, x_ + 0.008, y_ + 0.008, dz1)
    d.box('brass', dx0, dy0 - 0.008, dz1 - 0.008, dx1, dy0 + 0.008, dz1 + 0.004)
    d.box('stone_white', dx0, dy0, dz0, dx1, dy1, dz0 + 0.02)
    for ti, tz in enumerate((dz0 + 0.02, dz0 + 0.2)):
        if ti:
            d.box('glass_clear', dx0 + 0.01, dy0 + 0.01, tz - 0.004, dx1 - 0.01, dy1 - 0.01, tz)
        for k in range(4):
            tx0 = dx0 + 0.06 + k * 0.43
            d.box('steel_light', tx0, dy0 + 0.06, tz, tx0 + 0.38, dy1 - 0.06, tz + 0.008)
            for i in range(3):
                for j in range(3):
                    cookie(d, flavours[(k + ti) % 4], tx0 + 0.07 + i * 0.12, dy0 + 0.12 + j * 0.105, tz + 0.009, 0.044, rnd)
    # laptop (screen UV2 0..1 for the runtime "website being built")
    lx, ly = cx0 + 2.25, cy0 + 0.2
    with d.xf(Matrix.Translation((lx, ly, 1.02)) @ Matrix.Rotation(math.radians(15), 4, 'Z')):   # screen faces the street
        d.box('aluminium', -0.17, -0.12, 0.0, 0.17, 0.12, 0.012)
        with d.xf(Matrix.Translation((0, 0.12, 0.012)) @ Matrix.Rotation(math.radians(-15), 4, 'X')):
            d.box('aluminium', -0.17, -0.008, 0.0, 0.17, 0.0, 0.23)
            d.quad('MIGA_screen', (-0.16, -0.009, 0.01), (0.16, -0.009, 0.01), (0.16, -0.009, 0.22), (-0.16, -0.009, 0.22),
                   uv2=[(0, 1), (1, 1), (1, 0), (0, 0)])
    d.box('iron', cx0 + 2.72, cy0 + 0.25, 1.02, cx0 + 2.8, cy0 + 0.4, 1.035)
    d.box('iron', cx0 + 2.73, cy0 + 0.37, 1.035, cx0 + 2.79, cy0 + 0.4, 1.1)
    kraft_box(d, cx0 + 2.95, cy0 + 0.12, 1.02, 0.24, 0.24, 0.085)
    kraft_box(d, cx0 + 2.97, cy0 + 0.14, 1.107, 0.2, 0.2, 0.07)
    out.append(('display', d))

    # brass pendants over the counter
    p = MB()
    for k in range(3):
        pendant(p, cx0 + 0.6 + k * 0.9, (cy0 + cy1) / 2, 2.45, ceil)
    out.append(('lamps', p))

    # menu board on the left wall (UV2 0..1 for the runtime menu)
    m = MB()
    mz0, mz1, my0, my1 = 1.55, 2.75, 1.6, 3.4
    m.box('oak', ox0 + 0.005, my0 - 0.04, mz0 - 0.04, ox0 + 0.04, my1 + 0.04, mz1 + 0.04)
    m.quad('MIGA_menu', (ox0 + 0.041, my0, mz0), (ox0 + 0.041, my1, mz0), (ox0 + 0.041, my1, mz1), (ox0 + 0.041, my0, mz1),
           uv2=[(0, 1), (1, 1), (1, 0), (0, 0)])
    out.append(('menu', m))

    # window ledge with two stools, a potted olive and a door mat
    w = MB()
    w.box('oak', ox0 + 0.15, 0.36, 1.0, ox0 + 2.6, 0.7, 1.04)
    for bx in (ox0 + 0.3, ox0 + 2.4):
        w.box('iron', bx, 0.5, 0.0, bx + 0.03, 0.53, 1.0)
    stool(w, ox0 + 0.8, 1.05); stool(w, ox0 + 1.9, 1.05)
    potted_plant(w, ox0 + 0.45, depth - 1.15, 1.45, 3)
    w.box('mat', ox1 - 1.3, 0.35, 0.0, ox1 - 0.15, 1.15, 0.012)
    out.append(('window', w))
    return out


TEE = [(-0.08, 0.0), (0.0, -0.05), (0.08, 0.0), (0.22, -0.035), (0.31, -0.2), (0.25, -0.245), (0.21, -0.2),
       (0.21, -0.7), (-0.21, -0.7), (-0.21, -0.2), (-0.25, -0.245), (-0.31, -0.2), (-0.22, -0.035)]
HOODIE = [(-0.09, 0.02), (-0.12, 0.13), (0.0, 0.17), (0.12, 0.13), (0.09, 0.02), (0.24, -0.04), (0.34, -0.55), (0.27, -0.58),
          (0.22, -0.25), (0.22, -0.74), (-0.22, -0.74), (-0.22, -0.25), (-0.27, -0.58), (-0.34, -0.55), (-0.24, -0.04)]


def garment(mb, mat, shape, x, y, z, axis='y', th=0.012, s=1.0):
    """A garment hanging from a hanger at (x, y, z): a flat silhouette with thickness, plane across `axis`."""
    pts = [(u * s, v * s) for u, v in shape]
    if axis == 'y':    # rail runs along y, garment plane is x-z
        front = [(x + u, y - th, z + v) for u, v in pts]
        back = [(x + u, y + th, z + v) for u, v in reversed(pts)]
    else:              # rail runs along x, garment plane is y-z
        front = [(x + th, y + u, z + v) for u, v in pts]
        back = [(x - th, y + u, z + v) for u, v in reversed(pts)]
    mb.poly(mat, front); mb.poly(mat, back)
    n = len(front)
    for i in range(n):
        j = (i + 1) % n
        mb.poly(mat, [front[j], front[i], back[n - 1 - i], back[n - 1 - j]])
    hz = z + 0.02
    if axis == 'y':
        mb.tube('iron', (x - 0.2 * s, y, z - 0.02), (x, y, hz), 0.004, 4); mb.tube('iron', (x + 0.2 * s, y, z - 0.02), (x, y, hz), 0.004, 4)
    else:
        mb.tube('iron', (x, y - 0.2 * s, z - 0.02), (x, y, hz), 0.004, 4); mb.tube('iron', (x, y + 0.2 * s, z - 0.02), (x, y, hz), 0.004, 4)
    mb.tube('iron', (x, y, hz), (x, y, hz + 0.06), 0.004, 4)


def folded_stack(mb, mats, x0, y0, z0, n, w=0.3, d=0.24, h=0.034, rnd=None):
    """A neat stack of folded tees, alternating fold direction, each a slightly rounded slab."""
    rnd = rnd or random.Random(int(x0 * 100 + y0 * 31))
    z = z0
    for k in range(n):
        m = mats[k % len(mats)] if isinstance(mats, list) else mats
        jx, jy = rnd.uniform(-0.008, 0.008), rnd.uniform(-0.008, 0.008)
        mb.box(m, x0 + jx, y0 + jy, z, x0 + w + jx, y0 + d + jy, z + h - 0.003)
        mb.box(m, x0 + jx + 0.01, y0 + jy - 0.004, z + 0.004, x0 + w + jx - 0.01, y0 + jy, z + h - 0.007)   # rolled front fold
        z += h
    return z


def mailer(mb, x0, y0, z0, w=0.32, d=0.24, h=0.03):
    mb.box('poly_mailer', x0, y0, z0, x0 + w, y0 + d, z0 + h)
    mb.box('label_cream', x0 + w * 0.15, y0 + d * 0.25, z0 + h, x0 + w * 0.6, y0 + d * 0.75, z0 + h + 0.002)


def norte_fitout(ox0, ox1, depth, ceil=3.9):
    """NORTE: Lucía's clothing workshop. Local frame: x along the facade (ox0..ox1), y into the shop.
    Returns [(suffix, MB)] in build order: press and dryer, work table, rack, shelving, packing, lamps, wall."""
    rnd = random.Random(11)
    cot = ['cotton_sage', 'cotton_cream', 'cotton_black', 'cotton_rust', 'cotton_ink']
    out = []

    # screen-printing carousel (4 arms) and a conveyor dryer along the back wall
    pr = MB()
    px, py = ox0 + 1.6, depth - 1.5
    pr.cyl('steel', px, py, 0.0, 0.06, 0.42, 20)
    pr.cyl('steel_light', px, py, 0.06, 1.25, 0.06, 12)
    pr.cyl('steel', px, py, 1.25, 1.4, 0.16, 16)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        ca, sa = math.cos(a), math.sin(a)
        with pr.xf(Matrix.Translation((px, py, 0.98)) @ Matrix.Rotation(a, 4, 'Z')):
            pr.box('steel_light', 0.1, -0.025, -0.03, 0.62, 0.025, 0.02)                # arm
            pr.box('rubber', 0.38, -0.2, 0.02, 0.82, 0.2, 0.05)                         # platen
            if k % 2 == 0:
                folded = cot[k]
                pr.box(folded, 0.4, -0.19, 0.05, 0.8, 0.19, 0.058)                      # a shirt laid on the platen
        with pr.xf(Matrix.Translation((px, py, 1.32)) @ Matrix.Rotation(a + math.pi / 4, 4, 'Z')):
            pr.box('steel_light', 0.12, -0.02, -0.02, 0.52, 0.02, 0.02)                 # print-head arm
            for (u0, v0, u1, v1) in ((0.36, -0.25, 0.9, -0.22), (0.36, 0.22, 0.9, 0.25), (0.36, -0.25, 0.39, 0.25), (0.87, -0.25, 0.9, 0.25)):
                pr.box('aluminium', u0, v0, -0.12, u1, v1, -0.09)                        # screen frame
            pr.box('screen_mesh', 0.39, -0.22, -0.108, 0.87, 0.22, -0.104)
    # conveyor dryer
    dx0, dx1, dy0, dy1 = ox0 + 3.4, ox1 - 0.4, depth - 0.85, depth - 0.15
    pr.box('steel', dx0, dy0, 0.0, dx1, dy1, 0.78)
    pr.box('steel_brushed', dx0 + 0.9, dy0 - 0.02, 0.78, dx1 - 0.9, dy1 + 0.02, 1.32)
    pr.box('dryer_glow', dx0 + 0.9, dy0 - 0.025, 0.86, dx1 - 0.9, dy0 - 0.02, 0.9)
    pr.box('rubber', dx0, dy0 + 0.05, 0.78, dx1, dy1 - 0.05, 0.8)
    out.append(('press', pr))

    # central work table: oak top on iron legs, folded stock, laptop, label printer
    t = MB()
    tx0, tx1, ty0, ty1, th = ox0 + 2.1, ox0 + 4.7, 3.0, 4.2, 0.92
    t.box('oak', tx0, ty0, th - 0.05, tx1, ty1, th)
    for (lx, ly) in ((tx0 + 0.06, ty0 + 0.06), (tx1 - 0.1, ty0 + 0.06), (tx0 + 0.06, ty1 - 0.1), (tx1 - 0.1, ty1 - 0.1)):
        t.box('iron', lx, ly, 0.0, lx + 0.04, ly + 0.04, th - 0.05)
    t.box('iron', tx0 + 0.06, ty0 + 0.08, 0.18, tx1 - 0.06, ty1 - 0.08, 0.2)
    for i, sx in enumerate((tx0 + 0.15, tx0 + 0.55, tx0 + 0.95)):
        folded_stack(t, cot[i], sx, ty1 - 0.42, th, rnd.randint(4, 7), rnd=rnd)
    t.box('cutting_mat', tx0 + 1.4, ty0 + 0.25, th, tx0 + 2.3, ty0 + 0.85, th + 0.004)
    t.box('cotton_sage', tx0 + 1.55, ty0 + 0.35, th + 0.004, tx0 + 2.1, ty0 + 0.75, th + 0.012)   # a tee being folded
    lx, ly = tx0 + 0.55, ty0 + 0.35
    with t.xf(Matrix.Translation((lx, ly, th)) @ Matrix.Rotation(math.radians(-12), 4, 'Z')):        # screen faces the street
        t.box('aluminium', -0.17, -0.12, 0.0, 0.17, 0.12, 0.012)
        with t.xf(Matrix.Translation((0, 0.12, 0.012)) @ Matrix.Rotation(math.radians(-15), 4, 'X')):
            t.box('aluminium', -0.17, -0.008, 0.0, 0.17, 0.0, 0.23)
            t.quad('NORTE_screen', (-0.16, -0.009, 0.01), (0.16, -0.009, 0.01), (0.16, -0.009, 0.22), (-0.16, -0.009, 0.22),
                   uv2=[(0, 1), (1, 1), (1, 0), (0, 0)])
    t.box('mixer', tx1 - 0.45, ty0 + 0.2, th, tx1 - 0.25, ty0 + 0.38, th + 0.12)                  # label printer
    t.cyl('label_cream', tx1 - 0.35, ty0 + 0.5, th, th + 0.05, 0.05, 12)
    out.append(('table', t))

    # garment rack along the left wall
    r = MB()
    rx, ry0, ry1, rz = ox0 + 0.45, 1.6, depth - 2.6, 1.72
    r.tube('iron', (rx, ry0, rz), (rx, ry1, rz), 0.016, 8)
    for yy in (ry0, ry1):
        r.tube('iron', (rx, yy, 0.0), (rx, yy, rz), 0.016, 8)
        r.tube('iron', (rx - 0.28, yy, 0.02), (rx + 0.28, yy, 0.02), 0.016, 8)
    yy = ry0 + 0.25
    k = 0
    while yy < ry1 - 0.15:
        hoodie = k % 3 == 1
        garment(r, cot[(k * 2) % len(cot)], HOODIE if hoodie else TEE, rx, yy, rz - 0.06, axis='x', s=1.0)
        yy += 0.11 + rnd.uniform(0, 0.05); k += 1
    out.append(('rack', r))

    # shelving on the right wall: folded stock and mailers
    sh = MB()
    sx0, sx1, sy0, sy1 = ox1 - 0.5, ox1 - 0.05, 1.4, depth - 1.2
    for xx in (sx0, sx1 - 0.03):
        for yy in (sy0, sy1 - 0.03):
            sh.box('iron', xx, yy, 0.0, xx + 0.03, yy + 0.03, 2.4)
    for z in (0.3, 0.85, 1.4, 1.95):
        sh.box('oak', sx0, sy0, z, sx1, sy1, z + 0.03)
        yy = sy0 + 0.06
        while yy < sy1 - 0.35:
            if rnd.random() < 0.75:
                folded_stack(sh, rnd.choice(cot), sx0 + 0.08, yy, z + 0.03, rnd.randint(3, 8), w=0.3, d=0.26, rnd=rnd)
            else:
                for q in range(rnd.randint(2, 5)):
                    mailer(sh, sx0 + 0.07, yy, z + 0.03 + q * 0.03, 0.32, 0.26)
            yy += 0.34
    out.append(('shelves', sh))

    # packing bench by the window: mailers, kraft boxes, tape
    pk = MB()
    bx0, bx1, by0, by1, bh = ox1 - 2.9, ox1 - 0.9, 0.55, 1.15, 0.9
    pk.box('oak', bx0, by0, bh - 0.04, bx1, by1, bh)
    for (lx, ly) in ((bx0 + 0.05, by0 + 0.05), (bx1 - 0.09, by0 + 0.05), (bx0 + 0.05, by1 - 0.09), (bx1 - 0.09, by1 - 0.09)):
        pk.box('iron', lx, ly, 0.0, lx + 0.04, ly + 0.04, bh - 0.04)
    for q in range(6):
        mailer(pk, bx0 + 0.1 + rnd.uniform(-0.01, 0.01), by0 + 0.12, bh + q * 0.03)
    kraft_box(pk, bx0 + 0.6, by0 + 0.15, bh, 0.34, 0.26, 0.12)
    kraft_box(pk, bx0 + 0.62, by0 + 0.17, bh + 0.12, 0.3, 0.22, 0.1)
    pk.cyl('steel_light', bx1 - 0.35, by0 + 0.3, bh, bh + 0.05, 0.06, 14)
    folded_stack(pk, 'cotton_rust', bx1 - 0.7, by0 + 0.12, bh, 3, rnd=rnd)
    # window plinth with a folded display
    pk.box('stone_white', ox0 + 0.3, 0.35, 0.0, ox0 + 2.2, 0.95, 0.42)
    folded_stack(pk, ['cotton_sage', 'cotton_cream'], ox0 + 0.5, 0.5, 0.42, 4, rnd=rnd)
    folded_stack(pk, ['cotton_black', 'cotton_rust'], ox0 + 1.2, 0.5, 0.42, 3, rnd=rnd)
    out.append(('pack', pk))

    # industrial dome pendants
    lm = MB()
    for k in range(3):
        x, y, z = tx0 + 0.45 + k * 0.85, (ty0 + ty1) / 2, 2.25
        lm.tube('iron', (x, y, z + 0.2), (x, y, ceil), 0.004, 5)
        lm.cyl('iron', x, y, z + 0.16, z + 0.21, 0.03, 12)
        lm.cyl('iron', x, y, z, z + 0.16, 0.2, 24, (False, False), r1=0.04)
        lm.sphere('bulb', (x, y, z + 0.03), 0.045, 10, 6)
    out.append(('lamps', lm))

    # brand wall on the back: painted NORTE mark (UV2 0..1 for the runtime texture)
    w = MB()
    wx0, wx1, wz0, wz1 = ox0 + 0.6, ox0 + 3.0, 1.75, 3.1
    w.quad('NORTE_wall', (wx0, depth - 0.02, wz0), (wx1, depth - 0.02, wz0), (wx1, depth - 0.02, wz1), (wx0, depth - 0.02, wz1),
           uv2=[(0, 1), (1, 1), (1, 0), (0, 0)])
    out.append(('wall', w))
    return out

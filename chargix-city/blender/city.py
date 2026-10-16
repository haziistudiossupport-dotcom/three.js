"""Generate the CHARGIX miniature city block (Roma/Condesa-inspired) and export site/assets/cx-city.glb.

Usage: python3 city.py [-- render]
Blender axes: Z up, +Y north. The main street runs along X at y=0; the north row faces south (sunlit storefronts).
Static geometry is merged per material. Story-specific pieces (shop shells, shutters, signs, poster) stay separate
named objects so the runtime can animate them.
"""
import bpy, sys, math, random
from mathutils import Vector, Matrix, noise
sys.path.insert(0, '/home/claude/chargix-city/blender')
from citykit import MB
from fitout import miga_fitout, norte_fitout

OUT = '/home/claude/chargix-city/site/assets/cx-city.glb'
R = random.Random(42)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
for m in list(bpy.data.meshes):
    bpy.data.meshes.remove(m)

SW_Z = 0.15            # sidewalk height
ROAD_Y = 4.0           # carriageway half width
FACADE_Y = 7.2         # building line (north row at +7.2, south row at -7.2)
CROSS_X0, CROSS_X1 = 32.8, 40.8   # cross street carriageway
CORNER_X = 29.6        # east building line of the north/south rows

mb = MB()            # merged static geometry
named = []           # (name, MB) for separately animated pieces


def T(x, y, z=0.0, rot=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, 'Z')


# ===================================================================================== facade pieces
def window(mb, x0, x1, z0, z1, depth=0.2, kind='french', wid=0, frame='steel'):
    """Opening already cut in the wall; adds reveal, frame, mullions and glass (UV2 = pane coords + id)."""
    mb.reveal('plaster_reveal', (x0, x1, z0, z1), 0.0, depth, sill_mat='sill')
    fy = depth
    t = 0.05  # frame bar
    # outer frame
    mb.box(frame, x0, fy - 0.02, z0, x1, fy + 0.03, z0 + t)
    mb.box(frame, x0, fy - 0.02, z1 - t, x1, fy + 0.03, z1)
    mb.box(frame, x0, fy - 0.02, z0, x0 + t, fy + 0.03, z1)
    mb.box(frame, x1 - t, fy - 0.02, z0, x1, fy + 0.03, z1)
    xm = (x0 + x1) / 2
    mb.box(frame, xm - 0.025, fy - 0.015, z0, xm + 0.025, fy + 0.03, z1)
    if kind == 'french':
        zt = z0 + (z1 - z0) * 0.74
        mb.box(frame, x0, fy - 0.015, zt - 0.025, x1, fy + 0.03, zt + 0.025)
        # lower panels of a French door are solid
        mb.quad(frame, (x0 + t, fy + 0.01, z0 + t), (x1 - t, fy + 0.01, z0 + t), (x1 - t, fy + 0.01, z0 + 0.55), (x0 + t, fy + 0.01, z0 + 0.55))
        gz0 = z0 + 0.55
    else:
        gz0 = z0 + t
    # glass pane: UV2.x = u + 2*id (fract -> local u), UV2.y = v
    k = 2.0 * wid
    mb.quad('glass_res', (x0 + t, fy + 0.012, gz0), (x1 - t, fy + 0.012, gz0), (x1 - t, fy + 0.012, z1 - t), (x0 + t, fy + 0.012, z1 - t),
            uv2=[(k + 0.0, 0.0), (k + 1.0, 0.0), (k + 1.0, 1.0), (k + 0.0, 1.0)])
    # back wall behind the glass closes the reveal for shadows
    mb.quad('void', (x1, fy + 0.4, z0), (x0, fy + 0.4, z0), (x0, fy + 0.4, z1), (x1, fy + 0.4, z1))


def surround(mb, x0, x1, z0, z1, mat, w=0.12, p=0.05, head=True):
    """Moulded window surround protruding p from the wall (local frame, wall at y=0)."""
    mb.box(mat, x0 - w, -p, z0, x0, 0, z1 + (w if head else 0), skip=('+y',))
    mb.box(mat, x1, -p, z0, x1 + w, 0, z1 + (w if head else 0), skip=('+y',))
    if head:
        mb.box(mat, x0 - w - 0.04, -p - 0.04, z1 + w, x1 + w + 0.04, 0, z1 + w + 0.1, skip=('+y',))
        mb.box(mat, x0 - w + 0.02, -p - 0.02, z1, x1 + w - 0.02, 0, z1 + w, skip=('+y',))


def balcony(mb, x0, x1, z, depth=0.62, ornate=True):
    mb.box('sill', x0, -depth, z - 0.12, x1, 0, z, skip=('+y',))
    # corbels
    for cx in (x0 + 0.12, x1 - 0.12):
        mb.box('sill', cx - 0.06, -depth + 0.08, z - 0.32, cx + 0.06, 0, z - 0.12, skip=('+y',))
    h = 0.98
    y = -depth + 0.05
    mb.box('iron', x0 + 0.02, y - 0.02, z + h - 0.035, x1 - 0.02, y + 0.02, z + h)          # top rail (front)
    mb.box('iron', x0 + 0.02, y - 0.012, z + 0.08, x1 - 0.02, y + 0.012, z + 0.11)          # bottom rail
    for side in (x0 + 0.03, x1 - 0.03):                                                       # side rails
        mb.box('iron', side - 0.015, y, z + h - 0.035, side + 0.015, -0.02, z + h)
        mb.box('iron', side - 0.008, y, z + 0.08, side + 0.008, -0.02, z + 0.11)
    n = max(4, int((x1 - x0) / 0.12))
    for i in range(n + 1):
        bx = x0 + 0.03 + (x1 - x0 - 0.06) * i / n
        mb.box('iron', bx - 0.007, y - 0.007, z + 0.0, bx + 0.007, y + 0.007, z + h - 0.03)
    for i in range(1, 4):  # bars on the sides
        by = y + (-0.02 - y) * i / 4
        for side in (x0 + 0.03, x1 - 0.03):
            mb.box('iron', side - 0.007, by - 0.007, z, side + 0.007, by + 0.007, z + h - 0.03)
    if ornate:  # a band of circles just under the rail, the classic Roma ironwork
        for i in range(n):
            bx = x0 + 0.03 + (x1 - x0 - 0.06) * (i + 0.5) / n
            mb.box('iron', bx - 0.035, y - 0.006, z + h - 0.16, bx + 0.035, y + 0.006, z + h - 0.15)


def cornice(mb, x0, x1, z, mat, size=1.0, sides=True):
    """Stepped cornice band at height z (local frame), returns to the wall at both ends."""
    s = size
    mb.box(mat, x0 - 0.04 * s, -0.08 * s, z, x1 + 0.04 * s, 0, z + 0.08 * s, skip=('+y',))
    mb.box(mat, x0 - 0.1 * s, -0.16 * s, z + 0.08 * s, x1 + 0.1 * s, 0, z + 0.14 * s, skip=('+y',))
    mb.box(mat, x0 - 0.16 * s, -0.26 * s, z + 0.14 * s, x1 + 0.16 * s, 0, z + 0.24 * s, skip=('+y',))


def shutter_box(mb, x0, x1, z):
    mb.box('shutter_box', x0 - 0.05, -0.28, z, x1 + 0.05, 0.0, z + 0.36, skip=('+y',))


def storefront(mb, x0, x1, z0, z1, state='closed', wid=0, signmat=None):
    """Generic shop opening: roll-up shutter (closed / half / open) with a shallow lit interior behind glass."""
    mb.reveal('cantera_reveal', (x0, x1, z0, z1), 0.0, 0.3, skip_bottom=True)
    mb.quad('sidewalk', (x0, 0.0, z0 + 0.001), (x1, 0.0, z0 + 0.001), (x1, 0.3, z0 + 0.001), (x0, 0.3, z0 + 0.001))
    shutter_box(mb, x0, x1, z1)
    if state == 'closed':
        mb.quad('shutter', (x0, 0.08, z0), (x1, 0.08, z0), (x1, 0.08, z1), (x0, 0.08, z1))
        return
    zs = z1 if state == 'open' else z0 + (z1 - z0) * R.uniform(0.55, 0.8)
    if state != 'open':
        mb.quad('shutter', (x0, 0.08, zs), (x1, 0.08, zs), (x1, 0.08, z1), (x0, 0.08, z1))
        mb.box('steel', x0, 0.06, zs - 0.04, x1, 0.1, zs)
    # glass front + mullions
    for xx in (x0, x1):
        mb.box('steel', xx - 0.03, 0.18, z0, xx + 0.03, 0.24, z1)
    nb = max(1, int((x1 - x0) / 1.6))
    for i in range(1, nb):
        xx = x0 + (x1 - x0) * i / nb
        mb.box('steel', xx - 0.025, 0.18, z0, xx + 0.025, 0.24, z1)
    mb.box('steel', x0, 0.18, z0, x1, 0.24, z0 + 0.35)
    k = 2.0 * wid
    mb.quad('glass_shopfront', (x0, 0.21, z0 + 0.35), (x1, 0.21, z0 + 0.35), (x1, 0.21, z1), (x0, 0.21, z1),
            uv2=[(k, 0), (k + 1, 0), (k + 1, 1), (k, 1)])
    # shallow interior: floor, back wall, side walls, ceiling
    D = 2.4
    mb.quad('shop_floor', (x0, 0.24, z0 + 0.01), (x1, 0.24, z0 + 0.01), (x1, D, z0 + 0.01), (x0, D, z0 + 0.01))
    mb.quad('shop_back', (x1, D, z0), (x0, D, z0), (x0, D, z1 + 0.4), (x1, D, z1 + 0.4), uv2=[(k + 1, 0), (k, 0), (k, 1), (k + 1, 1)])
    mb.quad('shop_side', (x0, D, z0), (x0, 0.24, z0), (x0, 0.24, z1 + 0.4), (x0, D, z1 + 0.4))
    mb.quad('shop_side', (x1, 0.24, z0), (x1, D, z0), (x1, D, z1 + 0.4), (x1, 0.24, z1 + 0.4))
    mb.quad('shop_ceiling', (x0, D, z1 + 0.4), (x0, 0.24, z1 + 0.4), (x1, 0.24, z1 + 0.4), (x1, D, z1 + 0.4))


def entrance(mb, x0, x1, z0, z1):
    """Residential street door (painted steel or wood) with a transom."""
    mb.reveal('cantera_reveal', (x0, x1, z0, z1), 0.0, 0.25, skip_bottom=True)
    mb.box('step', x0 - 0.05, -0.12, z0, x1 + 0.05, 0.25, z0 + 0.06)
    zt = z1 - 0.6
    mb.quad('door_steel', (x0, 0.25, z0 + 0.06), (x1, 0.25, z0 + 0.06), (x1, 0.25, zt), (x0, 0.25, zt))
    mb.box('steel', x0, 0.22, zt - 0.04, x1, 0.27, zt + 0.04)
    mb.quad('glass_res', (x0, 0.24, zt), (x1, 0.24, zt), (x1, 0.24, z1), (x0, 0.24, z1))
    mb.box('brass', (x0 + x1) / 2 + 0.25, 0.2, z0 + 1.0, (x0 + x1) / 2 + 0.29, 0.25, z0 + 1.12)


# ===================================================================================== roof
def tinaco(mb, x, y, z, r=0.55, h=1.3):
    mb.cyl('tinaco', x, y, z, z + h * 0.85, r, 20, (False, False))
    mb.cyl('tinaco', x, y, z + h * 0.85, z + h, r, 20, (False, True), r1=r * 0.55)
    for k in range(4):  # moulded ribs
        zz = z + 0.15 + k * h * 0.2
        mb.cyl('tinaco', x, y, zz, zz + 0.05, r + 0.015, 20, (False, False))
    mb.cyl('tinaco', x, y, z + h, z + h + 0.08, r * 0.35, 12, (False, True))
    # steel stand
    mb.box('steel', x - r - 0.05, y - r - 0.05, z - 0.25, x + r + 0.05, y + r + 0.05, z)


def roof(mb, w, d, H, roofmat, parapet_mat, R2):
    mb.quad(roofmat, (0, 0.25, H), (w, 0.25, H), (w, d, H), (0, d, H))
    ph = 0.95
    mb.box(parapet_mat, -0.0, d - 0.2, H, w, d, H + ph)                     # back parapet
    mb.box(parapet_mat, 0.0, 0.25, H, 0.18, d - 0.2, H + ph)                # side parapets
    mb.box(parapet_mat, w - 0.18, 0.25, H, w, d - 0.2, H + ph)
    mb.box('coping', -0.02, d - 0.24, H + ph, w + 0.02, d + 0.02, H + ph + 0.05)
    mb.box('coping', -0.02, 0.2, H + ph, 0.2, d - 0.2, H + ph + 0.05)
    mb.box('coping', w - 0.2, 0.2, H + ph, w + 0.02, d - 0.2, H + ph + 0.05)
    # stair house
    sx = R2.uniform(0.8, max(0.9, w - 3.2))
    sy = d - 3.2
    mb.box('concrete', sx, sy, H, sx + 2.3, sy + 2.6, H + 2.4)
    mb.box('concrete', sx - 0.08, sy - 0.08, H + 2.4, sx + 2.38, sy + 2.68, H + 2.5)
    mb.quad('door_steel', (sx + 0.6, sy - 0.005, H), (sx + 1.5, sy - 0.005, H), (sx + 1.5, sy - 0.005, H + 2.0), (sx + 0.6, sy - 0.005, H + 2.0))
    # water tanks on the stair house and on the roof
    tinaco(mb, sx + 0.7, sy + 1.3, H + 2.5 + 0.25, 0.5, 1.2)
    if w > 7:
        tinaco(mb, sx + 1.7, sy + 1.3, H + 2.5 + 0.25, 0.5, 1.2)
    for i in range(R2.randint(1, 3)):
        tx = R2.uniform(1.0, w - 1.0)
        ty = R2.uniform(2.0, max(2.1, sy - 1.2))
        if abs(tx - sx - 1.15) > 1.9 or ty < sy - 1.0:
            tinaco(mb, tx, ty, H + 0.25, R2.uniform(0.45, 0.6), R2.uniform(1.0, 1.4))
    # antenna / boiler flue
    ax = R2.uniform(0.6, w - 0.6)
    mb.tube('steel', (ax, d - 1.0, H), (ax, d - 1.0, H + 2.6), 0.02, 6)
    mb.tube('steel', (ax - 0.5, d - 1.0, H + 2.3), (ax + 0.5, d - 1.0, H + 2.3), 0.012, 6)
    mb.tube('steel', (ax - 0.35, d - 1.0, H + 2.0), (ax + 0.35, d - 1.0, H + 2.0), 0.012, 6)
    if R2.random() < 0.6:  # gas tank (cilindro) in a cage, very CDMX
        gx = R2.uniform(0.6, w - 0.8); gy = 0.9
        mb.cyl('gas_tank', gx, gy, H, H + 1.1, 0.18, 14, (False, True))


# ===================================================================================== building
PLASTERS = ['plaster_ochre', 'plaster_terracotta', 'plaster_cream', 'plaster_sage', 'plaster_rose', 'plaster_white', 'plaster_gray']
WID = [0]


def next_wid():
    WID[0] += 1
    return R.randint(1, 4000)


def building(mb, b):
    """Builds a building in its local frame: facade on y=0 facing -Y, x in [0,w], z=0 at sidewalk level."""
    w, d = b['w'], b.get('d', 14.0)
    gf = b.get('gf', 4.3)
    fh = b.get('fh', 3.15)
    nf = b['floors']
    H = gf + nf * fh
    pm = b['plaster']
    style = b.get('style', 'colonial')
    R2 = random.Random(b.get('seed', int(w * 100 + nf)))
    deco = 'trim_' + b.get('trim', 'white')

    # ---- ground floor (cantera stone)
    holes = b.get('gf_holes')
    if holes is None:
        holes = []
        x = 0.45
        layout = b.get('gf_layout', ['shop', 'door'] if w < 8.5 else ['shop', 'door', 'shop'])
        widths = {'shop': None, 'door': 1.25}
        free = w - 0.9 - sum(widths[k] or 0 for k in layout) - 0.45 * (len(layout) - 1)
        nshop = sum(1 for k in layout if k == 'shop')
        for k in layout:
            ww = widths[k] or free / max(1, nshop)
            holes.append((k, x, x + ww))
            x += ww + 0.45
    openings = []
    for h in holes:
        kind, x0, x1 = h[0], h[1], h[2]
        if kind == 'door':
            openings.append((x0, x1, 0.0, 2.75))
        elif kind == 'custom':
            continue
        else:
            openings.append((x0, x1, 0.0, 3.2))
    custom = [h for h in holes if h[0] == 'custom']
    for c in custom:
        openings.append((c[1], c[2], 0.0, c[3]))
    mb.wall('cantera', 0, w, 0, gf - 0.35, 0.0, openings)
    mb.box('cantera', -0.02, -0.06, 0, w + 0.02, 0, 0.35, skip=('+y',))    # plinth
    for kind, x0, x1 in [h for h in holes if h[0] != 'custom']:
        if kind == 'door':
            entrance(mb, x0, x1, 0.0, 2.75)
        else:
            st = b.get('shop_state') or R2.choice(['closed', 'half', 'open', 'open'])
            storefront(mb, x0, x1, 0.0, 3.2, st, next_wid())
    # sign band / fascia between storefront head and first floor
    mb.box('cantera', -0.03, -0.08, gf - 0.35, w + 0.03, 0, gf - 0.2, skip=('+y',))
    cornice(mb, 0, w, gf - 0.2, 'cantera', 0.8)

    # ---- upper floors
    nb = b.get('bays') or max(2, int(round(w / 2.7)))
    pitch = w / nb
    ww = b.get('win_w', min(1.25, pitch * 0.5))
    for f in range(nf):
        z0 = gf + f * fh
        z1 = z0 + fh
        holes2 = []
        wins = []
        for i in range(nb):
            cx = pitch * (i + 0.5)
            if style == 'modern':
                holes2.append((cx - pitch * 0.42, cx + pitch * 0.42, z0 + 0.95, z0 + 2.45))
                wins.append(('window', holes2[-1]))
            else:
                french = style == 'colonial' and (b.get('balconies', 'alt') == 'all' or (f % 2 == 0) == (i % 2 == 0) or f == 0)
                if french:
                    holes2.append((cx - ww / 2, cx + ww / 2, z0 + 0.12, z0 + 2.55))
                    wins.append(('french', holes2[-1]))
                else:
                    holes2.append((cx - ww / 2, cx + ww / 2, z0 + 0.85, z0 + 2.45))
                    wins.append(('window', holes2[-1]))
        mb.wall(pm, 0, w, z0, z1, 0.0, holes2)
        for kind, h in wins:
            window(mb, *h, depth=0.2, kind='french' if kind == 'french' else 'window', wid=next_wid())
            if style != 'modern':
                surround(mb, *h, mat=deco, w=0.11, p=0.045)
            if kind == 'french' and b.get('balconies', 'alt') != 'none':
                balcony(mb, h[0] - 0.22, h[1] + 0.22, h[2], ornate=style == 'colonial')
            elif kind == 'window':
                mb.box('sill', h[0] - 0.12, -0.08, h[2] - 0.08, h[1] + 0.12, 0, h[2], skip=('+y',))
        if style == 'modern':
            mb.box('concrete', -0.02, -0.12, z1 - 0.25, w + 0.02, 0, z1 + 0.05, skip=('+y',))
        elif f < nf - 1:
            mb.box(deco, -0.02, -0.06, z1 - 0.08, w + 0.02, 0, z1 + 0.04, skip=('+y',))
        if style == 'deco':
            for i in range(nb + 1):
                px = pitch * i
                mb.box(deco, px - 0.14, -0.1, z0, px + 0.14, 0, z1, skip=('+y',))

    # ---- parapet + top cornice
    if style == 'modern':
        mb.wall(pm, 0, w, H, H + 0.95, 0.0)
        mb.box('coping', -0.03, -0.05, H + 0.95, w + 0.03, 0.25, H + 1.0)
    else:
        cornice(mb, 0, w, H - 0.25, deco, 1.25)
        mb.wall(pm, 0, w, H + 0.05, H + 0.95, 0.0)
        mb.box('coping', -0.08, -0.12, H + 0.95, w + 0.08, 0.25, H + 1.03)
        if style == 'deco':
            mid = w / 2
            mb.box(pm, mid - 1.2, -0.0, H + 0.95, mid + 1.2, 0.25, H + 1.6)
            mb.box('coping', mid - 1.25, -0.05, H + 1.6, mid + 1.25, 0.3, H + 1.66)
            mb.box(deco, mid - 0.9, -0.06, H + 1.05, mid + 0.9, 0, H + 1.12, skip=('+y',))
    mb.quad(pm, (0, 0.25, H + 0.95), (w, 0.25, H + 0.95), (w, 0.25, H + 0.05), (0, 0.25, H + 0.05))  # inner face of parapet
    # ---- side walls + back (party walls, seen over lower neighbours)
    side = 'party_' + pm.split('_')[1]
    mb.quad(side, (0, d, 0), (0, 0, 0), (0, 0, H + 0.95), (0, d, H + 0.95))
    mb.quad(side, (w, 0, 0), (w, d, 0), (w, d, H + 0.95), (w, 0, H + 0.95))
    mb.quad(side, (w, d, 0), (0, d, 0), (0, d, H + 0.95), (w, d, H + 0.95))
    roof(mb, w, d, H, b.get('roof', 'roof_red'), side, R2)
    return H


# ===================================================================================== street furniture
def lamp(mb, x, y, facing):
    """CDMX-style street lamp: tapered dark pole, curved arm, flat luminaire. facing: +1 arm toward +y, -1 toward -y."""
    z = SW_Z
    mb.cyl('lamp_metal', x, y, z, z + 0.45, 0.11, 14, (False, True), r1=0.08)
    mb.cyl('lamp_metal', x, y, z + 0.45, z + 7.6, 0.075, 12, (False, True), r1=0.05)
    pts = [(x, y, z + 7.4)]
    for i in range(1, 7):
        a = i / 6 * math.pi / 2
        pts.append((x, y + facing * 1.4 * math.sin(a) * 0.95, z + 7.4 + 0.55 * (1 - math.cos(a)) + 0.25 * math.sin(a)))
    for a_, b_ in zip(pts, pts[1:]):
        mb.tube('lamp_metal', a_, b_, 0.04, 8)
    hx, hy, hz = pts[-1]
    mb.box('lamp_metal', hx - 0.2, hy - 0.32, hz - 0.12, hx + 0.2, hy + 0.32, hz + 0.02)
    mb.box('lamp_glow', hx - 0.17, hy - 0.28, hz - 0.13, hx + 0.17, hy + 0.28, hz - 0.12)
    return (hx, hy, hz - 0.15)


LAMPS = []
TREES = []


def tree(mb, x, y, h=7.5, seed=0):
    rr = random.Random(seed)
    z = SW_Z
    # pit + grate
    mb.box('soil', x - 0.6, y - 0.6, z - 0.04, x + 0.6, y + 0.6, z - 0.02)
    mb.box('curb', x - 0.66, y - 0.66, z - 0.05, x + 0.66, y - 0.6, z + 0.02)
    mb.box('curb', x - 0.66, y + 0.6, z - 0.05, x + 0.66, y + 0.66, z + 0.02)
    mb.box('curb', x - 0.66, y - 0.6, z - 0.05, x - 0.6, y + 0.6, z + 0.02)
    mb.box('curb', x + 0.6, y - 0.6, z - 0.05, x + 0.66, y + 0.6, z + 0.02)
    # the tree itself is an instanced card-foliage model (trees.py / cx-trees.glb), placed at runtime
    TREES.append([x, y, z, seed % 3, round(rr.uniform(0, 2 * math.pi), 3), round(h / 7.5, 3)])
    return
    lean = Vector((rr.uniform(-0.25, 0.25), rr.uniform(-0.25, 0.25), 0))
    top = Vector((x, y, z + h * 0.45)) + lean
    mb.tube('bark', (x, y, z - 0.05), top, 0.13, 10)
    tips = []
    for i in range(4):
        a = rr.uniform(0, 2 * math.pi)
        L = rr.uniform(1.2, 2.0)
        tip = top + Vector((math.cos(a) * L * 0.6, math.sin(a) * L * 0.6, L * 0.9))
        mb.tube('bark', tuple(top), tuple(tip), 0.06, 7)
        tips.append(tip)
    cen = top + Vector((0, 0, h * 0.28))
    for i in range(14):
        a = rr.uniform(0, 2 * math.pi); el = rr.uniform(-0.2, 1.0)
        rad = rr.uniform(0.55, 1.0)
        off = Vector((math.cos(a) * 1.3 * (1 - el * 0.4), math.sin(a) * 1.3 * (1 - el * 0.4), el * 1.3))
        c = cen + off * rr.uniform(0.6, 1.0)
        s = rr.random() * 10
        mb.sphere('foliage', tuple(c), rad, 12, 8, (1.0, 1.0, 0.82),
                  noise_fn=lambda d, s=s: 0.22 * noise.noise(d * 2.2 + Vector((s, s, s))) + 0.08 * noise.noise(d * 6 + Vector((s, 0, 0))))


def bus_shelter(x, y):
    """Bus shelter on the north sidewalk with a back-lit ad panel at its east end facing west (toward pedestrians)."""
    z = SW_Z
    L, D, Hh = 4.2, 1.4, 2.5
    x0, x1 = x - L / 2, x + L / 2
    y0, y1 = y - D / 2, y + D / 2
    for px in (x0 + 0.1, x1 - 0.1):
        for py in (y1 - 0.08,):
            mb.box('steel_light', px - 0.05, py - 0.05, z, px + 0.05, py + 0.05, z + Hh)
    mb.box('steel_light', x0 - 0.1, y0 - 0.15, z + Hh, x1 + 0.1, y1 + 0.1, z + Hh + 0.12)
    mb.box('glass_clear', x0 + 0.15, y1 - 0.06, z + 0.3, x1 - 0.15, y1 - 0.04, z + Hh - 0.05)
    mb.box('steel_light', x0 + 0.4, y1 - 0.5, z + 0.42, x1 - 1.4, y1 - 0.2, z + 0.47)           # bench
    for bx in (x0 + 0.6, x1 - 1.6):
        mb.box('steel_light', bx - 0.03, y1 - 0.45, z, bx + 0.03, y1 - 0.25, z + 0.42)
    # ad panel (lightbox) at the east end, perpendicular to the street, poster faces west (-x)
    px = x1 - 0.05
    pan = MB()
    pan.box('steel_light', px - 0.12, y0 + 0.05, z, px + 0.12, y1 - 0.12, z + 2.45)
    pan.quad('poster_chargix', (px - 0.125, y1 - 0.2, z + 0.3), (px - 0.125, y0 + 0.13, z + 0.3), (px - 0.125, y0 + 0.13, z + 2.35), (px - 0.125, y1 - 0.2, z + 2.35),
             uv2=[(0, 0), (1, 0), (1, 1), (0, 1)])
    pan.quad('poster_back', (px + 0.125, y0 + 0.13, z + 0.3), (px + 0.125, y1 - 0.2, z + 0.3), (px + 0.125, y1 - 0.2, z + 2.35), (px + 0.125, y0 + 0.13, z + 2.35),
             uv2=[(0, 0), (1, 0), (1, 1), (0, 1)])
    named.append(('CX_poster', pan))


def kiosk(x, y, rot=0.0):
    """Green newspaper / snack kiosk ("puesto")."""
    with mb.xf(T(x, y, SW_Z, rot)):
        mb.box('kiosk_green', -1.1, -0.75, 0, 1.1, 0.75, 2.1)
        mb.box('kiosk_green', -1.35, -1.05, 2.1, 1.35, 1.0, 2.22)
        mb.box('kiosk_awning', -1.3, -1.25, 1.9, 1.3, -0.75, 2.12)
        mb.quad('kiosk_goods', (-1.0, -0.76, 0.9), (1.0, -0.76, 0.9), (1.0, -0.76, 1.85), (-1.0, -0.76, 1.85))


def bin_(x, y):
    mb.cyl('bin_green', x, y, SW_Z, SW_Z + 0.85, 0.24, 16, (True, True))
    mb.cyl('bin_dark', x, y, SW_Z + 0.85, SW_Z + 0.92, 0.26, 16, (False, True))


def bollard(x, y):
    mb.cyl('lamp_metal', x, y, SW_Z, SW_Z + 0.8, 0.06, 10, (False, True))
    mb.cyl('lamp_metal', x, y, SW_Z + 0.8, SW_Z + 0.86, 0.06, 10, (False, True), r1=0.03)


def street_sign(x, y, rot, name_mat):
    mb.cyl('lamp_metal', x, y, SW_Z, SW_Z + 3.0, 0.035, 8, (False, True))
    s = MB()
    with s.xf(T(x, y, SW_Z + 2.75, rot)):
        s.box('sign_frame', -0.48, -0.03, 0, 0.48, 0.03, 0.22)
        s.quad(name_mat, (-0.46, -0.031, 0.01), (0.46, -0.031, 0.01), (0.46, -0.031, 0.21), (-0.46, -0.031, 0.21), uv2=[(0, 0), (1, 0), (1, 1), (0, 1)])
        s.quad(name_mat, (0.46, 0.031, 0.01), (-0.46, 0.031, 0.01), (-0.46, 0.031, 0.21), (0.46, 0.031, 0.21), uv2=[(0, 0), (1, 0), (1, 1), (0, 1)])
    for mat, P in s.parts.items():
        for k in ('v', 'f', 'uv', 'uv2', 'smooth'):
            pass
    named.append((name_mat.upper(), s))


# ===================================================================================== ground
def ground():
    X0, X1 = -95.0, 95.0
    Y0, Y1 = -95.0, 95.0
    # carriageways
    mb.quad('asphalt', (X0, -ROAD_Y, 0), (CROSS_X0, -ROAD_Y, 0), (CROSS_X0, ROAD_Y, 0), (X0, ROAD_Y, 0))
    mb.quad('asphalt', (CROSS_X1, -ROAD_Y, 0), (X1, -ROAD_Y, 0), (X1, ROAD_Y, 0), (CROSS_X1, ROAD_Y, 0))
    mb.quad('asphalt', (CROSS_X0, Y0, 0), (CROSS_X1, Y0, 0), (CROSS_X1, Y1, 0), (CROSS_X0, Y1, 0))
    # sidewalks (four quadrants) as slabs with curbs
    def slab(x0, y0, x1, y1):
        mb.quad('sidewalk', (x0, y0, SW_Z), (x1, y0, SW_Z), (x1, y1, SW_Z), (x0, y1, SW_Z))
    def curb_x(x0, x1, y, side):  # curb along x at y; side=+1 sidewalk is at +y
        yy = y
        mb.box('curb', x0, yy - (0.0 if side > 0 else 0.22), 0, x1, yy + (0.22 if side > 0 else 0.0), SW_Z + 0.004, skip=('-z',))
    def curb_y(y0, y1, x, side):
        mb.box('curb', x - (0.0 if side > 0 else 0.22), y0, 0, x + (0.22 if side > 0 else 0.0), y1, SW_Z + 0.004, skip=('-z',))
    # north-west and south-west blocks (main street side + cross street side)
    slab(X0, ROAD_Y, CROSS_X0, FACADE_Y); curb_x(X0, CROSS_X0, ROAD_Y, +1)
    slab(CORNER_X, FACADE_Y, CROSS_X0, Y1); curb_y(ROAD_Y, Y1, CROSS_X0, -1)
    slab(X0, -FACADE_Y, CROSS_X0, -ROAD_Y); curb_x(X0, CROSS_X0, -ROAD_Y, -1)
    slab(CORNER_X, Y0, CROSS_X0, -FACADE_Y); curb_y(Y0, -ROAD_Y, CROSS_X0, -1)
    # east blocks
    slab(CROSS_X1, ROAD_Y, X1, FACADE_Y); curb_x(CROSS_X1, X1, ROAD_Y, +1)
    slab(CROSS_X1, FACADE_Y, CROSS_X1 + 3.2, Y1); curb_y(ROAD_Y, Y1, CROSS_X1, +1)
    slab(CROSS_X1, -FACADE_Y, X1, -ROAD_Y); curb_x(CROSS_X1, X1, -ROAD_Y, -1)
    slab(CROSS_X1, Y0, CROSS_X1 + 3.2, -FACADE_Y); curb_y(Y0, -ROAD_Y, CROSS_X1, +1)
    # block interiors (under buildings; also visible far away)
    mb.quad('ground_dark', (X0, FACADE_Y, SW_Z - 0.01), (CORNER_X, FACADE_Y, SW_Z - 0.01), (CORNER_X, Y1, SW_Z - 0.01), (X0, Y1, SW_Z - 0.01))
    mb.quad('ground_dark', (X0, Y0, SW_Z - 0.01), (CORNER_X, Y0, SW_Z - 0.01), (CORNER_X, -FACADE_Y, SW_Z - 0.01), (X0, -FACADE_Y, SW_Z - 0.01))
    mb.quad('ground_dark', (CROSS_X1 + 3.2, FACADE_Y, SW_Z - 0.01), (X1, FACADE_Y, SW_Z - 0.01), (X1, Y1, SW_Z - 0.01), (CROSS_X1 + 3.2, Y1, SW_Z - 0.01))
    mb.quad('ground_dark', (CROSS_X1 + 3.2, Y0, SW_Z - 0.01), (X1, Y0, SW_Z - 0.01), (X1, -FACADE_Y, SW_Z - 0.01), (CROSS_X1 + 3.2, -FACADE_Y, SW_Z - 0.01))
    # far ground skirt
    mb.quad('ground_far', (-600, -600, -0.05), (600, -600, -0.05), (600, 600, -0.05), (-600, 600, -0.05))
    # road markings: lane divider (dashed white), stop bars, zebra crossings
    x = X0 + 1
    while x < CROSS_X0 - 12:
        mb.quad('paint_white', (x, -0.06, 0.004), (x + 3.0, -0.06, 0.004), (x + 3.0, 0.06, 0.004), (x, 0.06, 0.004))
        x += 7.0
    zx0, zx1 = CORNER_X - 4.4, CORNER_X - 1.4
    y = -ROAD_Y + 0.35
    while y < ROAD_Y - 0.3:
        mb.quad('paint_white', (zx0, y, 0.004), (zx1, y, 0.004), (zx1, y + 0.45, 0.004), (zx0, y + 0.45, 0.004))
        y += 0.9
    mb.quad('paint_white', (zx0 - 1.1, -ROAD_Y + 0.1, 0.004), (zx0 - 0.7, -ROAD_Y + 0.1, 0.004), (zx0 - 0.7, -0.1, 0.004), (zx0 - 1.1, -0.1, 0.004))
    zy0, zy1 = FACADE_Y + 1.0, FACADE_Y + 4.0
    x = CROSS_X0 + 0.35
    while x < CROSS_X1 - 0.3:
        mb.quad('paint_white', (x, zy0, 0.004), (x + 0.45, zy0, 0.004), (x + 0.45, zy1, 0.004), (x, zy1, 0.004))
        x += 0.9
    # manholes and drains
    for mx in (-22.0, 3.0, 19.0):
        mb.cyl('manhole', mx, 1.6, 0.0, 0.008, 0.32, 20, (False, True))
    for gx in range(-80, 30, 12):
        mb.box('drain', gx, ROAD_Y - 0.42, -0.0, gx + 0.9, ROAD_Y - 0.06, 0.006)
        mb.box('drain', gx + 5, -ROAD_Y + 0.06, -0.0, gx + 5.9, -ROAD_Y + 0.42, 0.006)


# ===================================================================================== layout
NORTH = [  # x0, spec (facades face south onto the main street)
    (-62.0, dict(w=9.0, floors=3, plaster='plaster_sage', style='colonial', trim='cream', roof='roof_gray')),
    (-53.0, dict(w=7.5, floors=4, plaster='plaster_ochre', style='colonial', trim='white', roof='roof_red')),
    (-45.5, dict(w=11.5, floors=5, plaster='plaster_gray', style='modern', roof='roof_gray')),
    (-34.0, dict(w=8.0, floors=4, plaster='plaster_ochre', style='colonial', trim='white', roof='roof_red', balconies='all')),
    (-26.0, dict(w=9.0, floors=3, plaster='plaster_sage', style='colonial', trim='cream', roof='roof_gray')),
    (-17.0, dict(w=7.0, floors=5, plaster='plaster_cream', style='modern', roof='roof_red')),
    # MIGA: the cookie shop building, centre of chapter 1
    (-10.0, dict(w=8.0, floors=3, plaster='plaster_rose', style='colonial', trim='white', roof='roof_red', seed=11,
                 gf_holes=[('custom', 0.7, 6.3, 3.3), ('door', 6.75, 7.65)], balconies='all')),
    (-2.0, dict(w=9.0, floors=4, plaster='plaster_terracotta', style='colonial', trim='cream', roof='roof_gray')),
    (7.0, dict(w=6.0, floors=3, plaster='plaster_white', style='deco', trim='gray', roof='roof_red')),
    (13.0, dict(w=9.0, floors=4, plaster='plaster_sage', style='colonial', trim='white', roof='roof_red', balconies='all')),
    (22.0, dict(w=7.6, floors=5, plaster='plaster_cream', style='deco', trim='terracotta', roof='roof_gray')),
]
SOUTH = [  # x0 measured along the street; these face north (rotated 180°)
    (-62.0, dict(w=10.0, floors=4, plaster='plaster_terracotta', style='colonial', trim='cream', roof='roof_red')),
    (-52.0, dict(w=8.0, floors=3, plaster='plaster_white', style='deco', trim='sage', roof='roof_gray')),
    (-44.0, dict(w=9.0, floors=5, plaster='plaster_ochre', style='colonial', trim='white', roof='roof_red')),
    (-35.0, dict(w=10.0, floors=4, plaster='plaster_cream', style='modern', roof='roof_gray')),
    (-25.0, dict(w=8.0, floors=3, plaster='plaster_rose', style='colonial', trim='white', roof='roof_red')),
    (-17.0, dict(w=9.5, floors=4, plaster='plaster_sage', style='colonial', trim='cream', roof='roof_gray', balconies='all')),
    (-7.5, dict(w=7.0, floors=5, plaster='plaster_gray', style='modern', roof='roof_red')),
    # NORTE: the clothing studio building, centre of chapter 2
    (-0.5, dict(w=9.5, floors=3, plaster='plaster_cream', style='colonial', trim='sage', roof='roof_gray', seed=23,
                gf_holes=[('door', 0.5, 1.4), ('custom', 1.9, 8.9, 3.3)])),
    (9.0, dict(w=8.0, floors=4, plaster='plaster_ochre', style='colonial', trim='white', roof='roof_red')),
    (17.0, dict(w=6.5, floors=3, plaster='plaster_terracotta', style='deco', trim='cream', roof='roof_gray')),
    (23.5, dict(w=6.1, floors=4, plaster='plaster_white', style='colonial', trim='gray', roof='roof_red')),
]
EAST = [  # buildings across the cross street, both sides of the main street (background)
    (44.0, 'N', dict(w=10.0, floors=4, plaster='plaster_rose', style='colonial', trim='white', roof='roof_red')),
    (54.0, 'N', dict(w=9.0, floors=6, plaster='plaster_gray', style='modern', roof='roof_gray')),
    (63.0, 'N', dict(w=8.0, floors=3, plaster='plaster_ochre', style='colonial', trim='cream', roof='roof_red')),
    (44.0, 'S', dict(w=8.0, floors=3, plaster='plaster_sage', style='colonial', trim='white', roof='roof_gray')),
    (52.0, 'S', dict(w=11.0, floors=5, plaster='plaster_cream', style='modern', roof='roof_red')),
    (63.0, 'S', dict(w=8.0, floors=4, plaster='plaster_terracotta', style='colonial', trim='cream', roof='roof_red')),
]

ground()
for x0, spec in NORTH:
    with mb.xf(T(x0, FACADE_Y, SW_Z)):
        building(mb, spec)
for x0, spec in SOUTH:
    w = spec['w']
    with mb.xf(T(x0 + w, -FACADE_Y, SW_Z, math.pi)):
        building(mb, spec)
for x0, side, spec in EAST:
    if side == 'N':
        with mb.xf(T(x0, FACADE_Y, SW_Z)):
            building(mb, spec)
    else:
        with mb.xf(T(x0 + spec['w'], -FACADE_Y, SW_Z, math.pi)):
            building(mb, spec)
# cross-street facades of the two corner plots (east-facing walls of the corner buildings)
for sgn, spec in ((1, dict(w=16.0, floors=5, plaster='plaster_cream', style='deco', trim='terracotta', roof='roof_gray', d=7.6, gf_layout=['shop', 'shop', 'door'])),
                  (-1, dict(w=14.0, floors=4, plaster='plaster_white', style='colonial', trim='gray', roof='roof_red', d=6.1, gf_layout=['shop', 'door', 'shop']))):
    if sgn > 0:
        with mb.xf(T(CORNER_X, FACADE_Y, SW_Z, math.pi / 2)):
            building(mb, spec)
    else:
        with mb.xf(T(CORNER_X, -FACADE_Y - spec['w'], SW_Z, math.pi / 2)):
            building(mb, spec)

# west end: the street continues into the haze with simplified frontages
for side in (1, -1):
    x = -95.0
    while x < -62.0:
        w = R.uniform(7, 11)
        spec = dict(w=w, floors=R.randint(2, 5), plaster=R.choice(PLASTERS), style=R.choice(['colonial', 'modern', 'colonial']),
                    trim=R.choice(['white', 'cream', 'gray']), roof=R.choice(['roof_red', 'roof_gray']))
        if side > 0:
            with mb.xf(T(x, FACADE_Y, SW_Z)):
                building(mb, spec)
        else:
            with mb.xf(T(x + w, -FACADE_Y, SW_Z, math.pi)):
                building(mb, spec)
        x += w

# distant city massing (blocks beyond the street, read through haze)
far = MB()
for gx in range(-12, 13):
    for gy in range(-12, 13):
        cx, cy = gx * 26.0, gy * 26.0
        if abs(cy) < 30 and cx < 75:
            continue
        if abs(cx - 36.8) < 16 and abs(cy) < 70:
            continue
        rr = random.Random(gx * 97 + gy * 13)
        for k in range(rr.randint(2, 4)):
            bx = cx + rr.uniform(-9, 9); by = cy + rr.uniform(-9, 9)
            dist = math.hypot(bx, by)
            h = rr.uniform(7, 18) + (rr.random() < 0.07) * rr.uniform(20, 55) * min(1, dist / 120)
            bw, bd = rr.uniform(6, 14), rr.uniform(6, 14)
            far.box('far_' + rr.choice(['a', 'b', 'c', 'd']), bx - bw / 2, by - bd / 2, 0, bx + bw / 2, by + bd / 2, h, skip=('-z',))

# street furniture
for lx in (-56, -40, -24, -1, 14.5, 26):   # kept clear of the MIGA storefront sight lines
    LAMPS.append(lamp(mb, lx, ROAD_Y + 0.55, -1))
for lx in (-48, -32, -16, 0, 16):
    LAMPS.append(lamp(mb, lx, -ROAD_Y - 0.55, +1))
TREE_SPOTS = [(x, 5.0) for x in (-61.0, -51.0, -45.0, -32.0, -21.0, -14.0, 10.5, 19.5)] + \
             [(x, -5.0) for x in (-58.0, -47.0, -12.0, 12.5, 21.0)]
for i, (tx, ty) in enumerate(TREE_SPOTS):
    tree(mb, tx, ty, R.uniform(6.8, 8.2), seed=i * 7 + 3)
bus_shelter(5.5, 5.35)   # a few doors east of MIGA, poster facing the shop
kiosk(-20.0, -5.6, 0.0)
for bx, by in ((-11.6, 4.55), (8.4, 4.55), (-3.0, -4.55), (24.0, -4.55)):
    bin_(bx, by)
for k in range(5):
    bollard(CORNER_X - 4.6 + k * 0.0, ROAD_Y + 0.35 + k * 0.0) if k == 0 else None
for bx in (CORNER_X - 4.9, CORNER_X - 0.9):
    bollard(bx, ROAD_Y + 0.35); bollard(bx, -ROAD_Y - 0.35)
street_sign(CORNER_X + 0.4, ROAD_Y + 0.5, 0.0, 'sign_street_a')
street_sign(CORNER_X + 0.4, ROAD_Y + 0.5, math.pi / 2, 'sign_street_b')

# ===================================================================================== story pieces (separate objects)
def shop_shell(prefix, x0, x1, depth, facing_south=True, floor_mat='tiles'):
    """Interior room of a story shop, in the building's local frame (facade at y=0). Returns an MB."""
    s = MB()
    zc = 3.9
    s.quad(floor_mat, (x0, 0.0, 0.005), (x1, 0.0, 0.005), (x1, depth, 0.005), (x0, depth, 0.005))
    s.quad(prefix + '_wall', (x1, depth, 0), (x0, depth, 0), (x0, depth, zc), (x1, depth, zc))
    s.quad(prefix + '_wall', (x0, depth, 0), (x0, 0.3, 0), (x0, 0.3, zc), (x0, depth, zc))
    s.quad(prefix + '_wall', (x1, 0.3, 0), (x1, depth, 0), (x1, depth, zc), (x1, 0.3, zc))
    s.quad(prefix + '_ceiling', (x0, depth, zc), (x0, 0.3, zc), (x1, 0.3, zc), (x1, depth, zc))
    return s


def story_front(prefix, x0, x1, z1):
    """Storefront for a story shop: reveal, glass front with door, sign band, shutter (separate, can roll up)."""
    s = MB()
    s.reveal('cantera_reveal', (x0, x1, 0.0, z1), 0.0, 0.3, skip_bottom=True)
    s.quad('sidewalk', (x0, 0.0, 0.002), (x1, 0.0, 0.002), (x1, 0.3, 0.002), (x0, 0.3, 0.002))
    # glass front: fixed panes + a door on the right third
    yv = 0.26
    dx0 = x1 - 1.35
    for xx in (x0 + 0.03, dx0, x1 - 0.03):
        s.box(prefix + '_frame', xx - 0.03, yv - 0.03, 0, xx + 0.03, yv + 0.03, z1)
    s.box(prefix + '_frame', x0, yv - 0.03, 0, x1, yv + 0.03, 0.3)
    s.box(prefix + '_frame', x0, yv - 0.03, 2.55, x1, yv + 0.03, 2.62)
    s.quad('glass_story', (x0 + 0.06, yv, 0.3), (dx0 - 0.03, yv, 0.3), (dx0 - 0.03, yv, 2.55), (x0 + 0.06, yv, 2.55), uv2=[(0, 0), (1, 0), (1, 1), (0, 1)])
    s.quad('glass_story', (x0 + 0.06, yv, 2.62), (x1 - 0.06, yv, 2.62), (x1 - 0.06, yv, z1), (x0 + 0.06, yv, z1), uv2=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # door leaf (glass with frame), hinged at dx0
    door = MB()
    door.box(prefix + '_frame', 0.0, -0.025, 0.0, 1.2, 0.025, 0.08)
    door.box(prefix + '_frame', 0.0, -0.025, 2.47, 1.2, 0.025, 2.55)
    door.box(prefix + '_frame', 0.0, -0.025, 0.0, 0.07, 0.025, 2.55)
    door.box(prefix + '_frame', 1.13, -0.025, 0.0, 1.2, 0.025, 2.55)
    door.quad('glass_story', (0.07, 0.0, 0.08), (1.13, 0.0, 0.08), (1.13, 0.0, 2.47), (0.07, 0.0, 2.47), uv2=[(0, 0), (1, 0), (1, 1), (0, 1)])
    door.box('brass', 1.0, -0.08, 1.0, 1.03, -0.05, 1.5)
    # sign band above the opening, UV2 0..1 for the runtime sign texture
    sign = MB()
    sign.box(prefix + '_signbase', x0 - 0.1, -0.12, z1 + 0.42, x1 + 0.1, -0.02, z1 + 0.95, skip=('+y',))
    sign.quad(prefix + '_sign', (x0 - 0.08, -0.121, z1 + 0.44), (x1 + 0.08, -0.121, z1 + 0.44), (x1 + 0.08, -0.121, z1 + 0.93), (x0 - 0.08, -0.121, z1 + 0.93),
              uv2=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # shutter (roll-up): a single plane the runtime slides up into the box
    shut = MB()
    shut.quad('shutter_story', (x0, 0.08, 0.0), (x1, 0.08, 0.0), (x1, 0.08, z1), (x0, 0.08, z1), uv2=[(0, 0), (1, 0), (1, 1), (0, 1)])
    shut.box('steel', x0, 0.06, -0.0, x1, 0.1, 0.05)
    box = MB()
    box.box('shutter_box', x0 - 0.05, -0.28, z1, x1 + 0.05, 0.0, z1 + 0.36, skip=('+y',))
    return s, door, sign, shut, box, dx0, yv


STORY = {}
for key, x_build, w, south, (ox0, ox1, oz1), depth in (
        ('MIGA', -10.0, 8.0, False, (0.7, 6.3, 3.3), 7.0),
        ('NORTE', -0.5, 9.5, True, (1.9, 8.9, 3.3), 8.0)):
    if not south:
        M = T(x_build, FACADE_Y, SW_Z)
    else:
        M = T(x_build + w, -FACADE_Y, SW_Z, math.pi)
    shell = shop_shell(key, ox0, ox1, depth)
    front, door, sign, shut, sbox, dx0, yv = story_front(key, ox0, ox1, oz1)
    for nm, part, extra in ((key + '_room', shell, Matrix.Identity(4)), (key + '_front', front, Matrix.Identity(4)),
                            (key + '_sign', sign, Matrix.Identity(4)), (key + '_shutterbox', sbox, Matrix.Identity(4))):
        named.append((nm, part, M @ extra))
    named.append((key + '_door', door, M @ Matrix.Translation((dx0, yv, 0.0))))
    named.append((key + '_shutter', shut, M))
    STORY[key] = dict(matrix=[list(r) for r in M], opening=(ox0, ox1, oz1), depth=depth)
    fit = miga_fitout(ox0, ox1, depth) if key == 'MIGA' else norte_fitout(ox0, ox1, depth)
    STORY[key]['pieces'] = [suf for suf, _ in fit]
    for suf, part in fit:
        named.append((f'{key}_{suf}', part, M))

# ===================================================================================== emit + export
col = bpy.context.scene.collection
static = mb.emit('city')
farobjs = far.emit('far')
for item in named:
    if len(item) == 2:
        nm, part = item; Mx = Matrix.Identity(4)
    else:
        nm, part, Mx = item
    objs = part.emit(nm)
    if not objs:
        continue
    # join this named group into one object (multi-material) and apply its placement
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = nm
    o.data.transform(Mx)

# lamp positions for the runtime (night lighting) and story frames
import json
meta = dict(lamps=[list(l) for l in LAMPS], trees=TREES, story=STORY, sidewalk_z=SW_Z, facade_y=FACADE_Y, road_y=ROAD_Y,
            corner_x=CORNER_X, cross=[CROSS_X0, CROSS_X1])
json.dump(meta, open('/home/claude/chargix-city/site/assets/cx-city-meta.json', 'w'), indent=1)

tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
print('OBJECTS', len([o for o in bpy.data.objects if o.type == 'MESH']), 'TRIS', tris)
bpy.ops.wm.save_as_mainfile(filepath='/home/claude/chargix-city/build/city.blend')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
                          export_texcoords=True, export_normals=True, export_materials='EXPORT', export_image_format='NONE',
                          export_vertex_color='NONE')
print('EXPORTED', OUT)

"""Build a rigged, dressed MakeHuman (MPFB) character for the CHARGIX city and export it as GLB.

Usage: python3 make_character.py -- <name>   (name is a key of CHARACTERS below)
Output: build/char_<name>.glb, build/char_<name>.blend, scratchpad review renders.
"""
import bpy, bmesh, sys, math, json, os, random
from mathutils import Vector, kdtree, noise
sys.path.insert(0, '/home/claude/chargix-city/blender')
from render_util import *
import numpy as np

OUT = '/home/claude/chargix-city/build'
TEX = '/home/claude/chargix-city/build/tex'
REVIEW = '/tmp/claude-0/-home-claude/7fdae2aa-bab5-544e-a329-1c4bd93faf8f/scratchpad/review'
os.makedirs(TEX, exist_ok=True); os.makedirs(REVIEW, exist_ok=True)

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c)

CHARACTERS = {
    'mateo': dict(
        macro=dict(gender=1.0, age=0.56, muscle=0.56, weight=0.55, height=0.53, proportions=0.62, cupsize=0.5, firmness=0.5,
                   race=dict(caucasian=0.5, asian=0.25, african=0.25)),
        skin='#a8765a', lips='#9a5a4c', brow='#211a16', hair='#1d1714', stubble=0.55,
        hair_style='crop',
        detail={'mouth/mouth-upperlip-volume-decr': 0.55, 'mouth/mouth-lowerlip-volume-decr': 0.5, 'mouth/mouth-scale-horiz-decr': 0.2,
                'nose/nose-scale-horiz-decr': 0.25, 'nose/nose-flaring-decr': 0.3, 'chin/chin-prominent-incr': 0.3,
                'head/head-square': 0.25, 'eyebrows/eyebrows-trans-down': 0.25},
        top=dict(kind='tee', color='#3f5f86', sleeve=0.55, loose=0.013),
        bottom=dict(kind='jeans', color='#2e3239', loose=0.014),
        shoes=dict(upper='#e9e5dd', sole='#f4f2ee'),
        apron=dict(color='#e6dccb', strap='#5a3a2a'),
    ),
    'lucia': dict(
        macro=dict(gender=0.0, age=0.52, muscle=0.5, weight=0.47, height=0.5, proportions=0.66, cupsize=0.48, firmness=0.6,
                   race=dict(caucasian=0.2, asian=0.15, african=0.65)),
        skin='#7a4e36', lips='#6e3c33', brow='#16110e', hair='#141110', stubble=0.0,
        hair_style='bun',
        detail={'mouth/mouth-upperlip-volume-decr': 0.2, 'mouth/mouth-lowerlip-volume-decr': 0.15, 'nose/nose-scale-horiz-decr': 0.15,
                'head/head-oval': 0.4, 'chin/chin-width-decr': 0.2},
        top=dict(kind='tee', color='#e9e4d8', sleeve=0.62, loose=0.018),
        bottom=dict(kind='wide', color='#1f2124', loose=0.02),
        shoes=dict(upper='#1d1e20', sole='#ece8df'),
        apron=None,
    ),
}

name = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'mateo'
C = CHARACTERS[name]
random.seed(7 if name == 'mateo' else 11)

# ---------------------------------------------------------------- base human
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
HumanService, TargetService = mpfb()
macro = TargetService.get_default_macro_info_dict()
m = dict(C['macro']); race = m.pop('race'); macro.update(m); macro['race'] = race
bm = HumanService.create_human(macro_detail_dict=macro, mask_helpers=False)
TDIR = os.path.expanduser('~/.config/blender/5.2/extensions/user_default/mpfb/data/targets')
for tname, w in C.get('detail', {}).items():
    TargetService.load_target(bm, os.path.join(TDIR, tname + '.target.gz'), weight=w)
rig = HumanService.add_builtin_rig(bm, 'mixamo')
TargetService.bake_targets(bm)
bm.name = 'SRC'
rig.name = 'CHAR_' + name
for md in list(bm.modifiers):
    if md.type != 'ARMATURE':
        bm.modifiers.remove(md)

MW = bm.matrix_world.copy()
me = bm.data

def group_verts(obj, gname, thr=0.5):
    gi = obj.vertex_groups[gname].index
    return [v.index for v in obj.data.vertices if any(g.group == gi and g.weight > thr for g in v.groups)]

def centroid(gname):
    vs = group_verts(bm, gname)
    c = Vector()
    for i in vs:
        c += MW @ me.vertices[i].co
    return c / max(1, len(vs))

J = {k: centroid('joint-' + k) for k in ['neck', 'head', 'pelvis', 'l-shoulder', 'r-shoulder', 'l-elbow', 'r-elbow', 'l-hand', 'r-hand',
                                       'l-upper-leg', 'r-upper-leg', 'l-knee', 'r-knee', 'l-ankle', 'r-ankle', 'l-eye', 'r-eye', 'mouth', 'jaw']}
print('JOINTS', {k: [round(x, 3) for x in v] for k, v in J.items()})

def extract(src, keep_fn, oname):
    """Duplicate src and keep only vertices where keep_fn(index, world_co) is true."""
    o = src.copy(); o.data = src.data.copy(); o.name = oname; o.data.name = oname
    bpy.context.scene.collection.objects.link(o)
    b = bmesh.new(); b.from_mesh(o.data)
    b.verts.ensure_lookup_table()
    dele = [v for v in b.verts if not keep_fn(v.index, MW @ v.co)]
    bmesh.ops.delete(b, geom=dele, context='VERTS')
    b.to_mesh(o.data); b.free()
    o.data.update()
    return o

def in_group_fn(gnames):
    sets = set()
    for g in gnames:
        sets |= set(group_verts(bm, g))
    return lambda i, co: i in sets

def seg_param(p, a, b):
    ab = b - a
    t = (p - a).dot(ab) / ab.length_squared
    return t, (p - (a + ab * max(0, min(1, t)))).length

def arm_info(co):
    """Returns (side, u) where u is the normalized distance from shoulder (0) to wrist (2) along the arm, or (None, -1)."""
    for side in 'lr':
        S, E, W = J[side + '-shoulder'], J[side + '-elbow'], J[side + '-hand']
        if (co.x > 0) != (S.x > 0):
            continue
        t1, d1 = seg_param(co, S, E)
        t2, d2 = seg_param(co, E, W)
        if t1 < -0.05:
            continue
        if d1 <= d2 and d1 < 0.085:
            return side, max(0.0, min(t1, 1.0))
        if d2 < d1 and d2 < 0.075 and t2 <= 1.2:
            return side, 1.0 + max(0.0, t2)
    return None, -1

hip_z = (J['l-upper-leg'].z + J['r-upper-leg'].z) / 2
ankle_z = (J['l-ankle'].z + J['r-ankle'].z) / 2
neck = J['neck']
print('hip_z', hip_z, 'ankle_z', ankle_z, 'neck', neck)

def is_leg(co):
    return co.z < hip_z - 0.07 and abs(co.x) > 0.015

def neckline_ok(co, drop_front=0.05, drop_back=0.022):
    front = co.y < neck.y
    lim = neck.z - (drop_front if front else drop_back)
    # rounder neckline: lower near centre front
    lim -= 0.02 * max(0, 1 - abs(co.x) / 0.06) * (1 if front else 0.3)
    return co.z < lim

top = C['top']; bot = C['bottom']
tee_hem = hip_z - 0.035
waist_z = hip_z + 0.105
pant_hem = ankle_z + (0.045 if bot['kind'] == 'jeans' else 0.02)

SHX = abs(J['l-shoulder'].x)
def outside_torso(co):
    return abs(co.x) > SHX + 0.08 and co.z > hip_z
# crew neck: a plane tilted so the collar sits higher at the back, limited to a radius around the neck
NC = Vector((0.0, neck.y - 0.001, 0.0))
def collar_z(co):
    return neck.z - 0.046 + (co.y - NC.y) * 0.42
def neck_r(co):
    return math.hypot(co.x, co.y - NC.y)
def collar_r(co):
    ang = math.atan2(co.x, -(co.y - NC.y))  # 0 = front
    return 0.071 + 0.011 * max(0.0, math.cos(ang)), ang
def collar_floor(co):
    return collar_z(co) - 0.035
def in_collar(co, pad=0.0):
    return neck_r(co) < collar_r(co)[0] + pad and co.z > collar_floor(co) - pad
def tee_keep(i, co):
    side, u = arm_info(co)
    if side:
        return u < top['sleeve']
    if outside_torso(co):
        return False
    return co.z > tee_hem and co.z < neck.z - 0.005 and not in_collar(co) and not is_leg(co)

def pants_keep(i, co):
    side, u = arm_info(co)
    if side:
        return False
    return co.z < waist_z and co.z > pant_hem

tights_set = set(group_verts(bm, 'helper-tights'))
body_set = set(group_verts(bm, 'body'))

def normals_of(obj):
    obj.data.update()
    return {v.index: v.normal.copy() for v in obj.data.vertices}

def inflate(obj, fn):
    N = normals_of(obj)
    for v in obj.data.vertices:
        co = MW @ v.co
        v.co += N[v.index] * fn(co)

def add_mod(obj, typ, **kw):
    md = obj.modifiers.new(typ.lower(), typ)
    for k, v in kw.items():
        setattr(md, k, v)
    return md

def apply_all(obj, keep=('ARMATURE',)):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj; obj.select_set(True)
    for md in list(obj.modifiers):
        if md.type in keep:
            continue
        bpy.ops.object.modifier_apply(modifier=md.name)

def move_armature_last(obj):
    for md in obj.modifiers:
        if md.type == 'ARMATURE':
            arm = md.object
            obj.modifiers.remove(md)
            break
    md = obj.modifiers.new('Armature', 'ARMATURE'); md.object = rig

# ---------------------------------------------------------------- garments
def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def boundary_verts(obj):
    b = bmesh.new(); b.from_mesh(obj.data)
    idx = set()
    for e in b.edges:
        if len(e.link_faces) == 1:
            idx.add(e.verts[0].index); idx.add(e.verts[1].index)
    b.free()
    return idx

def neckline_z(co, drop_front=0.05, drop_back=0.022):
    front = co.y < neck.y
    lim = neck.z - (drop_front if front else drop_back)
    lim -= 0.02 * max(0, 1 - abs(co.x) / 0.06) * (1 if front else 0.3)
    return lim

def snap(obj, rule):
    inv = MW.inverted()
    for i in boundary_verts(obj):
        v = obj.data.vertices[i]
        co = MW @ v.co
        nco = rule(co)
        if nco is not None:
            v.co = inv @ nco
    obj.data.update()

def tee_snap(co):
    side, u = arm_info(co)
    if side:
        S, E = J[side + '-shoulder'], J[side + '-elbow']
        if abs(u - top['sleeve']) < 0.12:
            return co + (E - S) * (top['sleeve'] - u)
        return None
    if co.z < tee_hem + 0.03:
        return Vector((co.x, co.y, tee_hem))
    if co.z > neck.z - 0.13 and neck_r(co) < 0.11:
        if abs(co.z - collar_floor(co)) < 0.012:
            return Vector((co.x, co.y, collar_floor(co)))
        r, ang = collar_r(co)
        return Vector((math.sin(ang) * r, NC.y - math.cos(ang) * r, co.z))
    return None

def pants_snap(co):
    if co.z < pant_hem + 0.03:
        return Vector((co.x, co.y, pant_hem))
    if co.z > waist_z - 0.03:
        return Vector((co.x, co.y, waist_z))
    return None


# ---------------------------------------------------------------- drape: cloth hangs from the high points
def hull_radius(Rrow, nth):
    """Stretch a ring of radii around its convex hull, the way cloth bridges the sternum and spine instead of
    sinking between the pecs or shoulder blades. Returns the hull's radius along each bin's ray."""
    ths = (np.arange(nth) + 0.5) / nth * 2 * math.pi - math.pi
    P = [(float(r * math.sin(t)), float(-r * math.cos(t))) for r, t in zip(Rrow, ths)]
    pts_ = sorted(set(P))
    if len(pts_) < 3:
        return Rrow
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p_ in pts_:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p_) <= 0: lo.pop()
        lo.append(p_)
    for p_ in reversed(pts_):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p_) <= 0: hi.pop()
        hi.append(p_)
    H = lo[:-1] + hi[:-1]
    out = np.array(Rrow, dtype=float)
    for i, t in enumerate(ths):
        dx, dy = math.sin(t), -math.cos(t)
        best = None
        for a, b in zip(H, H[1:] + H[:1]):
            ex, ey = b[0] - a[0], b[1] - a[1]
            den = dx * ey - dy * ex
            if abs(den) < 1e-12: continue
            s_ = (a[0] * ey - a[1] * ex) / den        # distance along the ray
            u_ = (a[0] * dy - a[1] * dx) / den        # position along the edge
            if s_ > 0 and -1e-6 <= u_ <= 1 + 1e-6:
                best = s_ if best is None else min(best, s_)
        if best is not None:
            out[i] = max(out[i], best)
    return out

def drape(obj, select, centre_of, z_lo, z_hi, ztop_fn, taper, pad=0.002, dz=0.022, nth=48, blur=(2, 1), cover=0.004, relax=0, hull=False):
    """Rebuild a garment's radius around an axis so it falls from the widest point above instead of
    following every contour (no pecs or knees showing through). Works in cylindrical coordinates."""
    inv = MW.inverted()
    pts = []
    for v in obj.data.vertices:
        co = MW @ v.co
        if not select(co):
            continue
        cx, cy = centre_of(co)
        dx, dy = co.x - cx, co.y - cy
        pts.append((v, co, cx, cy, math.hypot(dx, dy), math.atan2(dx, -dy)))
    nz = int((z_hi - z_lo) / dz) + 2
    R = np.full((nz, nth), np.nan)
    for v, co, cx, cy, r, th in pts:
        zi = int((co.z - z_lo) / dz); ti = int((th + math.pi) / (2 * math.pi) * nth) % nth
        if 0 <= zi < nz:
            R[zi, ti] = r if np.isnan(R[zi, ti]) else max(R[zi, ti], r)
    idx = np.arange(nth)
    for zi in range(nz):
        ok = ~np.isnan(R[zi])
        if ok.sum():
            xs, ys = idx[ok], R[zi][ok]
            R[zi] = np.interp(idx, np.concatenate([xs - nth, xs, xs + nth]), np.concatenate([ys, ys, ys]))
    rows = [zi for zi in range(nz) if not np.isnan(R[zi]).all()]
    for zi in range(nz):
        if np.isnan(R[zi]).all() and rows:
            near = min(rows, key=lambda q: abs(q - zi)); R[zi] = R[near]
    if hull:
        for zi in range(nz):
            R[zi] = hull_radius(R[zi], nth)
    zt = np.array([ztop_fn(((ti + 0.5) / nth) * 2 * math.pi - math.pi) for ti in range(nth)])
    for zi in range(nz - 2, -1, -1):
        zc = z_lo + (zi + 0.5) * dz
        below = (zc < zt) & (zc + dz < zt)   # only drape from rows that are themselves below the top line
        R[zi] = np.where(below, np.maximum(R[zi], R[zi + 1] - taper * dz), R[zi])
    bt, bz = blur
    K = R.copy()
    for k in range(1, bt + 1):
        K += np.roll(R, k, 1) + np.roll(R, -k, 1)
    K /= (2 * bt + 1)
    R2 = K.copy()
    for k in range(1, bz + 1):
        R2[k:] += K[:-k]; R2[:-k] += K[k:]
    cnt = np.ones(nz)[:, None] * (1 + 2 * bz)
    for k in range(1, bz + 1):
        cnt[:k] -= 1; cnt[-k:] -= 1
    R = R2 / cnt
    if os.environ.get('DRAPE_DBG'):
        for zi in range(0, nz, 2):
            rs = [p_[4] for p_ in pts if int((p_[1].z - z_lo) / dz) == zi]
            print('DRAPE', obj.name, round(z_lo + zi * dz, 3), 'n', len(rs), 'rmax', round(max(rs), 3) if rs else None, 'Rmean', round(float(np.nanmean(R[zi])), 3), 'Rmax', round(float(np.nanmax(R[zi])), 3))
    for v, co, cx, cy, r, th in pts:
        zt_v = ztop_fn(th)
        if co.z > zt_v:
            continue
        fz = min(nz - 1.001, max(0.0, (co.z - z_lo) / dz - 0.5)); z0 = int(fz); tz = fz - z0
        ft = ((th + math.pi) / (2 * math.pi) * nth - 0.5) % nth; t0 = int(ft); tt = ft - t0; t1 = (t0 + 1) % nth
        Rs = (R[z0, t0] * (1 - tt) + R[z0, t1] * tt) * (1 - tz) + (R[z0 + 1, t0] * (1 - tt) + R[z0 + 1, t1] * tt) * tz
        nr = max(Rs + pad, r - cover)
        w = smoothstep(zt_v, zt_v - 0.045, co.z)
        nr = r + (nr - r) * w
        if os.environ.get('DRAPE_DBG2') and obj.name == 'TOP' and abs(co.x - 0.085) < 0.02 and co.y < cy:
            print('DV', round(co.z, 3), 'th', round(th, 2), 'r', round(r, 4), 'Rs', round(float(Rs), 4), 'nr', round(nr, 4))
        v.co = inv @ Vector((cx + nr * math.sin(th), cy - nr * math.cos(th), co.z))
    obj.data.update()
    if not relax:
        return
    # projecting folded body geometry onto one surface collapses faces; even the vertices out along the
    # draped surface (uniform Laplacian, then back onto the surface) so no crease survives
    def sampleR(z, th):
        fz = min(nz - 1.001, max(0.0, (z - z_lo) / dz - 0.5)); z0 = int(fz); tz = fz - z0
        ft = ((th + math.pi) / (2 * math.pi) * nth - 0.5) % nth; t0 = int(ft); tt = ft - t0; t1 = (t0 + 1) % nth
        return (R[z0, t0] * (1 - tt) + R[z0, t1] * tt) * (1 - tz) + (R[z0 + 1, t0] * (1 - tt) + R[z0 + 1, t1] * tt) * tz
    b = bmesh.new(); b.from_mesh(obj.data); b.verts.ensure_lookup_table()
    moving = {}
    for v, co, cx, cy, r, th in pts:
        bv = b.verts[v.index]
        if bv.is_boundary or co.z > ztop_fn(th) - 0.05:
            continue
        moving[v.index] = (cx, cy)
    for _ in range(relax):
        newpos = {}
        for i, (cx, cy) in moving.items():
            bv = b.verts[i]
            nb = [e.other_vert(bv).co for e in bv.link_edges]
            if not nb: continue
            avg = sum(nb, Vector()) / len(nb)
            p_ = MW @ (bv.co * 0.4 + avg * 0.6)
            th = math.atan2(p_.x - cx, -(p_.y - cy))
            nr = sampleR(p_.z, th) + pad
            newpos[i] = inv @ Vector((cx + nr * math.sin(th), cy - nr * math.cos(th), p_.z))
        for i, p_ in newpos.items():
            b.verts[i].co = p_
    b.to_mesh(obj.data); b.free(); obj.data.update()

tee = extract(bm, lambda i, co: i in body_set and tee_keep(i, co), 'TOP')
snap(tee, tee_snap)
from mathutils.bvhtree import BVHTree
tb = bmesh.new(); tb.from_mesh(me)
tb.verts.ensure_lookup_table()
bmesh.ops.delete(tb, geom=[v for v in tb.verts if v.index not in tights_set], context='VERTS')
for v in tb.verts: v.co = MW @ v.co
TIGHTS_BVH = BVHTree.FromBMesh(tb)
def to_tights(obj, near=0.012, far=0.03):
    inv = MW.inverted()
    for v in obj.data.vertices:
        co = MW @ v.co
        loc, nrm, fi, d = TIGHTS_BVH.find_nearest(co)
        if loc is None: continue
        w = 1 - smoothstep(near, far, d)
        v.co = inv @ co.lerp(loc, w)
    obj.data.update()
to_tights(tee)

def rebuild_collar(obj):
    """Replace the stair-stepped neckline with an even, smooth crew-neck loop, then relax the rings below it."""
    b = bmesh.new(); b.from_mesh(obj.data)
    b.verts.ensure_lookup_table()
    W = lambda v: MW @ v.co
    ce = [e for e in b.edges if e.is_boundary and all(W(v).z > neck.z - 0.15 and neck_r(W(v)) < 0.13 for v in e.verts)]
    adj = {}
    for e in ce:
        a_, b_ = e.verts
        adj.setdefault(a_, []).append(b_); adj.setdefault(b_, []).append(a_)
    if not adj:
        b.free(); return
    start = max(adj, key=lambda v: -W(v).y)          # rear-most vertex
    loop = [start]; prev = None; cur = start
    while True:
        nxt = [q for q in adj[cur] if q is not prev]
        if not nxt or nxt[0] is start:
            break
        prev, cur = cur, nxt[0]; loop.append(cur)
        if len(loop) > 400: break
    n = len(loop)
    angs = [math.atan2(W(v).x, -(W(v).y - NC.y)) for v in loop]
    # direction of travel around the neck
    d = sum(((angs[(i + 1) % n] - angs[i] + math.pi) % (2 * math.pi) - math.pi) for i in range(n))
    sgn = 1 if d > 0 else -1
    a0 = angs[0]
    inv = MW.inverted()
    for i, v in enumerate(loop):
        a_ = a0 + sgn * 2 * math.pi * i / n
        rc = 0.072 + 0.012 * max(0.0, math.cos(a_))
        y = NC.y - math.cos(a_) * rc; x = math.sin(a_) * rc
        z = neck.z - 0.046 + (y - NC.y) * 0.42 - 0.01 * max(0.0, math.cos(a_)) ** 2
        p_ = Vector((x, y, z))
        loc, nrm, _, dist = TIGHTS_BVH.find_nearest(p_)
        if loc is not None and dist < 0.04:
            out = Vector((p_.x, p_.y - NC.y, 0)).normalized()
            if nrm.dot(out) < 0: nrm = -nrm
            p_ = loc + nrm * 0.003   # rib sits on the skin
        v.co = inv @ p_
    ring = set(loop)
    near = set()
    for v in loop:
        for e in v.link_edges:
            o = e.other_vert(v)
            if o not in ring: near.add(o)
    near2 = set(near)
    for v in list(near):
        for e in v.link_edges:
            o = e.other_vert(v)
            if o not in ring: near2.add(o)
    for _ in range(6):
        bmesh.ops.smooth_laplacian_vert(b, verts=list(near2), lambda_factor=0.5, lambda_border=0.0, use_x=True, use_y=True, use_z=True, preserve_volume=False)
    b.to_mesh(obj.data); b.free(); obj.data.update()
rebuild_collar(tee)

b = bmesh.new(); b.from_mesh(tee.data)
cedges = [e for e in b.edges if e.is_boundary and all((MW @ v.co).z > neck.z - 0.13 and neck_r(MW @ v.co) < 0.11 for v in e.verts)]
r = bmesh.ops.extrude_edge_only(b, edges=cedges)
for v in [g for g in r['geom'] if isinstance(g, bmesh.types.BMVert)]:
    co = MW @ v.co
    d = Vector((co.x, co.y - NC.y, 0.0))
    if d.length > 1e-5:
        co = co - d.normalized() * 0.004
    co.z += 0.008
    v.co = MW.inverted() @ co
b.to_mesh(tee.data); b.free(); tee.data.update()
b = bmesh.new(); b.from_mesh(tee.data)
inner = [v for v in b.verts if not v.is_boundary]
for _ in range(3):
    bmesh.ops.smooth_laplacian_vert(b, verts=inner, lambda_factor=0.6, lambda_border=0.0, use_x=True, use_y=True, use_z=True, preserve_volume=True)
b.to_mesh(tee.data); b.free(); tee.data.update()
loose = top['loose']
def tee_off(co):
    side, u = arm_info(co)
    # the shirt rests on the shoulders: barely any gap over the deltoid, opening up down the sleeve and chest
    if side:
        return 0.003 + (loose * 0.45) * smoothstep(0.12, 0.42, u) - 0.003 * smoothstep(top['sleeve'] - 0.15, top['sleeve'], u)
    belly = smoothstep(neck.z - 0.25, tee_hem, co.z)  # 0 at chest, 1 at hem
    rest = smoothstep(neck.z - 0.17, neck.z - 0.07, co.z) * smoothstep(0.06, 0.13, abs(co.x))
    full = loose + 0.006 * belly + (0.006 if top['kind'] == 'tee' and name == 'lucia' else 0)
    return full + (0.003 - full) * rest
inflate(tee, tee_off)
SHZ = (J['l-shoulder'].z + J['r-shoulder'].z) / 2
ARMPIT = SHZ - 0.11
TORSO_CY = sum((MW @ v.co).y for v in tee.data.vertices) / len(tee.data.vertices)
def torso_sel(co):
    side, u = arm_info(co)
    if side or outside_torso(co):
        return False
    if neck_r(co) < collar_r(co)[0] + 0.03 and co.z > collar_floor(co) - 0.03:
        return False
    return co.z < SHZ + 0.02
def torso_top(th):
    k = abs(math.cos(th)) ** 0.7
    return ARMPIT + (SHZ - 0.04 - ARMPIT) * k
drape(tee, torso_sel, lambda co: (0.0, TORSO_CY), tee_hem - 0.02, SHZ + 0.03, torso_top, taper=0.2, pad=0.003, cover=0.006, relax=12, hull=True)
# relax the draped panel so there is no crease where the cloth leaves the chest
b = bmesh.new(); b.from_mesh(tee.data)
sel = [v for v in b.verts if not v.is_boundary and torso_sel(MW @ v.co) and (MW @ v.co).z < SHZ - 0.02]
for _ in range(5):
    bmesh.ops.smooth_laplacian_vert(b, verts=sel, lambda_factor=0.5, lambda_border=0.0, use_x=True, use_y=True, use_z=True, preserve_volume=True)
b.to_mesh(tee.data); b.free(); tee.data.update()

pants = extract(bm, lambda i, co: i in tights_set and pants_keep(i, co), 'BOTTOM')
snap(pants, pants_snap)
def pants_off(co):
    if bot['kind'] == 'wide':
        # wide-leg trousers: flare from the thigh down
        flare = smoothstep(hip_z - 0.1, pant_hem + 0.05, co.z)
        return bot['loose'] * 0.5 + 0.055 * (1 - (co.z - pant_hem) / max(0.01, hip_z - pant_hem)) * (1 if is_leg(co) else 0.2)
    return bot['loose'] + 0.004 * smoothstep(hip_z - 0.3, pant_hem, co.z)
inflate(pants, pants_off)
# trousers hang straight below the knee: per-leg axis from each height band's bounding box, then a round
# tube that never dips below the body (no calf or knee showing through)
LEGB = {}
for v in pants.data.vertices:
    co = MW @ v.co
    if is_leg(co):
        k = (co.x > 0, int(co.z / 0.03))
        a = LEGB.setdefault(k, [9, -9, 9, -9]); a[0] = min(a[0], co.x); a[1] = max(a[1], co.x); a[2] = min(a[2], co.y); a[3] = max(a[3], co.y)
def leg_centre(co):
    k = (co.x > 0, int(co.z / 0.03))
    if k not in LEGB:
        ks = [q for q in LEGB if q[0] == k[0]]
        k = min(ks, key=lambda q: abs(q[1] - k[1]))
    a = LEGB[k]; return ((a[0] + a[1]) / 2, (a[2] + a[3]) / 2)
knee_z = (J['l-knee'].z + J['r-knee'].z) / 2
r_knee, r_hem = (0.071, 0.064) if bot['kind'] == 'jeans' else (0.1, 0.11)
for v in pants.data.vertices:
    co = MW @ v.co
    if not is_leg(co) or co.z > knee_z + 0.16:
        continue
    cx, cy = leg_centre(co)
    dx, dy = co.x - cx, co.y - cy
    r = math.hypot(dx, dy)
    if r < 1e-5:
        continue
    t = max(0.0, min(1.0, (knee_z - co.z) / max(0.05, knee_z - pant_hem)))
    tgt = r_knee + (r_hem - r_knee) * t
    w = smoothstep(knee_z + 0.16, knee_z + 0.02, co.z)
    nr = r + (max(r + 0.004, tgt) - r) * w
    v.co = MW.inverted() @ Vector((cx + dx / r * nr, cy + dy / r * nr, co.z))
pants.data.update()
# keep the two legs from crossing the midline
inv = MW.inverted()
for v in pants.data.vertices:
    co = MW @ v.co
    if is_leg(co) and co.z < hip_z - 0.15:
        sgn = 1 if co.x > 0 else -1
        if co.x * sgn < 0.012:
            v.co = inv @ Vector((0.012 * sgn, co.y, co.z))
pants.data.update()

# shoes from the body's feet
shoe_top = ankle_z + 0.035
shoes = extract(bm, lambda i, co: i in body_set and co.z < shoe_top, 'SHOES')
def shoe_off(co):
    return 0.011 + 0.004 * smoothstep(shoe_top, 0.0, co.z)
inflate(shoes, shoe_off)
for v in shoes.data.vertices:
    co = MW @ v.co
    if co.z < 0.028:
        v.co.z = max(v.co.z, 0.0) * 0.35  # flatten the sole
# sole: extrude the bottom faces down a touch and give them their own material slot
b = bmesh.new(); b.from_mesh(shoes.data)
bottom = [f for f in b.faces if f.normal.z < -0.6]
r = bmesh.ops.extrude_face_region(b, geom=bottom)
newv = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
for v in newv:
    v.co.z -= 0.018
for f in b.faces:
    f.material_index = 1 if all((MW @ v.co).z < 0.022 for v in f.verts) else 0
b.to_mesh(shoes.data); b.free()

# solidify + smooth every garment
for g, th in ((tee, 0.0035), (pants, 0.004)):
    add_mod(g, 'SOLIDIFY', thickness=th, offset=-1.0, use_rim=True, use_even_offset=False)
    add_mod(g, 'SUBSURF', levels=1, render_levels=1)
    apply_all(g)
add_mod(shoes, 'SUBSURF', levels=1, render_levels=1)
apply_all(shoes)

# ---------------------------------------------------------------- body (remove what clothes cover)
def body_keep(i, co):
    if i not in body_set:
        return False
    if os.environ.get('FULLBODY'):
        return True
    side, u = arm_info(co)
    if side:
        if u < top['sleeve'] - 0.12:
            return False
        return True
    if co.z < shoe_top - 0.015:
        return False
    if outside_torso(co):
        return True
    a_ = math.atan2(co.x, -(co.y - NC.y)); c_ = max(0.0, math.cos(a_))
    rc = 0.072 + 0.012 * c_; zc = neck.z - 0.046 - math.cos(a_) * rc * 0.42 - 0.01 * c_ ** 2
    under_collar = neck_r(co) < rc + 0.075 and co.z > zc - 0.07   # skin shows inside the neckline and past the collar at the sides
    covered_by_tee = co.z > tee_hem + 0.03 and co.z < neck.z - 0.02 and not in_collar(co, 0.018) and not under_collar and not is_leg(co)
    covered_by_pants = co.z < waist_z - 0.03 and co.z > pant_hem + 0.06
    return not (covered_by_tee or covered_by_pants)
body = extract(bm, body_keep, 'BODY')

# ---------------------------------------------------------------- hair
head = J['head']
eye_mid = (J['l-eye'] + J['r-eye']) / 2
HC = Vector((0.0, eye_mid.y + 0.05, eye_mid.z + 0.01))
def interp(table, a):
    a = abs(a)
    for (a0, z0), (a1, z1) in zip(table, table[1:]):
        if a0 <= a <= a1:
            t = (a - a0) / (a1 - a0); t = t * t * (3 - 2 * t)
            return z0 + (z1 - z0) * t
    return table[-1][1]
if C['hair_style'] == 'crop':
    HL = [(0.0, 0.068), (0.45, 0.062), (0.85, 0.045), (1.2, 0.0), (1.38, 0.03), (1.9, 0.03), (2.3, -0.035), (3.2, -0.085)]
else:
    HL = [(0.0, 0.072), (0.5, 0.066), (0.95, 0.04), (1.25, 0.02), (1.4, 0.035), (1.9, 0.03), (2.4, -0.03), (3.2, -0.07)]
def azim(co):
    return math.atan2(co.x - HC.x, -(co.y - HC.y))
def hairline(co):
    return eye_mid.z + interp(HL, azim(co))
def hair_keep(i, co):
    return i in body_set and co.z > eye_mid.z - 0.14 and co.z > hairline(co) - 0.03 and (co - HC).length < 0.17
hair = extract(bm, hair_keep, 'HAIR')
add_mod(hair, 'SUBSURF', levels=2, render_levels=2)
apply_all(hair)
b = bmesh.new(); b.from_mesh(hair.data)
bmesh.ops.delete(b, geom=[v for v in b.verts if (MW @ v.co).z < hairline(MW @ v.co) - 0.002], context='VERTS')
b.to_mesh(hair.data); b.free(); hair.data.update()
snap(hair, lambda co: Vector((co.x, co.y, hairline(co))))
hair_col = srgb(C['hair'])
def hair_thick(co):
    a = abs(azim(co))
    up = smoothstep(eye_mid.z + 0.03, eye_mid.z + 0.12, co.z)
    edge = smoothstep(hairline(co), hairline(co) + 0.018, co.z)
    if C['hair_style'] == 'crop':
        base = 0.0055 + 0.016 * up * (1 - 0.35 * smoothstep(1.8, 3.0, a)) + 0.004 * smoothstep(2.0, 3.1, a) * (1 - up)
    else:
        base = 0.008 + 0.006 * up
    return 0.0012 + (base - 0.0012) * edge
HN = normals_of(hair)
for v in hair.data.vertices:
    co = MW @ v.co
    a = azim(co); el = (co - HC).normalized().z
    # strand-aligned noise: fine across strands (azimuth), long along strands (elevation)
    st = noise.noise(Vector((a * 9, el * 3, 0.3)))
    v.co += HN[v.index] * hair_thick(co) * (1 + 0.1 * st)
b = bmesh.new(); b.from_mesh(hair.data)
inner = [v for v in b.verts if not v.is_boundary]
for _ in range(3):
    bmesh.ops.smooth_laplacian_vert(b, verts=inner, lambda_factor=0.5, lambda_border=0.0, use_x=True, use_y=True, use_z=True, preserve_volume=True)
b.to_mesh(hair.data); b.free(); hair.data.update()
objs_extra = []
if C['hair_style'] == 'bun':
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=24, radius=0.068)
    bun = bpy.context.active_object; bun.name = 'BUN'
    top_head = max((MW @ v.co).z for v in hair.data.vertices)
    bun.location = (0, eye_mid.y + 0.075, top_head - 0.02)
    bun.scale = (1.0, 0.92, 0.82)
    bpy.ops.object.transform_apply(location=True, scale=True)
    bun.data.update()
    BN = normals_of(bun)
    for v in bun.data.vertices:
        co = v.co.copy()
        v.co += BN[v.index] * (0.012 * noise.noise(co * 40) + 0.004 * noise.noise(co * 160))
    add_mod(bun, 'SUBSURF', levels=1, render_levels=1); apply_all(bun)
    bun.parent = rig; bun.matrix_parent_inverse = rig.matrix_world.inverted()
    objs_extra.append(bun)

# ---------------------------------------------------------------- eyes
eyes = []
for side in 'lr':
    vs = group_verts(bm, 'helper-%s-eye' % side)
    c = Vector()
    for i in vs:
        c += MW @ me.vertices[i].co
    c /= len(vs)
    rad = sum(((MW @ me.vertices[i].co) - c).length for i in vs) / len(vs)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=rad * 0.98, location=c)
    e = bpy.context.active_object; e.name = 'EYE_' + side
    e.rotation_euler = (math.radians(90), 0, 0)  # sphere pole looks along -Y (forward)
    bpy.ops.object.transform_apply(location=False, rotation=True)
    eyes.append(e)

# ---------------------------------------------------------------- weights for new objects
SRC_WEIGHTS = extract(bm, lambda i, co: i in body_set, 'WSRC')
def own_weights(obj):
    """Garments are cut from the base mesh, so each vertex still carries the skin weights of the body point it
    came from. Keeping those (instead of re-sampling the nearest body surface after the cloth was draped) stops
    a draped side panel from latching onto the arm and ballooning when the arms come down."""
    deform = {g.index for g in obj.vertex_groups if g.name.startswith('mixamorig:')}
    missing = [v.index for v in obj.data.vertices if sum(e.weight for e in v.groups if e.group in deform) < 0.05]
    print('OWN_WEIGHTS', obj.name, len(obj.data.vertices), 'missing', len(missing))
    if len(missing) > 0.02 * len(obj.data.vertices):
        return False
    if missing:
        tmp = obj.copy(); tmp.data = obj.data.copy(); bpy.context.scene.collection.objects.link(tmp)
        transfer_weights(tmp)
        names = {g.index: g.name for g in tmp.vertex_groups}
        for i in missing:
            for g in obj.vertex_groups:
                g.remove([i])
            for e in tmp.data.vertices[i].groups:
                nm = names[e.group]
                vg = obj.vertex_groups.get(nm) or obj.vertex_groups.new(name=nm)
                vg.add([i], e.weight, 'REPLACE')
        bpy.data.objects.remove(tmp)
    return True

def transfer_weights(obj, only_bone=None, own=False):
    if own and own_weights(obj):
        obj.parent = rig
        obj.matrix_parent_inverse = rig.matrix_world.inverted()
        for md in list(obj.modifiers):
            obj.modifiers.remove(md)
        for g in list(obj.vertex_groups):
            if not g.name.startswith('mixamorig:'):
                obj.vertex_groups.remove(g)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = obj; obj.select_set(True)
        # cloth moves more smoothly than skin, and rebuilt edges (collar, hem) carry weights from wherever
        # their vertices came from; blur the weights across the garment so it deforms as one piece
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=6)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
        md = obj.modifiers.new('Armature', 'ARMATURE'); md.object = rig
        return
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    for md in list(obj.modifiers):
        obj.modifiers.remove(md)
    if only_bone:
        vg = obj.vertex_groups.new(name=only_bone)
        vg.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')
    else:
        dt = obj.modifiers.new('dt', 'DATA_TRANSFER')
        dt.object = SRC_WEIGHTS
        dt.use_vert_data = True
        dt.data_types_verts = {'VGROUP_WEIGHTS'}
        dt.vert_mapping = 'POLYINTERP_NEAREST'
        dt.layers_vgroup_select_src = 'ALL'
        dt.layers_vgroup_select_dst = 'NAME'
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = obj; obj.select_set(True)
        bpy.ops.object.datalayout_transfer(modifier='dt')
        bpy.ops.object.modifier_apply(modifier='dt')
        # keep only deform groups
        for g in list(obj.vertex_groups):
            if not g.name.startswith('mixamorig:'):
                obj.vertex_groups.remove(g)
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    md = obj.modifiers.new('Armature', 'ARMATURE'); md.object = rig

for o in (tee, pants):
    transfer_weights(o, own=True)
transfer_weights(shoes)
for o in [hair] + eyes + objs_extra:
    transfer_weights(o, 'mixamorig:Head')
# body keeps its own weights; drop helper/joint groups
for g in list(body.vertex_groups):
    if not g.name.startswith('mixamorig:'):
        body.vertex_groups.remove(g)
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = body; body.select_set(True)
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)

# ---------------------------------------------------------------- textures (numpy)
def save_img(arr, path, name):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = arr[..., :3]
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    return img

def tile_noise(n, scale, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((scale, scale))
    # bilinear upsample, tileable
    x = np.linspace(0, scale, n, endpoint=False)
    i0 = np.floor(x).astype(int) % scale; i1 = (i0 + 1) % scale; f = x - np.floor(x)
    f = f * f * (3 - 2 * f)
    a = g[i0][:, i0] * (1 - f)[None, :] + g[i0][:, i1] * f[None, :]
    b = g[i1][:, i0] * (1 - f)[None, :] + g[i1][:, i1] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]

def height_to_normal(hgt, strength):
    gx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * strength
    gy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * strength
    n = np.stack([-gx, gy, np.ones_like(hgt)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5

N = 512
yy, xx = np.mgrid[0:N, 0:N] / N
# jersey knit: columns of small V loops
knit = (np.abs(np.sin(xx * math.pi * 64)) ** 0.6) * (0.6 + 0.4 * np.abs(np.sin((yy * 96 + np.abs(np.sin(xx * math.pi * 64)) * 0.5) * math.pi)))
knit += 0.25 * tile_noise(N, 32, 1)
knit_n = height_to_normal(knit, 1.6)
# denim twill: diagonal ridges + slub noise
twill = 0.5 + 0.5 * np.sin((xx * 90 + yy * 90) * 2 * math.pi)
slub = tile_noise(N, 64, 2)
denim_h = twill * 0.8 + slub * 0.3
denim_n = height_to_normal(denim_h, 1.3)
denim_c = np.stack([denim_h * 0.12 + 0.88 + 0.0 * slub] * 3, -1)
# hair strands: fine anisotropic lines
hair_h = tile_noise(N, 256, 3)[:, :1].repeat(N, 1) * 0.6 + tile_noise(N, 16, 4) * 0.4
hair_n = height_to_normal(hair_h, 3.0)
canvas_h = 0.5 + 0.25 * np.sin(xx * 2 * math.pi * 110) + 0.25 * np.sin(yy * 2 * math.pi * 110) + 0.2 * tile_noise(N, 64, 5)
canvas_n = height_to_normal(canvas_h, 0.9)
save_img(knit_n, TEX + '/knit_n.png', 'knit_n')
save_img(denim_n, TEX + '/denim_n.png', 'denim_n')
save_img(hair_n, TEX + '/hair_n.png', 'hair_n')
save_img(canvas_n, TEX + '/canvas_n.png', 'canvas_n')

# eye texture: sclera + iris + pupil, iris centred in UV (u=0.5 is front after rotation? we map by sphere UV: pole at v=1)
E = 256
ev, eu = np.mgrid[0:E, 0:E] / E
r = ev  # rows are flipped on save, so this puts the iris at the +Z pole (v=1), which faces forward after rotation
iris_col = np.array(srgb('#6b4a30'))
sclera = np.array(srgb('#e8e2da'))
eye = np.zeros((E, E, 3))
eye[:] = sclera * (0.92 + 0.08 * ev[..., None])
iris_r, pupil_r = 0.135, 0.055
streak = 0.75 + 0.25 * np.sin(eu * 2 * math.pi * 40)
irismask = (r < iris_r)
eye[irismask] = (iris_col * (0.7 + 0.5 * (r[..., None] / iris_r)) * streak[..., None])[irismask]
eye[r < pupil_r] = 0.01
limbal = (r > iris_r - 0.012) & (r < iris_r + 0.004)
eye[limbal] *= 0.35
save_img(eye, TEX + '/eye_%s.png' % name, 'eye')

# ---------------------------------------------------------------- materials
def mat(mname, color=None, rough=0.6, normal=None, nstrength=0.6, tex=None, metal=0.0, sheen=0.0):
    mt = bpy.data.materials.new(mname); mt.use_nodes = True
    nt = mt.node_tree; bsdf = nt.nodes['Principled BSDF']
    if color is not None:
        bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if tex:
        it = nt.nodes.new('ShaderNodeTexImage'); it.image = bpy.data.images.load(tex)
        nt.links.new(it.outputs['Color'], bsdf.inputs['Base Color'])
    if normal:
        it = nt.nodes.new('ShaderNodeTexImage'); it.image = bpy.data.images.load(normal); it.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstrength
        nt.links.new(it.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    return mt

def uv_project(obj, scale):
    """Smart-project UVs and scale them so `scale` metres = 1 UV tile."""
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj; obj.select_set(True)
    while obj.data.uv_layers:
        obj.data.uv_layers.remove(obj.data.uv_layers[0])
    obj.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.01, scale_to_bounds=False, correct_aspect=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    # rescale: measure average UV/world ratio
    me2 = obj.data; uvl = me2.uv_layers.active.data
    ratio = []
    for p in me2.polygons[:400]:
        if len(p.loop_indices) < 3: continue
        l0, l1 = p.loop_indices[0], p.loop_indices[1]
        dw = (me2.vertices[me2.loops[l0].vertex_index].co - me2.vertices[me2.loops[l1].vertex_index].co).length
        du = (uvl[l0].uv - uvl[l1].uv).length
        if du > 1e-6: ratio.append(dw / du)
    k = (sum(ratio) / len(ratio)) / scale if ratio else 1
    for l in uvl:
        l.uv = l.uv * k

top_mat = mat('M_top', srgb(top['color']), 0.85, TEX + '/knit_n.png', 0.35)
uv_project(tee, 0.05)
tee.data.materials.clear(); tee.data.materials.append(top_mat)
if bot['kind'] == 'jeans':
    bmat = mat('M_bottom', srgb(bot['color']), 0.78, TEX + '/denim_n.png', 0.5)
else:
    bmat = mat('M_bottom', srgb(bot['color']), 0.72, TEX + '/canvas_n.png', 0.25)
uv_project(pants, 0.06)
pants.data.materials.clear(); pants.data.materials.append(bmat)
shoes.data.materials.clear()
shoes.data.materials.append(mat('M_shoe', srgb(C['shoes']['upper']), 0.55))
shoes.data.materials.append(mat('M_sole', srgb(C['shoes']['sole']), 0.7))
hair.data.uv_layers.new(name='HUV') if not hair.data.uv_layers else None
uvl = hair.data.uv_layers.active.data
for p in hair.data.polygons:
    for li in p.loop_indices:
        co = MW @ hair.data.vertices[hair.data.loops[li].vertex_index].co
        a = azim(co); el = math.asin(max(-1, min(1, (co - HC).normalized().z)))
        uvl[li].uv = (a / math.pi * 6.0, el * 2.0)
hair_mat = mat('M_hair', hair_col, 0.42, TEX + '/hair_n.png', 0.8)
hair.data.materials.clear(); hair.data.materials.append(hair_mat)
for o in objs_extra:
    uv_project(o, 0.03); o.data.materials.clear(); o.data.materials.append(hair_mat)
eye_mat = mat('M_eye', None, 0.12, tex=TEX + '/eye_%s.png' % name)
for e in eyes:
    e.data.materials.clear(); e.data.materials.append(eye_mat)

# ---------------------------------------------------------------- skin bake (procedural albedo -> 2048 texture)
skin = srgb(C['skin']); lipc = srgb(C['lips']); browc = srgb(C['brow'])
cl = body.data.color_attributes.new('mask', 'FLOAT_COLOR', 'POINT')
lips_set = set(group_verts(bm, 'lips', 0.3)); ears_set = set(group_verts(bm, 'ears', 0.3)); nails_set = set(group_verts(bm, 'fingernails', 0.3)) | set(group_verts(bm, 'toenails', 0.3))
# body vertex index -> SRC index: rebuild via kd-tree of SRC positions
kd = kdtree.KDTree(len(me.vertices))
for v in me.vertices:
    kd.insert(MW @ v.co, v.index)
kd.balance()
for v in body.data.vertices:
    co = MW @ v.co
    _, si, _ = kd.find(co)
    lips = 1.0 if si in lips_set else 0.0
    # eyebrow band: above each eye, arched
    brow = 0.0
    for side in 'lr':
        e = J[side + '-eye']
        dx = (co.x - e.x) * (1 if e.x > 0 else -1)  # + = outward
        if -0.019 < dx < 0.031 and co.y < e.y + 0.01 and co.x * e.x > 0:
            arch = 0.018 + 0.006 * (1 - ((dx - 0.006) / 0.026) ** 2) - 0.003 * smoothstep(0.012, 0.03, dx)
            thick = 0.0058 * (1 - 0.6 * smoothstep(0.0, 0.031, dx)) * smoothstep(-0.019, -0.012, dx) + 0.0005
            dz = co.z - (e.z + arch)
            brow = max(brow, max(0.0, 1 - abs(dz) / thick))
    # beard / stubble region: lower face below cheekbones
    jaw = J['jaw']; mouth = J['mouth']
    beard = 0.0
    if co.y < jaw.y + 0.03 and co.z < mouth.z + 0.035 and co.z > jaw.z - 0.065:
        face_front = co.y < eye_mid.y + 0.035
        side_ok = abs(co.x) < 0.075
        if face_front and side_ok:
            beard = smoothstep(mouth.z + 0.035, mouth.z + 0.012, co.z) * smoothstep(jaw.z - 0.065, jaw.z - 0.03, co.z)
            if abs(co.x) < 0.02 and co.z > mouth.z - 0.008 and co.z < mouth.z + 0.005:
                beard *= 0.3
            beard = max(beard, smoothstep(mouth.z + 0.03, mouth.z + 0.012, co.z) * (1 if abs(co.x) < 0.028 and co.z > mouth.z + 0.003 else 0))
    if si in lips_set:
        beard = 0
    ear = 1.0 if si in ears_set else 0.0
    nail = 1.0 if si in nails_set else 0.0
    cl.data[v.index].color = (lips, brow, beard, ear * 0.6 + nail)
body.data.update()

skin_mat = bpy.data.materials.new('M_skin'); skin_mat.use_nodes = True
nt = skin_mat.node_tree; bsdf = nt.nodes['Principled BSDF']
bsdf.inputs['Roughness'].default_value = 0.52
ca = nt.nodes.new('ShaderNodeVertexColor'); ca.layer_name = 'mask'
sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(ca.outputs['Color'], sep.inputs['Color'])
tc = nt.nodes.new('ShaderNodeTexCoord')
nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 180; nz.inputs['Detail'].default_value = 6
nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
nz2 = nt.nodes.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 1400; nz2.inputs['Detail'].default_value = 2
nt.links.new(tc.outputs['Object'], nz2.inputs['Vector'])
def mix(a, b, fac):
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    if isinstance(fac, float): mx.inputs['Factor'].default_value = fac
    else: nt.links.new(fac, mx.inputs['Factor'])
    for slot, val in (('A', a), ('B', b)):
        if isinstance(val, tuple): mx.inputs[slot].default_value = (*val, 1)
        else: nt.links.new(val, mx.inputs[slot])
    return mx.outputs['Result']
def mathn(op, a, b):
    mn = nt.nodes.new('ShaderNodeMath'); mn.operation = op
    for idx, val in enumerate((a, b)):
        if isinstance(val, float): mn.inputs[idx].default_value = val
        else: nt.links.new(val, mn.inputs[idx])
    return mn.outputs[0]
base = mix(tuple(x * 0.93 for x in skin), tuple(min(1, x * 1.07) for x in skin), nz.outputs['Fac'])
redder = tuple(min(1, x * k) for x, k in zip(skin, (1.12, 0.92, 0.9)))
base = mix(base, redder, mathn('MULTIPLY', sep.outputs['Blue' if False else 'Red'], 0.0))  # placeholder keeps graph simple
ears_f = mathn('MULTIPLY', ca.outputs['Alpha'], 0.5)
base = mix(base, redder, ears_f)
base = mix(base, lipc, mathn('MULTIPLY', sep.outputs['Red'], 0.5))
if C['stubble'] > 0:
    st = mathn('MULTIPLY', sep.outputs['Blue'], mathn('MULTIPLY', mathn('GREATER_THAN', nz2.outputs['Fac'], 0.47), C['stubble']))
    base = mix(base, tuple(h * 1.4 + s * 0.35 for h, s in zip(srgb(C['hair']), skin)), st)
    base = mix(base, tuple(x * 0.82 for x in skin), mathn('MULTIPLY', sep.outputs['Blue'], 0.35))
brow_f = mathn('MULTIPLY', sep.outputs['Green'], mathn('ADD', mathn('MULTIPLY', mathn('GREATER_THAN', nz2.outputs['Fac'], 0.42), 0.6), 0.35))
base = mix(base, browc, mathn('MINIMUM', mathn('MULTIPLY', brow_f, 1.4), 0.95))
nt.links.new(base, bsdf.inputs['Base Color'])
body.data.materials.clear(); body.data.materials.append(skin_mat)

# bake to texture
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 4; sc.cycles.device = 'CPU'
img = bpy.data.images.new('skin_' + name, 2048, 2048, alpha=False)
itn = nt.nodes.new('ShaderNodeTexImage'); itn.image = img
for n in nt.nodes: n.select = False
itn.select = True; nt.nodes.active = itn
# emission path for bake
em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(base, em.inputs['Color'])
out = nt.nodes['Material Output']; old = out.inputs['Surface'].links[0].from_socket
nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = body; body.select_set(True)
mods_state = [(md, md.show_viewport, md.show_render) for md in body.modifiers]
for md, _, _ in mods_state: md.show_viewport = md.show_render = False
sc.render.bake.margin = 8
bpy.ops.object.bake(type='EMIT')
for md, a, b in mods_state: md.show_viewport = a; md.show_render = b
img.filepath_raw = TEX + '/skin_%s.png' % name; img.file_format = 'PNG'; img.save()
# rewire: baked texture drives base color
nt.links.new(old, out.inputs['Surface'])
nt.links.new(itn.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Subsurface Weight'].default_value = 0.0

# ---------------------------------------------------------------- tidy + export
for o in (bm, SRC_WEIGHTS):
    bpy.data.objects.remove(o)
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.data.color_attributes.clear() if hasattr(o.data.color_attributes, 'clear') else None
        for p in o.data.polygons: p.use_smooth = True
tri = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
print('POLYS', tri, [(o.name, len(o.data.vertices)) for o in bpy.data.objects if o.type == 'MESH'])
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/char_%s.blend' % name)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT + '/char_%s.glb' % name, export_format='GLB', use_selection=True, export_skins=True,
                          export_animations=False, export_yup=True, export_apply=False, export_image_format='WEBP' if hasattr(bpy.types, 'Image') else 'AUTO',
                          export_vertex_color='NONE')
print('EXPORTED')

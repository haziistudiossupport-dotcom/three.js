"""Street trees (trueno / Ligustrum style): tapered branching bark tubes + alpha-card foliage with
canopy-oriented custom normals. Three variants exported to cx-trees.glb as tree{N}_bark / tree{N}_leaves."""
import bpy, bmesh, math, random, os, sys
from mathutils import Vector, Matrix, Quaternion

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'site', 'assets'))
bpy.ops.wm.read_factory_settings(use_empty=True)

def frame(d):
    d = d.normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    u = d.cross(up).normalized(); v = d.cross(u).normalized()
    return u, v

class Tree:
    def __init__(self, seed):
        self.r = random.Random(seed)
        self.bark = bmesh.new(); self.buv = self.bark.loops.layers.uv.new('UVMap')
        self.leaf = bmesh.new(); self.luv = self.leaf.loops.layers.uv.new('UVMap')
        self.tips = []      # (pos, dir, depth)
        self.lnorm = []     # per leaf vertex: custom normal

    def tube(self, pts, radii, sides):
        rings = []
        acc = 0.0
        for i, p in enumerate(pts):
            d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
            u, v = frame(d)
            ring = []
            for k in range(sides + 1):
                a = k / sides * 2 * math.pi
                ring.append(self.bark.verts.new(p + (u * math.cos(a) + v * math.sin(a)) * radii[i]))
            if i: acc += (pts[i] - pts[i - 1]).length
            rings.append((ring, acc))
        for (r0, a0), (r1, a1) in zip(rings, rings[1:]):
            circ = 2 * math.pi * 0.12
            for k in range(sides):
                f = self.bark.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k]))
                f.smooth = True
                for loop, (uu, vv) in zip(f.loops, ((k / sides, a0), ((k + 1) / sides, a0), ((k + 1) / sides, a1), (k / sides, a1))):
                    loop[self.buv].uv = (uu * circ / 0.6 * 2, vv / 0.6)

    def branch(self, p, d, L, r0, depth, maxd):
        r = self.r
        n = max(3, int(L / 0.35))
        pts = [p.copy()]; dirs = []
        cur = p.copy(); dd = d.normalized()
        for i in range(n):
            # bend: up-seeking with a little wander
            dd = (dd + Vector((r.uniform(-.18, .18), r.uniform(-.18, .18), r.uniform(-.05, .12) + 0.04 * (depth > 0)))).normalized()
            cur = cur + dd * (L / n)
            pts.append(cur.copy()); dirs.append(dd.copy())
        rad = [r0 * (1 - 0.45 * i / n) for i in range(n + 1)]
        self.tube(pts, rad, 8 if depth < 2 else 5)
        if depth >= maxd:
            self.tips.append((pts[-1], dirs[-1], depth))
            return
        kids = {0: r.randint(3, 4), 1: r.randint(3, 4), 2: r.randint(2, 3)}[depth]
        az0 = r.uniform(0, 2 * math.pi)
        for k in range(kids):
            t = 1.0 if depth == 0 else r.uniform(0.35, 1.0) if k else 1.0
            idx = min(n, max(1, int(round(t * n))))
            base = pts[idx]; pd = dirs[idx - 1]
            u, v = frame(pd)
            az = az0 + k * 2 * math.pi / kids + r.uniform(-0.4, 0.4)
            spread = {0: r.uniform(0.4, 0.65), 1: r.uniform(0.45, 0.8), 2: r.uniform(0.5, 0.9)}[depth]
            nd = (pd * math.cos(spread) + (u * math.cos(az) + v * math.sin(az)) * math.sin(spread)).normalized()
            nL = {0: r.uniform(1.15, 1.5), 1: r.uniform(0.75, 1.0), 2: r.uniform(0.4, 0.6)}[depth]
            self.branch(base, nd, nL, rad[idx] * 0.72, depth + 1, maxd)
            if depth >= 1:
                self.tips.append((base, nd, depth))

    def card(self, c, n, up, size, cell):
        # quad with bottom edge at the twig (c), extending along `up`
        u = up.cross(n).normalized(); upv = n.cross(u).normalized()
        w = size * 0.5
        P = [c - u * w, c + u * w, c + u * w + upv * size, c - u * w + upv * size]
        vs = [self.leaf.verts.new(p) for p in P]
        f = self.leaf.faces.new(vs)
        x0 = 0.5 * cell
        for loop, uv in zip(f.loops, ((x0 + 0.004, 0.004), (x0 + 0.496, 0.004), (x0 + 0.496, 0.996), (x0 + 0.004, 0.996))):
            loop[self.luv].uv = uv
        return vs

    def foliage(self, centre, rx, rz, count):
        r = self.r
        cards = []
        tips = [t for t in self.tips if t[2] >= 2]
        for i in range(count):
            p, d, depth = tips[r.randrange(len(tips))]
            q = p + Vector((r.gauss(0, .35), r.gauss(0, .35), r.gauss(0, .3)))
            out = q - centre; out = Vector((out.x / rx, out.y / rx, out.z / rz))
            # keep cards inside the canopy ellipsoid shell
            if out.length > 1.05: q = centre + (q - centre) * (1.05 / out.length)
            o = (q - centre); o = Vector((o.x / rx ** 2, o.y / rx ** 2, o.z / rz ** 2)).normalized()
            n = (Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized() + o * 0.6).normalized()
            up = (o + d * 0.6 + Vector((0, 0, 0.5))).normalized()
            if abs(up.dot(n)) > 0.9: up = Vector((0, 0, 1))
            size = r.uniform(0.6, 0.9)
            vs = self.card(q - up * 0.12, n, up, size, r.randrange(2))
            for v in vs:
                o2 = v.co - centre; o2 = Vector((o2.x / rx ** 2, o2.y / rx ** 2, o2.z / rz ** 2)).normalized()
                self.lnorm.append(o2)

def build(variant):
    t = Tree(100 + variant * 17)
    r = t.r
    H0 = r.uniform(2.4, 2.9)
    lean = Vector((r.uniform(-.06, .06), r.uniform(-.06, .06), 1)).normalized()
    # trunk to the fork
    n = 6; pts = [Vector((0, 0, -0.1))]
    for i in range(n): pts.append(pts[-1] + lean * (H0 / n) + Vector((r.uniform(-.02, .02), r.uniform(-.02, .02), 0)))
    rad = [0.17 - 0.05 * i / n for i in range(n + 1)]; rad[0] = 0.21
    t.tube(pts, rad, 10)
    top = pts[-1]
    kids = r.randint(3, 4); az0 = r.uniform(0, 6.28)
    for k in range(kids):
        az = az0 + k * 2 * math.pi / kids + r.uniform(-.3, .3)
        sp = r.uniform(0.45, 0.7)
        d = Vector((math.cos(az) * math.sin(sp), math.sin(az) * math.sin(sp), math.cos(sp)))
        t.branch(top.copy(), d, r.uniform(1.3, 1.8), 0.1, 0, 3)
    # canopy ellipsoid from the twig cloud
    tips = [p for p, _, dep in t.tips]
    cx = sum(p.x for p in tips) / len(tips); cy = sum(p.y for p in tips) / len(tips)
    zs = sorted(p.z for p in tips); cz = (zs[int(len(zs) * .1)] + zs[-1]) / 2 + 0.1
    rx = max(math.hypot(p.x - cx, p.y - cy) for p in tips) * 0.9 + 0.4
    rz = (zs[-1] - zs[int(len(zs) * .1)]) / 2 + 0.5
    centre = Vector((cx, cy, cz))
    t.foliage(centre, rx, rz, 760)
    return t, centre, rx, rz

def to_obj(bm, name, mat, normals=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if normals:
        me.normals_split_custom_set_from_vertices(normals)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    m = bpy.data.materials.get(mat) or bpy.data.materials.new(mat)
    me.materials.append(m)
    return ob

info = {}
for v in range(3):
    t, c, rx, rz = build(v)
    to_obj(t.bark, f'tree{v}_bark', 'tree_bark')
    to_obj(t.leaf, f'tree{v}_leaves', 'tree_leaves', t.lnorm)
    info[v] = (tuple(round(x, 3) for x in c), round(rx, 3), round(rz, 3))
    print('variant', v, info[v], len(bpy.data.objects[f'tree{v}_bark'].data.polygons), len(bpy.data.objects[f'tree{v}_leaves'].data.polygons))

bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'cx-trees.glb'), export_format='GLB', export_image_format='NONE',
                          export_normals=True, export_apply=False, export_yup=True)
import json
json.dump({str(k): {'centre': v[0], 'rx': v[1], 'rz': v[2]} for k, v in info.items()}, open(os.path.join(OUT, 'cx-trees.json'), 'w'))

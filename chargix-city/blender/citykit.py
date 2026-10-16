"""Mesh-building kit for the CHARGIX city: accumulates faces per material, then emits Blender objects.

All units are metres, Blender axes (Z up, +Y north). UV0 is world-scale (1 UV unit = 1 m) so the runtime can tile
textures by physical size. UV1 is optional per-face data (window-local coords, ids) used by custom shaders.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix
from collections import defaultdict
from contextlib import contextmanager


class MB:
    def __init__(self):
        self.parts = defaultdict(lambda: {'v': [], 'f': [], 'uv': [], 'uv2': [], 'smooth': []})
        self.M = Matrix.Identity(4)
        self.stack = []

    @contextmanager
    def xf(self, m):
        self.stack.append(self.M)
        self.M = self.M @ m
        try:
            yield
        finally:
            self.M = self.stack.pop()

    def _add(self, mat, pts, uvs=None, uv2=None, smooth=False, share=None):
        P = self.parts[mat]
        base = len(P['v'])
        P['v'].extend(self.M @ Vector(p) for p in pts)
        return base

    # -- primitive faces ------------------------------------------------------------------------------------
    def poly(self, mat, pts, uv2=None, smooth=False, uvmode='auto', uvscale=1.0):
        """Single n-gon from local points (counter-clockwise seen from the front)."""
        P = self.parts[mat]
        wp = [self.M @ Vector(p) for p in pts]
        base = len(P['v'])
        P['v'].extend(wp)
        P['f'].append(tuple(range(base, base + len(wp))))
        n = (wp[1] - wp[0]).cross(wp[2] - wp[0])
        if n.length < 1e-12 and len(wp) > 3:
            n = (wp[2] - wp[0]).cross(wp[3] - wp[0])
        P['uv'].append([self._uv(p, n, uvmode, uvscale) for p in wp])
        P['uv2'].append(uv2 if uv2 else [(0.0, 0.0)] * len(wp))
        P['smooth'].append(smooth)

    @staticmethod
    def _uv(p, n, mode, s):
        if mode == 'auto':
            ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
            if az >= ax and az >= ay:
                return (p.x * s, p.y * s)
            if ax >= ay:
                return ((p.y if n.x > 0 else -p.y) * s, p.z * s)
            return ((-p.x if n.y > 0 else p.x) * s, p.z * s)
        return mode(p, n)

    def quad(self, mat, a, b, c, d, **kw):
        self.poly(mat, [a, b, c, d], **kw)

    def box(self, mat, x0, y0, z0, x1, y1, z1, skip=(), **kw):
        """Axis-aligned box. skip: subset of {'-x','+x','-y','+y','-z','+z'}."""
        F = {
            '-y': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            '+y': [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
            '-x': [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
            '+x': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
            '+z': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
            '-z': [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
        }
        for k, pts in F.items():
            if k not in skip:
                self.poly(mat, pts, **kw)

    def cyl(self, mat, cx, cy, z0, z1, r, seg=16, caps=(True, True), r1=None, smooth=True):
        """Vertical cylinder / cone frustum with shared side vertices (smooth)."""
        r1 = r if r1 is None else r1
        P = self.parts[mat]
        base = len(P['v'])
        ring0 = [self.M @ Vector((cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg), z0)) for i in range(seg)]
        ring1 = [self.M @ Vector((cx + r1 * math.cos(2 * math.pi * i / seg), cy + r1 * math.sin(2 * math.pi * i / seg), z1)) for i in range(seg)]
        P['v'].extend(ring0 + ring1)
        circ = 2 * math.pi * max(r, r1)
        for i in range(seg):
            j = (i + 1) % seg
            P['f'].append((base + i, base + j, base + seg + j, base + seg + i))
            u0, u1 = circ * i / seg, circ * (i + 1) / seg
            P['uv'].append([(u0, z0), (u1, z0), (u1, z1), (u0, z1)])
            P['uv2'].append([(0, 0)] * 4)
            P['smooth'].append(smooth)
        if caps[1]:
            P['f'].append(tuple(base + seg + i for i in range(seg)))
            P['uv'].append([(v.x, v.y) for v in ring1]); P['uv2'].append([(0, 0)] * seg); P['smooth'].append(False)
        if caps[0]:
            P['f'].append(tuple(base + i for i in reversed(range(seg))))
            P['uv'].append([(v.x, v.y) for v in reversed(ring0)]); P['uv2'].append([(0, 0)] * seg); P['smooth'].append(False)

    def tube(self, mat, a, b, r, seg=8, caps=True):
        """Cylinder between two arbitrary points."""
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        m = Matrix.Translation(a) @ q.to_matrix().to_4x4()
        with self.xf(m):
            self.cyl(mat, 0, 0, 0, L, r, seg, (caps, caps))

    def sphere(self, mat, c, r, seg=16, rings=10, scale=(1, 1, 1), smooth=True, noise_fn=None):
        P = self.parts[mat]
        base = len(P['v'])
        verts = []
        for j in range(rings + 1):
            th = math.pi * j / rings
            for i in range(seg):
                ph = 2 * math.pi * i / seg
                d = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
                rr = r * (1 + (noise_fn(d) if noise_fn else 0))
                verts.append(self.M @ Vector((c[0] + d.x * rr * scale[0], c[1] + d.y * rr * scale[1], c[2] + d.z * rr * scale[2])))
        P['v'].extend(verts)
        for j in range(rings):
            for i in range(seg):
                i2 = (i + 1) % seg
                a, b2 = base + j * seg + i, base + j * seg + i2
                c2, d2 = base + (j + 1) * seg + i2, base + (j + 1) * seg + i
                P['f'].append((a, d2, c2, b2))
                P['uv'].append([(i / seg * 2 * math.pi * r, -j / rings * math.pi * r), (i / seg * 2 * math.pi * r, -(j + 1) / rings * math.pi * r),
                                ((i + 1) / seg * 2 * math.pi * r, -(j + 1) / rings * math.pi * r), ((i + 1) / seg * 2 * math.pi * r, -j / rings * math.pi * r)])
                P['uv2'].append([(0, 0)] * 4)
                P['smooth'].append(smooth)

    # -- walls with rectangular openings (local frame: wall in the XZ plane at y, facing -Y) ---------------
    def wall(self, mat, x0, x1, z0, z1, y=0.0, holes=(), **kw):
        xs = sorted({x0, x1} | {h[0] for h in holes} | {h[1] for h in holes})
        for a, b in zip(xs, xs[1:]):
            if b - a < 1e-6:
                continue
            cover = sorted([(h[2], h[3]) for h in holes if h[0] <= a + 1e-6 and h[1] >= b - 1e-6])
            z = z0
            for hz0, hz1 in cover:
                if hz0 > z + 1e-6:
                    self.quad(mat, (a, y, z), (b, y, z), (b, y, hz0), (a, y, hz0), **kw)
                z = max(z, hz1)
            if z1 > z + 1e-6:
                self.quad(mat, (a, y, z), (b, y, z), (b, y, z1), (a, y, z1), **kw)

    def reveal(self, mat, h, y0, y1, sill_mat=None, skip_bottom=False):
        """Inner faces of an opening h=(x0,x1,z0,z1) from the wall face y0 back to y1 (y1 > y0)."""
        x0, x1, z0, z1 = h
        self.quad(mat, (x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1))       # left jamb faces +x
        self.quad(mat, (x1, y1, z0), (x1, y0, z0), (x1, y0, z1), (x1, y1, z1))       # right jamb faces -x
        self.quad(mat, (x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1))       # head faces -z
        if not skip_bottom:
            self.quad(sill_mat or mat, (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))  # sill faces +z

    # -- output -----------------------------------------------------------------------------------------
    def emit(self, prefix, collection=None, merge=True):
        objs = []
        for mat, P in self.parts.items():
            if not P['f']:
                continue
            me = bpy.data.meshes.new(f'{prefix}_{mat}')
            me.from_pydata([tuple(v) for v in P['v']], [], P['f'])
            uv = me.uv_layers.new(name='UVMap')
            uv2 = me.uv_layers.new(name='UV2')
            li = 0
            for fi, poly in enumerate(me.polygons):
                for k, l in enumerate(poly.loop_indices):
                    uv.data[l].uv = P['uv'][fi][k]
                    uv2.data[l].uv = P['uv2'][fi][k]
                poly.use_smooth = P['smooth'][fi]
            m = bpy.data.materials.get(mat) or bpy.data.materials.new(mat)
            me.materials.append(m)
            if merge:
                bm = bmesh.new(); bm.from_mesh(me)
                bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
                bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new(f'{prefix}_{mat}', me)
            (collection or bpy.context.scene.collection).objects.link(o)
            objs.append(o)
        self.parts.clear()
        return objs

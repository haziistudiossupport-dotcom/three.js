import bpy, sys, bmesh
sys.path.insert(0, '/home/claude/chargix-city/blender')
from render_util import *
bpy.ops.wm.open_mainfile(filepath='/home/claude/chargix-city/build/mh_probe.blend')
bm_obj = [o for o in bpy.data.objects if o.type=='MESH'][0]
# bake shape keys
HumanService, TargetService = mpfb()
TargetService.bake_targets(bm_obj)
for md in list(bm_obj.modifiers):
    if md.type=='MASK': bm_obj.modifiers.remove(md)
cols = {'body':(0.7,0.55,0.45),'helper-tights':(0.2,0.4,0.9),'helper-skirt':(0.9,0.3,0.2),'helper-hair':(0.2,0.8,0.3),'helper-l-eye':(1,1,1),'helper-r-eye':(1,1,1)}
info={}
for gname,col in cols.items():
    gi = bm_obj.vertex_groups[gname].index
    me = bm_obj.data
    verts = [v.index for v in me.vertices if any(g.group==gi and g.weight>0.5 for g in v.groups)]
    info[gname]=len(verts)
    o = bm_obj.copy(); o.data = bm_obj.data.copy(); bpy.context.scene.collection.objects.link(o)
    o.parent=None; o.modifiers.clear(); o.name = gname
    b = bmesh.new(); b.from_mesh(o.data)
    keep=set(verts)
    bmesh.ops.delete(b, geom=[v for v in b.verts if v.index not in keep], context='VERTS')
    b.to_mesh(o.data); b.free()
    m = bpy.data.materials.new(gname); m.use_nodes=True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(*col,1)
    if gname=='helper-skirt': m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value=0.4
    o.data.materials.clear(); o.data.materials.append(m)
    o.matrix_world = bm_obj.matrix_world
    o.location.x += {'body':-1.2,'helper-tights':0,'helper-skirt':1.2,'helper-hair':2.4,'helper-l-eye':-2.4,'helper-r-eye':-2.4}[gname]
bm_obj.hide_render=True
for o in bpy.data.objects:
    if o.type=='ARMATURE': o.hide_render=True
print(info)
ground(30); add_sun(); world_sky()
add_cam((0.6,-7.5,1.6),(0.6,0,0.95),lens=40)
setup_render('/tmp/claude-0/-home-claude/7fdae2aa-bab5-544e-a329-1c4bd93faf8f/scratchpad/mh_helpers.png', 1400, 600, 16)
bpy.ops.render.render(write_still=True)

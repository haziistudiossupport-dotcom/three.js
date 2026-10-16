import bpy, sys
sys.path.insert(0, '/home/claude/chargix-city/blender')
from render_util import *
bpy.ops.wm.open_mainfile(filepath='/home/claude/chargix-city/build/mh_probe.blend')
bm = [o for o in bpy.data.objects if o.type=='MESH'][0]
m = bpy.data.materials.new("skin"); m.use_nodes=True
b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value=(0.62,0.42,0.32,1); b.inputs["Roughness"].default_value=0.5
b.inputs["Subsurface Weight"].default_value=0.3; b.inputs["Subsurface Radius"].default_value=(1,0.4,0.25)
bm.data.materials.clear(); bm.data.materials.append(m)
ground()
add_sun(); world_sky()
add_cam((1.2,-3.6,1.4),(0,0,0.95),lens=60)
setup_render('/tmp/claude-0/-home-claude/7fdae2aa-bab5-544e-a329-1c4bd93faf8f/scratchpad/mh_look.png', 700, 700, 24)
bpy.ops.render.render(write_still=True)

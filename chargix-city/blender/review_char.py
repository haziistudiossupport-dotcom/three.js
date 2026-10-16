import bpy, sys, math
sys.path.insert(0, '/home/claude/chargix-city/blender')
from render_util import *
name = sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath='/home/claude/chargix-city/build/char_%s.blend' % name)
R='/tmp/claude-0/-home-claude/7fdae2aa-bab5-544e-a329-1c4bd93faf8f/scratchpad/review/'
ground(20, (0.42,0.42,0.42)); add_sun((55,0,35), 3.2); world_sky((0.6,0.66,0.75), 0.9)
shots = [('front',(0,-4.2,1.2),(0,0,0.92),55,(900,900)),('q34',(2.6,-3.0,1.5),(0,0,0.92),55,(900,900)),('back',(0.8,3.6,1.4),(0,0,0.92),55,(900,900)),('face',(0.25,-0.75,1.68),(0,0,1.62),85,(900,900))]
for nm,loc,tgt,lens,(w,h) in shots:
    add_cam(loc,tgt,lens,'C_'+nm)
    setup_render(R+'%s_%s.png'%(name,nm), w, h, 20)
    bpy.ops.render.render(write_still=True)

import bpy, math, mathutils
def setup_render(path, w=800, h=800, samples=32, engine='CYCLES'):
    sc = bpy.context.scene
    sc.render.engine = engine
    if engine == 'CYCLES':
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.device = 'CPU'
        sc.cycles.max_bounces = 4
    sc.render.resolution_x = w; sc.render.resolution_y = h
    sc.render.filepath = path
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX'
    return sc
def add_cam(loc, target, lens=50, name="CAM"):
    cd = bpy.data.cameras.new(name); co = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(co)
    co.location = loc
    d = mathutils.Vector(target) - mathutils.Vector(loc)
    co.rotation_euler = d.to_track_quat('-Z','Y').to_euler()
    cd.lens = lens
    bpy.context.scene.camera = co
    return co
def add_sun(rot=(50,0,30), energy=3.5, color=(1,0.96,0.9)):
    s = bpy.data.lights.new("SUN", 'SUN'); s.energy = energy; s.color = color; s.angle = math.radians(3)
    o = bpy.data.objects.new("SUN", s); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = tuple(math.radians(a) for a in rot)
    return o
def world_sky(color=(0.55,0.62,0.75), strength=0.8):
    sc = bpy.context.scene
    if sc.world is None: sc.world = bpy.data.worlds.new("W")
    w = sc.world; w.use_nodes = True
    bg = w.node_tree.nodes.get("Background"); bg.inputs[0].default_value = (*color,1); bg.inputs[1].default_value = strength
def ground(size=20, color=(0.5,0.5,0.5)):
    bpy.ops.mesh.primitive_plane_add(size=size)
    g = bpy.context.active_object
    m = bpy.data.materials.new("ground"); m.use_nodes=True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(*color,1)
    g.data.materials.append(m)
    return g
def mpfb():
    import addon_utils
    addon_utils.enable('bl_ext.user_default.mpfb', default_set=True, persistent=True)
    import importlib
    hs = importlib.import_module('bl_ext.user_default.mpfb.services.humanservice').HumanService
    ts = importlib.import_module('bl_ext.user_default.mpfb.services.targetservice').TargetService
    return hs, ts

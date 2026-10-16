"""Retarget the Mixamo clips that ship with three.js (Xbot.glb) onto an MPFB character rig and save them as actions.

Usage: python3 retarget.py -- <name>
Reads build/char_<name>.blend, writes build/char_<name>_anim.blend (rig + meshes + one action per clip).

Method: each source bone's world rotation is expressed as a delta from the source T-pose, then applied to the
target bone in the same T-pose (the target's A-pose is first swung into the source's rest directions), so the
different rest poses and bone rolls cancel out. Hips translation is scaled by the hip-height ratio.
"""
import bpy, sys, math
from mathutils import Matrix, Quaternion, Vector

name = sys.argv[sys.argv.index('--') + 1]
BUILD = '/home/claude/chargix-city/build'
SRC_GLB = '/home/claude/three.js/examples/models/gltf/Xbot.glb'
CLIPS = {'idle': 'idle', 'walk': 'walk', 'agree': 'nod', 'headShake': 'shake', 'run': 'run'}
FPS = 30

bpy.ops.wm.open_mainfile(filepath=f'{BUILD}/char_{name}.blend')
tgt = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bpy.ops.import_scene.gltf(filepath=SRC_GLB)
src = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o != tgt][0]
# drop the imported Xbot meshes, keep its armature for sampling
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.parent == src:
        bpy.data.objects.remove(o)
src_ad = src.animation_data
for tr in list(src_ad.nla_tracks):
    src_ad.nla_tracks.remove(tr)

sc = bpy.context.scene
IMPORT_FPS = sc.render.fps / sc.render.fps_base  # the glTF importer keys at the scene rate
sc.render.fps = FPS

bones = [b.name for b in tgt.data.bones]  # hierarchical order (parents first)
SW, TW = src.matrix_world, tgt.matrix_world
src_rest = {n: SW @ src.data.bones[n].matrix_local for n in bones}
tgt_rest = {n: TW @ tgt.data.bones[n].matrix_local for n in bones}

# target bone world rotations when swung into the source's rest directions (T-pose). Bone axes differ between the
# rigs (the glTF importer points every Xbot bone up), so directions come from joint positions: head -> chosen child head.
PREF = {'mixamorig:Hips': 'mixamorig:Spine', 'mixamorig:Spine2': 'mixamorig:Neck',
        'mixamorig:LeftHand': 'mixamorig:LeftHandMiddle1', 'mixamorig:RightHand': 'mixamorig:RightHandMiddle1'}
def joint_dir(arm, M, n):
    b = arm.data.bones[n]
    kids = [c.name for c in b.children if c.name in bones]
    if not kids:
        return None
    c = PREF.get(n, kids[0])
    return ((M @ arm.data.bones[c].matrix_local).translation - (M @ b.matrix_local).translation).normalized()
swing = {}
tgt_T = {}
for n in bones:
    dt, ds = joint_dir(tgt, TW, n), joint_dir(src, SW, n)
    if dt is not None and ds is not None:
        swing[n] = dt.rotation_difference(ds)
    else:
        par = tgt.data.bones[n].parent
        swing[n] = swing[par.name] if par else Quaternion()
    tgt_T[n] = swing[n] @ tgt_rest[n].to_quaternion()

hip_ratio = tgt_rest['mixamorig:Hips'].translation.z / src_rest['mixamorig:Hips'].translation.z
TWi = TW.inverted()


def sample(action, out_name):
    src_ad.action = action
    if hasattr(src_ad, 'action_slot') and action.slots:
        src_ad.action_slot = action.slots[0]
    f0, f1 = action.frame_range
    dur = (f1 - f0) / IMPORT_FPS
    nframes = max(2, int(round(dur * FPS)) + 1)
    act = bpy.data.actions.new(out_name)
    tgt.animation_data_create()
    tgt.animation_data.action = act
    for pb in tgt.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    for k in range(nframes):
        t = k / FPS
        fs = f0 + t * IMPORT_FPS
        sc.frame_set(int(math.floor(fs)), subframe=fs - math.floor(fs))
        desired = {}
        for n in bones:
            Ws = SW @ src.pose.bones[n].matrix
            delta = Ws.to_quaternion() @ src_rest[n].to_quaternion().inverted()
            rot = delta @ tgt_T[n]
            b = tgt.data.bones[n]
            if b.parent is None:
                dp = Ws.translation - src_rest[n].translation
                pos = tgt_rest[n].translation + dp * hip_ratio
            else:
                pw = desired[b.parent.name]
                off = tgt.data.bones[b.parent.name].matrix_local.inverted() @ b.matrix_local
                pos = (pw @ off).translation
            desired[n] = Matrix.Translation(pos) @ rot.to_matrix().to_4x4()
        for n in bones:
            pb = tgt.pose.bones[n]; b = pb.bone
            M = TWi @ desired[n]
            if b.parent is None:
                basis = b.matrix_local.inverted() @ M
            else:
                PM = TWi @ desired[b.parent.name]
                basis = (PM @ b.parent.matrix_local.inverted() @ b.matrix_local).inverted() @ M
            loc, q, _ = basis.decompose()
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=k + 1)
            if b.parent is None:
                pb.location = loc
                pb.keyframe_insert('location', frame=k + 1)
    act.use_fake_user = True
    print('CLIP', out_name, nframes, 'frames')
    return act


made = []
srcacts = {}
for a in list(bpy.data.actions):
    srcacts[a.name] = a
    a.name = 'src_' + a.name
for sname, oname in CLIPS.items():
    made.append(sample(srcacts[sname], oname))

# park each clip on its own NLA track so the glTF exporter writes them all
tgt.animation_data.action = None
for act in made:
    tr = tgt.animation_data.nla_tracks.new(); tr.name = act.name
    tr.strips.new(act.name, 1, act)
    tr.mute = True

bpy.data.objects.remove(src)
for a in list(bpy.data.actions):
    if a not in made:
        bpy.data.actions.remove(a)
bpy.ops.wm.save_as_mainfile(filepath=f'{BUILD}/char_{name}_anim.blend')
print('SAVED')

# ---------------------------------------------------------------- export rig + meshes + clips
for o in bpy.data.objects:
    o.select_set(o.type in ('MESH', 'ARMATURE'))
for tr in tgt.animation_data.nla_tracks:
    tr.mute = False
bpy.ops.export_scene.gltf(filepath=f'{BUILD}/char_{name}.glb', export_format='GLB', use_selection=True, export_skins=True,
                          export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
                          export_frame_step=1, export_yup=True, export_apply=False, export_image_format='WEBP',
                          export_image_quality=82, export_vertex_color='NONE', export_def_bones=True)
print('EXPORTED')

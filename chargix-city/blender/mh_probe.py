import bpy, sys, json, math
import addon_utils
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
addon_utils.enable('bl_ext.user_default.mpfb', default_set=True, persistent=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
macro = TargetService.get_default_macro_info_dict()
macro.update({"gender":1.0,"age":0.5,"muscle":0.55,"weight":0.5,"height":0.55,"proportions":0.6})
macro["race"] = {"caucasian":0.5,"asian":0.3,"african":0.2}
bm = HumanService.create_human(macro_detail_dict=macro)
rig = HumanService.add_builtin_rig(bm, "mixamo")
out = {"verts": len(bm.data.vertices), "vgroups": [g.name for g in bm.vertex_groups][:400], "bones": [b.name for b in rig.data.bones], "dims": list(bm.dimensions), "shape_keys": [k.name for k in bm.data.shape_keys.key_blocks] if bm.data.shape_keys else []}
json.dump(out, open('/home/claude/chargix-city/build/mh_probe.json','w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath='/home/claude/chargix-city/build/mh_probe.blend')
print("OK", out["verts"], out["dims"], len(out["bones"]))

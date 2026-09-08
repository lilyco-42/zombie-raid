import bpy

p = r"C:\Users\liuqi\dev\fps-chaf\assets\vendor\kaykit\KayKit-Character-Pack-Skeletons-1.0\addons\kaykit_character_pack_skeletons\Characters\gltf\Skeleton_Minion.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=p)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("=== BONES ===")
for b in arm.data.bones:
    print("BONE", b.name, "| parent=", b.parent.name if b.parent else None,
          "| head=", tuple(round(v, 2) for v in b.head_local))
print("=== EMPTIES / OTHERS ===")
for o in bpy.data.objects:
    if o.type == "EMPTY":
        print("EMPTY", o.name, "| parent=", o.parent.name if o.parent else None,
              "| parent_bone=", o.parent_bone)

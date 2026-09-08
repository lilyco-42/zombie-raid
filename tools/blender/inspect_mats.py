import bpy

p = r"C:\Users\liuqi\dev\fps-chaf\assets\vendor\kaykit\KayKit-Character-Pack-Skeletons-1.0\addons\kaykit_character_pack_skeletons\Characters\gltf\Skeleton_Minion.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=p)
print("=== OBJECTS ===")
for o in bpy.data.objects:
    print("OBJ", o.type, o.name)
print("=== MATERIALS ===")
for m in bpy.data.materials:
    if not m.use_nodes:
        print("MAT", m.name, "no-nodes")
        continue
    kinds = sorted({n.bl_idname for n in m.node_tree.nodes})
    print("MAT", m.name, kinds)
    for n in m.node_tree.nodes:
        if n.bl_idname == "ShaderNodeBsdfPrincipled":
            bc = n.inputs["Base Color"]
            em = n.inputs["Emission Color"]
            es = n.inputs["Emission Strength"]
            print("   basecol_linked=", bc.is_linked,
                  "emiss=", tuple(round(v, 2) for v in em.default_value),
                  "estr=", es.default_value)
print("=== ACTIONS ===")
for a in bpy.data.actions:
    print("ACT", a.name)

"""Generate a warehouse-combat map as GLB for Godot.

Run: blender --background --python generate_warehouse_map.py

Layout: 50x50 ground, shipping-container clusters as cover, perimeter walls,
two watchtower platforms, ramps. Flat-shaded low-poly.
"""
import bpy

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

MATS = {}

def make_mat(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.8
    MATS[name] = mat
    return mat

make_mat("ground", (0.35, 0.37, 0.40))
make_mat("wall", (0.55, 0.56, 0.60))
make_mat("container_red", (0.55, 0.16, 0.12))
make_mat("container_blue", (0.13, 0.28, 0.50))
make_mat("container_green", (0.15, 0.42, 0.28))
make_mat("metal", (0.30, 0.32, 0.36))
make_mat("wood", (0.42, 0.30, 0.18))

def make_box(name, loc, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    obj.data.materials.append(MATS[mat])
    bpy.ops.object.shade_flat()
    return obj

# Ground 50x50
make_box("Ground", (0, 0, -0.5), (50, 50, 1), "ground")

# Perimeter walls
make_box("Wall_N", (0, -25, 2), (52, 1, 5), "wall")
make_box("Wall_S", (0, 25, 2), (52, 1, 5), "wall")
make_box("Wall_E", (-25, 0, 2), (1, 52, 5), "wall")
make_box("Wall_W", (25, 0, 2), (1, 52, 5), "wall")

# Shipping containers (2.5 x 2.5 x 6 units) in combat clusters
containers = [
    # west cluster
    ("C1", (-12, -10, 1.25), (6, 2.5, 2.5), "container_red"),
    ("C2", (-12, -4, 1.25), (6, 2.5, 2.5), "container_blue"),
    ("C3", (-15, -7, 3.75), (2.5, 2.5, 2.5), "container_green"),
    # east cluster
    ("C4", (12, 8, 1.25), (6, 2.5, 2.5), "container_green"),
    ("C5", (12, 14, 1.25), (6, 2.5, 2.5), "container_red"),
    ("C6", (15, 11, 3.75), (2.5, 2.5, 2.5), "container_blue"),
    # center cover
    ("C7", (0, 0, 1.25), (6, 2.5, 2.5), "container_blue"),
    ("C8", (-4, 2, 1.25), (2.5, 2.5, 2.5), "container_red"),
    ("C9", (4, -2, 1.25), (2.5, 2.5, 2.5), "container_green"),
    # north lane
    ("C10", (-8, 16, 1.25), (6, 2.5, 2.5), "container_red"),
    ("C11", (8, -16, 1.25), (6, 2.5, 2.5), "container_blue"),
]
for name, loc, size, mat in containers:
    make_box(name, loc, size, mat)

# Watchtower platforms (corner NE & SW)
for tag, (x, y) in {"T1": (18, -18), "T2": (-18, 18)}.items():
    make_box(f"{tag}_LegA", (x-2, y-2, 2), (0.5, 0.5, 4), "metal")
    make_box(f"{tag}_LegB", (x+2, y-2, 2), (0.5, 0.5, 4), "metal")
    make_box(f"{tag}_LegC", (x-2, y+2, 2), (0.5, 0.5, 4), "metal")
    make_box(f"{tag}_LegD", (x+2, y+2, 2), (0.5, 0.5, 4), "metal")
    make_box(f"{tag}_Deck", (x, y, 4.25), (6, 5, 0.5), "wood")

# Ramps up to the towers
make_box("Ramp1", (18, -13.5, 2.0), (2, 7, 0.4), "metal")
bpy.context.active_object.rotation_euler.x = -0.55
make_box("Ramp2", (-18, 13.5, 2.0), (2, 7, 0.4), "metal")
bpy.context.active_object.rotation_euler.x = -0.55

# Player spawn clearing marker (just a visual pad)
make_box("SpawnPad", (0, 20, 0.05), (3, 3, 0.1), "metal")

# Apply scale
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

bpy.ops.export_scene.gltf(
    filepath="C:/Users/liuqi/dev/fps-chaf/assets/maps/warehouse.glb",
    export_format='GLB',
    use_selection=False,
)
print("=== WAREHOUSE MAP EXPORT DONE ===")

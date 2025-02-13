import bpy
import os
import random
import mathutils

# ---------------------------------------------------
# 0) Basic scene cleanup except for the Camera
# ---------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
camera = bpy.data.objects.get('Camera')
if camera:
    camera.select_set(False)  # Deselect the camera to prevent deletion
bpy.ops.object.delete(use_global=False)

# ---------------------------------------------------
# 1) Create a collision plane
# ---------------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
plane = bpy.context.active_object
plane.name = "CollisionPlane"

# Add a Collision modifier so that soft bodies can collide with this plane
bpy.ops.object.modifier_add(type='COLLISION')
plane.collision.thickness_outer = 0.02
plane.collision.damping = 0.5

# ---------------------------------------------------
# 2) Set up lighting
# ---------------------------------------------------
bpy.ops.object.light_add(type='POINT', location=(5, 5, 5))
bpy.ops.object.light_add(type='POINT', location=(-5, -5, 5))
bpy.ops.object.light_add(type='AREA', location=(0, 0, 10))
bpy.data.lights['Point'].energy = 1000
bpy.data.lights['Point.001'].energy = 1000
bpy.data.lights['Area'].energy = 500

# ---------------------------------------------------
# 3) Define directories for ECS and cell meshes
# ---------------------------------------------------
cells_dir = "/Users/ackermand/Documents/programming/blender/cello/meshes/cells"
ecs_dir   = "/Users/ackermand/Documents/programming/blender/cello/meshes/ecs"

# Colors
matrix_color = (0.2, 0.2, 0.8, 1)  # Blue color for ECS (matrix)
cell_color   = (0.8, 0.2, 0.2, 1) # Red color for cells

# Lists to keep track of imported objects
all_objects = []
ecs_objects = []
cell_objects = []

# ---------------------------------------------------
# 4) Load ECS meshes (now set as soft bodies)
# ---------------------------------------------------
for filename in os.listdir(ecs_dir):
    if filename.endswith(".ply"):
        bpy.ops.wm.ply_import(filepath=os.path.join(ecs_dir, filename))
        obj = bpy.context.selected_objects[0]
        obj.name = f"ECS_{filename}"
        all_objects.append(obj)
        ecs_objects.append(obj)

        # --- Create a metallic, shiny material for ECS ---
        mat = bpy.data.materials.new(name="MatrixMaterial")
        mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        # Remove default nodes
        for node in nodes:
            nodes.remove(node)

        # Add Principled BSDF
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf.inputs['Base Color'].default_value = matrix_color  # ECS color
        bsdf.inputs['Metallic'].default_value   = 1.0           # Fully metallic
        bsdf.inputs['Roughness'].default_value  = 0.2           # Low roughness for shine

        # Output node
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])

        # Assign the material & set a diffuse_color for viewport
        mat.diffuse_color = matrix_color
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()

        # Recalculate normals
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Apply transforms
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ---------------------------------------------------
# 5) Load cell meshes (also as soft bodies)
# ---------------------------------------------------
for filename in os.listdir(cells_dir):
    if filename.endswith(".ply"):
        bpy.ops.wm.ply_import(filepath=os.path.join(cells_dir, filename))
        obj = bpy.context.selected_objects[0]
        obj.name = f"Cell_{filename}"
        all_objects.append(obj)
        cell_objects.append(obj)

        # --- Create a rough, subsurface material for Cells ---
        mat = bpy.data.materials.new(name="CellMaterial")
        mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        # Remove default nodes
        for node in nodes:
            nodes.remove(node)

        # Add Principled BSDF
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf.inputs['Base Color'].default_value   = cell_color    # Cell color
        bsdf.inputs['Roughness'].default_value    = 0.8           # Rough, diffuse
        bsdf.inputs['Subsurface Weight'].default_value   = 0.3           # Subsurface factor
        bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.2, 0.2)  # R,G,B scattering

        # Output node
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])

        # Optional: Set for viewport
        mat.diffuse_color = cell_color
        obj.data.materials.append(mat)
        bpy.ops.object.shade_smooth()

        # Recalculate normals
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Apply transforms
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


# ---------------------------------------------------
# 6) Compute a bounding box for the ECS objects (for uniform scaling)
# ---------------------------------------------------
if ecs_objects:
    ecs_min_x, ecs_min_y, ecs_min_z = float('inf'), float('inf'), float('inf')
    ecs_max_x, ecs_max_y, ecs_max_z = float('-inf'), float('-inf'), float('-inf')

    for obj in ecs_objects:
        for vertex in obj.bound_box:
            world_vertex = obj.matrix_world @ mathutils.Vector(vertex)
            ecs_min_x = min(ecs_min_x, world_vertex.x)
            ecs_min_y = min(ecs_min_y, world_vertex.y)
            ecs_min_z = min(ecs_min_z, world_vertex.z)
            ecs_max_x = max(ecs_max_x, world_vertex.x)
            ecs_max_y = max(ecs_max_y, world_vertex.y)
            ecs_max_z = max(ecs_max_z, world_vertex.z)

    ecs_size_x = ecs_max_x - ecs_min_x
    ecs_size_y = ecs_max_y - ecs_min_y
    ecs_size_z = ecs_max_z - ecs_min_z

    # Determine scaling factor to make smallest ECS dimension = 1
    min_dimension = min(ecs_size_x, ecs_size_y, ecs_size_z)
    scaling_factor = 1.0
    if min_dimension > 0:
        scaling_factor = 1.0 / min_dimension

    # Rescale all imported objects (ECS + cells) by the same factor
    for obj in all_objects:
        obj.scale *= scaling_factor

    # Recompute the ECS bounding box center after scaling
    ecs_center_x = (ecs_min_x + ecs_max_x) / 2 * scaling_factor
    ecs_center_y = (ecs_min_y + ecs_max_y) / 2 * scaling_factor
    ecs_center_z = (ecs_min_z + ecs_max_z) / 2 * scaling_factor

    # Shift all objects so ECS is roughly centered at (0, 0, 0)
    for obj in all_objects:
        obj.location.x -= ecs_center_x
        obj.location.y -= ecs_center_y
        obj.location.z -= ecs_center_z

# ---------------------------------------------------
# 7) Randomize starting positions above the plane
# ---------------------------------------------------
for obj in all_objects:
    # Randomize X, Y in some range, and Z above the plane (e.g., between 1 and 2)
    obj.location = (
        random.uniform(-2, 2),
        random.uniform(-2, 2),
        random.uniform(1, 2)
    )

# ---------------------------------------------------
# 8) Add Soft Body physics to all ECS and cell objects
#    (less squishy + more substeps to reduce choppiness)
# ---------------------------------------------------
for obj in all_objects:
    bpy.context.view_layer.objects.active = obj
    
    # Add Soft Body modifier
    bpy.ops.object.modifier_add(type='SOFT_BODY')
    sb_mod = obj.modifiers["Softbody"]
    
    # Make sure we enable object collisions (if you want collision with plane)
    # sb_mod.collision_settings.use_collision = True
    
    # Enable 'edges' so the mesh holds its shape better
    sb_mod.settings.use_edges = True

    # Increase stiffness for a jello-like feel (less “squishy”)
    sb_mod.settings.goal_spring   = 1.0
    sb_mod.settings.goal_default  = 0.7
    sb_mod.settings.goal_max      = 0.2
    sb_mod.settings.bend          = 5.0
    sb_mod.settings.pull          = 0.9
    sb_mod.settings.push          = 0.9
    sb_mod.settings.friction      = 0.2
    sb_mod.settings.use_goal      = True

    # Some friction & damping for stability
    sb_mod.settings.goal_friction = 0.1

# ---------------------------------------------------
# 9) Scene & physics settings
# ---------------------------------------------------
# Set scene frames
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end   = 100

# Gravity
bpy.context.scene.gravity = (0, 0, -9.81)

# If you do have a rigidbody world, you can boost substeps:
if bpy.context.scene.rigidbody_world:
    bpy.context.scene.rigidbody_world.substeps_per_frame  = 8
    bpy.context.scene.rigidbody_world.solver_iterations   = 8

# ---------------------------------------------------
# 10) Bake Soft Body simulation for smooth playback/render
# ---------------------------------------------------
# Clear existing caches
bpy.ops.ptcache.free_bake_all()

# Ensure each object's Soft Body cache aligns with our scene frames
for obj in all_objects:
    if "Softbody" in obj.modifiers:
        sb_mod = obj.modifiers["Softbody"]
        sb_mod.point_cache.frame_start = bpy.context.scene.frame_start
        sb_mod.point_cache.frame_end   = bpy.context.scene.frame_end

# Bake all Soft Body caches
bpy.ops.ptcache.bake_all()

# ---------------------------------------------------
# 11) Render settings
# ---------------------------------------------------
bpy.context.scene.render.image_settings.file_format = 'PNG'
output_path = "/Users/ackermand/Documents/programming/blender/cello/output/frames_falling/"

# Remove old file if it exists
# if os.path.exists(output_path):
#     os.remove(output_path)

# Example of saving each frame as PNG (uncomment for real use):
bpy.context.scene.render.filepath = output_path
# bpy.context.scene.render.ffmpeg.format = 'MPEG4'
# bpy.context.scene.render.ffmpeg.codec = 'H264'
# bpy.context.scene.render.ffmpeg.constant_rate_factor = 'HIGH'
# bpy.context.scene.render.ffmpeg.ffmpeg_preset = 'GOOD'

# ---------------------------------------------------
# 12) Render the animation (uncomment to run)
# ---------------------------------------------------
# bpy.ops.render.render(animation=True)

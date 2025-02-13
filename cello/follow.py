import bpy
import os
import mathutils

def get_vertex_center(obj):
    """Returns the geometric center of an object's vertices in world coordinates."""
    if not obj or obj.type != 'MESH':
        return None  # Only works for mesh objects
    
    # Ensure the object has mesh data
    mesh = obj.data
    
    # Calculate the average position of all vertices in world space
    vertex_sum = mathutils.Vector((0, 0, 0))
    num_vertices = len(mesh.vertices)

    if num_vertices == 0:
        return None  # Prevent division by zero if object has no vertices

    for vert in mesh.vertices:
        world_vert = obj.matrix_world @ vert.co  # Convert local coordinates to world space
        vertex_sum += world_vert
    
    return vertex_sum / num_vertices  # Compute the average position (center)


# ---------------------------------------------------
# 0) Basic scene cleanup except for the Camera
# ---------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
camera = bpy.data.objects.get('Camera')
if camera:
    camera.select_set(False)  # Deselect the camera to prevent deletion
bpy.ops.object.delete(use_global=False)

# Turn off gravity
bpy.context.scene.use_gravity = False

# ---------------------------------------------------
# 1) (Optional) Create a collision plane (commented out)
# ---------------------------------------------------
# bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
# plane = bpy.context.active_object
# plane.name = "CollisionPlane"
# bpy.ops.object.modifier_add(type='COLLISION')
# plane.collision.thickness_outer = 0.02
# plane.collision.damping = 0.5

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
# 4) Load ECS meshes (they will be collision objects)
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
# 5) Load cell meshes (these will be soft bodies)
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
        bsdf.inputs['Base Color'].default_value = cell_color    # Cell color
        bsdf.inputs['Roughness'].default_value  = 0.8           # Rough, diffuse
        bsdf.inputs['Subsurface Weight'].default_value = 0.3    # Subsurface factor
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
# 7) Create a path for each cell from its initial location
#    to (x*10, y*10, z) over 100 frames using Follow Path
# ---------------------------------------------------
frames = 240
for i, obj in enumerate(cell_objects):
    true_center = get_vertex_center(obj)
    original_location = obj.location.copy()
    final_location = true_center - original_location
    # Create a new curve (poly line with 2 points)
    curve_data = bpy.data.curves.new(name=f"CellPath_{i}", type='CURVE')
    curve_data.dimensions = '3D'
    print(obj.name, true_center, final_location, original_location)
    spline = curve_data.splines.new('POLY')
    spline.points.add(1)  # 2 points: start and end
    spline.points[0].co = (0,0,0, 1)
    spline.points[1].co = (true_center[0]*2, true_center[1]*2, 0, 1)

    # Create an object from the curve data and link it to the scene
    curve_obj = bpy.data.objects.new(f"CellPathObj_{i}", curve_data)
    bpy.context.collection.objects.link(curve_obj)

    # Add a Follow Path constraint to the cell
    follow_path_con = obj.constraints.new('FOLLOW_PATH')
    follow_path_con.target = curve_obj
    follow_path_con.use_fixed_location = True
    #follow_path_con.use_path = True  # Ensure it follows the path properly

    # Ensure Blender updates scene dependencies
    bpy.context.view_layer.update()

    # Animate the offset_factor from 0.0 to 1.0 across 100 frames
    bpy.context.scene.frame_set(1)
    follow_path_con.offset_factor = 0.0
    follow_path_con.keyframe_insert(data_path="offset_factor", frame=1)

    bpy.context.scene.frame_set(frames)
    follow_path_con.offset_factor = 1.0
    follow_path_con.keyframe_insert(data_path="offset_factor", frame=frames)

# Make sure all updates are applied
bpy.context.view_layer.update()


# ---------------------------------------------------
# 8) ECS as Collision objects
# ---------------------------------------------------
for obj in ecs_objects:
    bpy.context.view_layer.objects.active = obj
    # Add a Collision modifier so soft-body Cells can collide with ECS
    bpy.ops.object.modifier_add(type='COLLISION')
    obj.collision.thickness_outer = 0.02
    obj.collision.damping = 0.5

# ---------------------------------------------------
# 9) Cells as Soft Bodies (with collisions enabled)
# ---------------------------------------------------
for obj in cell_objects:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_add(type='SOFT_BODY')
    sb_mod = obj.modifiers["Softbody"]

    # Make sure collisions are considered
    # sb_mod.collision_settings.use_collision = True

    # Basic shape retention & softness
    sb_mod.settings.use_edges       = True
    sb_mod.settings.use_goal        = True
    sb_mod.settings.goal_spring     = 0.2   
    sb_mod.settings.goal_default    = 0.2   
    sb_mod.settings.goal_max        = 0.1   
    sb_mod.settings.goal_friction   = 0.1
    sb_mod.settings.bend            = 0.5   
    sb_mod.settings.pull            = 0.2   
    sb_mod.settings.push            = 0.2   
    sb_mod.settings.friction        = 0.1   

# ---------------------------------------------------
# 10) Set up scene, bake, and prepare to render
# ---------------------------------------------------
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end   = frames  # Only 100 frames now

# # Clear existing caches
bpy.ops.ptcache.free_bake_all()

# Ensure each cell's Soft Body cache matches our 1→100 frames
for obj in cell_objects:
    sb_mod = obj.modifiers["Softbody"]
    sb_mod.point_cache.frame_start = bpy.context.scene.frame_start
    sb_mod.point_cache.frame_end   = bpy.context.scene.frame_end

# Bake all Soft Body caches
bpy.ops.ptcache.bake_all()

# Rendering parameters (optional)
bpy.context.scene.render.image_settings.file_format = 'PNG'
output_path = "/Users/ackermand/Documents/programming/blender/cello/output/frames_follow_softer_extended/"
bpy.context.scene.render.filepath = output_path

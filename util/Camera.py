import bpy
from mathutils import Vector
from typing import List, Optional

from property_groups import AnimationSetPropertyGroup
from util.Bounds import Bounds2D
import utils

####################################################################################
# Public methods: same as private but don't return the Bounds object
####################################################################################

def fit_camera_to_targets(context: bpy.types.Context):
    props = context.scene.SpritesheetPropertyGroup
    camera = props.camera_options.render_camera
    camera_obj = props.camera_options.render_camera_obj

    bounds = _find_camera_target_bounds(context, context.scene)
    _adjust_camera_based_on_bounds(context, camera, camera_obj, bounds)

def optimize_for_animation_set(context: bpy.types.Context, animation_set: Optional[AnimationSetPropertyGroup]):
    props = context.scene.SpritesheetPropertyGroup
    camera = props.camera_options.render_camera
    camera_obj = props.camera_options.render_camera_obj

    bounds = _optimal_bounds_for_animation_set(context, animation_set)
    _adjust_camera_based_on_bounds(context, camera, camera_obj, bounds)

def optimize_for_all_frames(context: bpy.types.Context, rotations_degrees: List[Optional[int]], animation_sets: List[AnimationSetPropertyGroup]):
    props = context.scene.SpritesheetPropertyGroup
    camera = props.camera_options.render_camera
    camera_obj = props.camera_options.render_camera_obj

    bounds = _optimize_for_all_frames(context, camera, rotations_degrees, animation_sets)
    _adjust_camera_based_on_bounds(context, camera, camera_obj, bounds)

def optimize_for_rotation(context: bpy.types.Context, rotation_degrees: List[Optional[int]], animation_sets: List[AnimationSetPropertyGroup]):
    props = context.scene.SpritesheetPropertyGroup
    camera = props.camera_options.render_camera
    camera_obj = props.camera_options.render_camera_obj

    bounds = _optimize_for_rotation(context, camera, rotation_degrees, animation_sets)
    _adjust_camera_based_on_bounds(context, camera, camera_obj, bounds)

####################################################################################
# Internal methods: all return Bounds so they can call each other usefully
####################################################################################

def _adjust_camera_based_on_bounds(context: bpy.types.Context, camera: bpy.types.Camera, camera_obj: bpy.types.Object, bounds: Bounds2D):
    # Bounds are in camera space; convert back to world
    cam_space_center = bounds.center_3d
    world_space_center = camera_obj.rotation_euler.to_matrix() @ cam_space_center

    # Camera position needs to be moved away from the target objects; since it's orthographic,
    # it doesn't matter how far we move, as long as the targets stay in our clipping planes
    cam_dir = Vector( (0, 0, 1) ) # default camera orientation
    cam_dir.rotate(camera_obj.rotation_euler)

    camera_obj.location = world_space_center + 10 * cam_dir
    camera.ortho_scale = _calculate_ortho_scale(context, bounds)

def _calculate_ortho_scale(context: bpy.types.Context, cam_space_bounds: Bounds2D) -> float:
    props = context.scene.SpritesheetPropertyGroup

    # max(cam_space_bounds.size) will give us an accurate ortho scale if we're rendering in a square
    # aspect ratio, but if we're not, we may need to adjust.
    render_size = Vector( (props.sprite_size[0], props.sprite_size[1]) )

    # Make the smallest dimension 1, and all others relative to it
    render_scale = (1 / min(render_size)) * render_size

    # Multiply each size by the other dimension, representing the true ortho scale needed to capture the whole object in that direction
    size = Vector( (cam_space_bounds.size[0] * render_scale[1], cam_space_bounds.size[1] * render_scale[0] ) )

    # Consider adding a small fudge factor in future in case the edges are being clipped
    return max(size)

def _optimal_bounds_for_animation_set(context: bpy.types.Context, animation_set: AnimationSetPropertyGroup):
    return _find_bounding_box_for_animation_set(context, animation_set)

def _optimize_for_all_frames(context: bpy.types.Context, camera: bpy.types.Camera, rotations_degrees: List[Optional[int]], animation_sets: List[AnimationSetPropertyGroup]):
    if camera.type != "ORTHO":
        raise RuntimeError("Camera.optimize_for_all_frames currently only works for orthographic cameras")

    props = context.scene.SpritesheetPropertyGroup
    cumulative_bounds = None

    if props.rotation_options.control_rotation:
        for angle in rotations_degrees:
            bounds = _optimize_for_rotation(context, camera, angle, animation_sets)

            if cumulative_bounds is None:
                cumulative_bounds = bounds
            else:
                cumulative_bounds.encapsulate(bounds)
    elif props.animation_options.control_animations:
        for animation_set in props.animation_options.get_animation_sets():
            bounds = _optimal_bounds_for_animation_set(context, animation_set)

            if cumulative_bounds is None:
                cumulative_bounds = bounds
            else:
                cumulative_bounds.encapsulate(bounds)
    else:
        cumulative_bounds = _find_camera_target_bounds(context, context.scene)

    return cumulative_bounds

def _optimize_for_rotation(context: bpy.types.Context, camera: bpy.types.Camera, rotation_degrees: List[Optional[int]], animation_sets: List[Optional[AnimationSetPropertyGroup]]):
    if camera.type != "ORTHO":
        raise RuntimeError("Camera.optimize_for_rotation currently only works for orthographic cameras")

    if rotation_degrees is not None:
        rotation_targets = list(map(lambda t: t.target, context.scene.SpritesheetPropertyGroup.rotation_options.targets))
        utils.rotate_objects(rotation_targets, z_rot_degrees = rotation_degrees)

    cumulative_bounds = None

    for animation_set in animation_sets:
        if animation_set is not None:
            current_bounds = _optimal_bounds_for_animation_set(context, animation_set)
        else:
            current_bounds = _find_camera_target_bounds(context, context.scene)

        if cumulative_bounds is not None:
            cumulative_bounds.encapsulate(current_bounds)
        else:
            cumulative_bounds = current_bounds

    return cumulative_bounds

def _find_bounding_box_for_animation_set(context: bpy.types.Context, animation_set: AnimationSetPropertyGroup):
    """Returns a Bounds object describing the minimal bounding box that can fit all frames of the animation set"""
    scene = context.scene
    frame_data = animation_set.get_frame_data()

    cumulative_bounds = None

    for index in range(frame_data.frame_min, frame_data.frame_max + 1):
        scene.frame_set(index)
        current_bounds = _find_camera_target_bounds(context, scene)

        if cumulative_bounds is not None:
            cumulative_bounds.encapsulate(current_bounds)
        else:
            cumulative_bounds = current_bounds

    return cumulative_bounds

def _find_camera_target_bounds(context: bpy.types.Context, scene: bpy.types.Scene) -> Bounds2D:
    props = scene.SpritesheetPropertyGroup

    cumulative_bounds = None

    targets = [t.target for t in props.camera_options.targets]
    meshes = []

    while len(targets) > 0:
        target = targets.pop()

        if target.type == 'MESH':
            meshes.append(target)

        targets.extend(target.children)

    if len(meshes) == 0:
        raise Exception("Found no meshes within the target set; cannot compute camera bounds")

    for m in meshes:
        bounds = _get_camera_space_bounding_box(context, props.camera_options.render_camera_obj, m)

        if cumulative_bounds is not None:
            cumulative_bounds.encapsulate(bounds = bounds)
        else:
            cumulative_bounds = bounds

    return cumulative_bounds

def _get_camera_space_bounding_box(context: bpy.types.Context, camera_obj: bpy.types.Object, target_obj: bpy.types.Object) -> Bounds2D:
    # TODO support more than just meshes (esp. metaballs)
    if target_obj.type != 'MESH':
        raise Exception(f"Target object {target_obj} is not a mesh")

    # Get latest version of target object with modifiers such as armature applied
    depsgraph = context.evaluated_depsgraph_get()
    target_obj = target_obj.evaluated_get(depsgraph)

    m_obj_to_world = target_obj.matrix_world
    m_world_to_cam = camera_obj.rotation_euler.to_matrix().inverted()

    obj_verts = target_obj.to_mesh().vertices
    cam_verts = [m_world_to_cam @ (m_obj_to_world @ v.co) for v in obj_verts]

    return Bounds2D.from_points(cam_verts)

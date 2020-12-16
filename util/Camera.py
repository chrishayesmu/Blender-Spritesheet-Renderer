import bpy
from mathutils import Vector
from typing import List, Optional

from property_groups import AnimationSetPropertyGroup
from util.Bounds import Bounds
import utils

####################################################################################
# Public methods: same as private but don't return the Bounds object
####################################################################################

def fit_camera_to_targets(context: bpy.types.Context):
    _select_only_camera_targets(context.scene)
    bpy.ops.view3d.camera_to_view_selected()

def optimize_for_animation_set(context: bpy.types.Context, animation_set: Optional[AnimationSetPropertyGroup]):
    props = context.scene.SpritesheetPropertyGroup

    _optimize_for_animation_set(context, props.camera_options.render_camera, props.camera_options.render_camera_obj, animation_set)

def optimize_for_all_frames(context: bpy.types.Context, rotations_degrees: List[Optional[int]], animation_sets: List[AnimationSetPropertyGroup]):
    props = context.scene.SpritesheetPropertyGroup

    _optimize_for_all_frames(context, props.camera_options.render_camera, props.camera_options.render_camera_obj, rotations_degrees, animation_sets)

def optimize_for_rotation(context: bpy.types.Context, rotation_degrees: List[Optional[int]], animation_sets: List[AnimationSetPropertyGroup]):
    props = context.scene.SpritesheetPropertyGroup

    _optimize_for_rotation(context, props.camera_options.render_camera, props.camera_options.render_camera_obj, rotation_degrees, animation_sets)

####################################################################################
# Internal methods: all return Bounds so they can call each other usefully
####################################################################################

def _optimize_for_animation_set(context: bpy.types.Context, camera: bpy.types.Camera, camera_obj: bpy.types.Object, animation_set: AnimationSetPropertyGroup):
    if camera.type != "ORTHO":
        raise RuntimeError("Camera.optimize_for_animation_set currently only works for orthographic cameras")

    max_bounds = _find_bounding_box_for_animation_set(context, camera, camera_obj, animation_set)

    camera_obj.location = max_bounds.center
    camera.ortho_scale = max(max_bounds.size)

    return max_bounds

def _optimize_for_all_frames(context: bpy.types.Context, camera: bpy.types.Camera, camera_obj: bpy.types.Object, rotations_degrees: List[Optional[int]], animation_sets: List[AnimationSetPropertyGroup]):
    if camera.type != "ORTHO":
        raise RuntimeError("Camera.optimize_for_all_frames currently only works for orthographic cameras")

    cumulative_bounds = None

    for angle in rotations_degrees:
        rotation_bounds = _optimize_for_rotation(context, camera, camera_obj, angle, animation_sets)

        if cumulative_bounds is None:
            cumulative_bounds = rotation_bounds
        else:
            cumulative_bounds.encapsulate(rotation_bounds)

    camera_obj.location = cumulative_bounds.center
    camera.ortho_scale = max(cumulative_bounds.size)

    return cumulative_bounds

def _optimize_for_rotation(context: bpy.types.Context, camera: bpy.types.Camera, camera_obj: bpy.types.Object, rotation_degrees: List[Optional[int]], animation_sets: List[Optional[AnimationSetPropertyGroup]]):
    if camera.type != "ORTHO":
        raise RuntimeError("Camera.optimize_for_rotation currently only works for orthographic cameras")

    _select_only_camera_targets(context.scene)

    if rotation_degrees is not None:
        rotation_targets = list(map(lambda t: t.target, context.scene.SpritesheetPropertyGroup.rotation_options.targets))
        utils.rotate_objects(rotation_targets, z_rot_degrees = rotation_degrees)

    cumulative_bounds = None

    for animation_set in animation_sets:
        if animation_set is not None:
            current_bounds = _optimize_for_animation_set(context, camera, camera_obj, animation_set)
        else:
            bpy.ops.view3d.camera_to_view_selected()
            current_bounds = _get_camera_image_plane(camera, camera_obj)

        if cumulative_bounds is not None:
            cumulative_bounds.encapsulate(current_bounds)
        else:
            cumulative_bounds = current_bounds

    camera_obj.location = cumulative_bounds.center
    camera.ortho_scale = max(cumulative_bounds.size)

    return cumulative_bounds

def _find_bounding_box_for_animation_set(context: bpy.types.Context, camera: bpy.types.Camera, camera_obj: bpy.types.Object, animation_set: AnimationSetPropertyGroup):
    """Returns a Bounds object describing the minimal bounding box that can fit all frames of the animation set"""
    scene = context.scene

    _select_only_camera_targets(context.scene)
    frame_data = animation_set.get_frame_data()

    cumulative_bounds = None

    for index in range(frame_data.frame_min, frame_data.frame_max + 1):
        scene.frame_set(index)
        bpy.ops.view3d.camera_to_view_selected()

        current_bounds = _get_camera_image_plane(camera, camera_obj)

        if cumulative_bounds is not None:
            cumulative_bounds.encapsulate(current_bounds)
        else:
            cumulative_bounds = current_bounds

    return cumulative_bounds

def _get_camera_image_plane(camera: bpy.types.Camera, camera_obj: bpy.types.Object):
    size = camera.ortho_scale

    # Take the dimensions for the default camera orientation (facing downwards) and rotate them
    # Default camera setup is with (0, 0, 0) at its center, and a rotation of (0, 0, 0) which points downward (which is (0, 0, -1))
    size_vec = Vector((size, size, 0))
    size_vec.rotate(camera_obj.rotation_quaternion)

    return Bounds.from_center_and_size(camera_obj.location, size_vec)

def _select_only_camera_targets(scene: bpy.types.Scene):
    props = scene.SpritesheetPropertyGroup

    for obj in scene.objects:
        is_target = any(target is obj for target in props.camera_options.targets)
        obj.select_set(is_target)
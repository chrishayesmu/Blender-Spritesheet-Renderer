import bpy
import math
from typing import List
from mathutils import Vector

from util.Bounds import Bounds
import utils

####################################################################################
# Public methods: same as private but don't return the Bounds object
####################################################################################

def fit_camera_to_target_object(context: bpy.types.Context):
    props = context.scene.SpritesheetPropertyGroup

    _select_only_object(context.scene, props.targetObject)
    bpy.ops.view3d.camera_to_view_selected()

def optimize_for_action(context: bpy.types.Context, action: bpy.types.Action):
    props = context.scene.SpritesheetPropertyGroup

    _optimize_for_action(context, props.renderCamera, props.targetObject, action)

def optimize_for_all_frames(context: bpy.types.Context, rotation_root: bpy.types.Object, rotations_degrees: List[int], actions: List[bpy.types.Action]):
    props = context.scene.SpritesheetPropertyGroup

    _optimize_for_all_frames(context, props.renderCamera, props.targetObject, rotation_root, rotations_degrees, actions)

def optimize_for_rotation(context: bpy.types.Context, rotation_root: bpy.types.Object, rotation_degrees: List[int], actions: List[bpy.types.Action]):
    props = context.scene.SpritesheetPropertyGroup

    _optimize_for_rotation(context, props.renderCamera, props.targetObject, rotation_root, rotation_degrees, actions)

####################################################################################
# Internal methods: all return Bounds so they can call each other usefully
####################################################################################

def _optimize_for_action(context: bpy.types.Context, camera: bpy.types.Camera, target_object, action):
    if camera.type != "ORTHO":
        raise RuntimeError("Camera.optimizeForAction currently only works for orthographic cameras")

    max_bounds = _find_bounding_box_for_action(context, camera, target_object, action)

    camera.location = max_bounds.center
    camera.data.ortho_scale = max(max_bounds.size)

    return max_bounds

def _optimize_for_all_frames(context: bpy.types.Context, camera: bpy.types.Camera, target_object, rotation_root, rotations_degrees, actions):
    if camera.data.type != "ORTHO":
        raise RuntimeError("Camera.optimizeForAllFrames currently only works for orthographic cameras")

    cumulative_bounds = None

    for angle in rotations_degrees:
        rotation_bounds = _optimize_for_rotation(context, camera, target_object, rotation_root, angle, actions)

        if cumulative_bounds is not None:
            cumulative_bounds.encapsulate(rotation_bounds)
        else:
            cumulative_bounds = rotation_bounds

    camera.location = cumulative_bounds.center
    camera.data.ortho_scale = max(cumulative_bounds.size)

    return cumulative_bounds

def _optimize_for_rotation(context: bpy.types.Context, camera: bpy.types.Camera, target_object, rotation_root, rotation_degrees, actions):
    if camera.type != "ORTHO":
        raise RuntimeError("Camera.optimizeForRotation currently only works for orthographic cameras")

    _select_only_object(context.scene, target_object)

    cumulative_bounds = None
    rotation_root.rotation_euler[2] = math.radians(rotation_degrees)

    for action in actions:
        if action is not None:
            current_bounds = _optimize_for_action(context, camera, target_object, action)
        else:
            bpy.ops.view3d.camera_to_view_selected()
            current_bounds = _get_camera_image_plane(camera)

        if cumulative_bounds is not None:
            cumulative_bounds.encapsulate(current_bounds)
        else:
            cumulative_bounds = current_bounds

    camera_obj = utils.find_object_data_for_camera(camera)
    camera_obj.location = cumulative_bounds.center
    camera.ortho_scale = max(cumulative_bounds.size)

    return cumulative_bounds

def _find_bounding_box_for_action(context: bpy.types.Context, camera: bpy.types.Camera, target_object, action):
    """Returns a Bounds object describing the minimal bounding box that can fit all frames of the action"""
    scene = context.scene
    frame_min = math.floor(action.frame_range[0])
    frame_max = math.ceil(action.frame_range[1])

    _select_only_object(context.scene, target_object)

    cumulative_bounds = None

    for index in range(frame_min, frame_max + 1):
        scene.frame_set(index)
        bpy.ops.view3d.camera_to_view_selected()

        current_bounds = _get_camera_image_plane(camera)

        if cumulative_bounds is not None:
            cumulative_bounds.encapsulate(current_bounds)
        else:
            cumulative_bounds = current_bounds

    return cumulative_bounds

def _get_camera_image_plane(camera: bpy.types.Camera):
    size = camera.ortho_scale
    camera_obj = utils.find_object_data_for_camera(camera)

    # Take the dimensions for the default camera orientation (facing downwards) and rotate them
    # Default camera setup is with (0, 0, 0) at its center, and a rotation of (0, 0, 0) which points downward (which is (0, 0, -1))
    size_vec = Vector((size, size, 0))
    size_vec.rotate(camera_obj.rotation_quaternion)

    return Bounds.from_center_and_size(camera_obj.location, size_vec)

def _select_only_object(scene: bpy.types.Scene, target_object):
    for obj in scene.objects:
        obj.select_set(False)

    target_object.select_set(True)

import bpy
import collections
import math
from mathutils import Vector

from util.Bounds import Bounds

####################################################################################
# Public methods: same as private but don't return the Bounds object
####################################################################################

def fitCameraToTargetObject(context):
    props = context.scene.SpritesheetPropertyGroup

    _selectOnlyObject(context.scene, props.targetObject)
    bpy.ops.view3d.camera_to_view_selected()

def optimizeForAction(context, action):
    props = context.scene.SpritesheetPropertyGroup

    _optimizeForAction(context, props.renderCamera, props.targetObject, action)

def optimizeForAllFrames(context, rotationRoot, rotationsDegrees, actions):
    props = context.scene.SpritesheetPropertyGroup

    _optimizeForAllFrames(context, props.renderCamera, props.targetObject, rotationRoot, rotationsDegrees, actions)

def optimizeForRotation(context, rotationRoot, rotationDegrees, actions):
    props = context.scene.SpritesheetPropertyGroup

    _optimizeForRotation(context, props.renderCamera, props.targetObject, rotationRoot, rotationDegrees, actions)

####################################################################################
# Internal methods: all return Bounds so they can call each other usefully
####################################################################################

def _optimizeForAction(context, camera, targetObject, action):
    if camera.data.type != "ORTHO":
        raise RuntimeError("Camera.optimizeForAction currently only works for orthographic cameras")

    maxBounds = _findBoundingBoxForAction(context, camera, targetObject, action)

    camera.location = maxBounds.center
    camera.data.ortho_scale = max(maxBounds.size)

    return maxBounds

def _optimizeForAllFrames(context, camera, targetObject, rotationRoot, rotationsDegrees, actions):
    if camera.data.type != "ORTHO":
        raise RuntimeError("Camera.optimizeForAllFrames currently only works for orthographic cameras")

    cumulativeBounds = None

    for angle in rotationsDegrees:
        rotationBounds = _optimizeForRotation(context, camera, targetObject, rotationRoot, angle, actions)

        if cumulativeBounds is not None:
            cumulativeBounds.encapsulate(rotationBounds)
        else:
            cumulativeBounds = rotationBounds

    camera.location = cumulativeBounds.center
    camera.data.ortho_scale = max(cumulativeBounds.size)

    return cumulativeBounds

def _optimizeForRotation(context, camera, targetObject, rotationRoot, rotationDegrees, actions):
    if camera.data.type != "ORTHO":
        raise RuntimeError("Camera.optimizeForRotation currently only works for orthographic cameras")

    _selectOnlyObject(context.scene, targetObject)

    cumulativeBounds = None
    rotationRoot.rotation_euler[2] = math.radians(rotationDegrees)

    for action in actions:
        if action is not None:
            currentBounds = _optimizeForAction(context, camera, targetObject, action)
        else:
            bpy.ops.view3d.camera_to_view_selected()
            currentBounds = _getCameraImagePlane(camera)

        if cumulativeBounds is not None:
            cumulativeBounds.encapsulate(currentBounds)
        else:
            cumulativeBounds = currentBounds

    camera.location = cumulativeBounds.center
    camera.data.ortho_scale = max(cumulativeBounds.size)

    return cumulativeBounds


def _findBoundingBoxForAction(context, camera, targetObject, action):
    """Returns a Bounds object describing the minimal bounding box that can fit all frames of the action"""
    scene = context.scene
    frameMin = math.floor(action.frame_range[0])
    frameMax = math.ceil(action.frame_range[1])

    _selectOnlyObject(context.scene, targetObject)
    
    cumulativeBounds = None

    for index in range(frameMin, frameMax + 1):
        scene.frame_set(index)
        bpy.ops.view3d.camera_to_view_selected()

        currentBounds = _getCameraImagePlane(camera)

        if cumulativeBounds is not None:
            cumulativeBounds.encapsulate(currentBounds)
        else:
            cumulativeBounds = currentBounds

    return cumulativeBounds

def _getCameraImagePlane(camera):
    size = camera.data.ortho_scale

    # Take the dimensions for the default camera orientation (facing downwards) and rotate them
    # Default camera setup is with (0, 0, 0) at its center, and a rotation of (0, 0, 0) which points downward (which is (0, 0, -1))
    sizeVec = Vector((size, size, 0))
    sizeVec.rotate(camera.rotation_quaternion)

    return Bounds.fromCenterAndSize(camera.location, sizeVec)

def _selectOnlyObject(scene, targetObject):
    for obj in scene.objects:
        obj.select_set(False)

    targetObject.select_set(True)
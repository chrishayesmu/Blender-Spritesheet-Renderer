import bpy

class SceneSnapshot:

    def __init__(self, context, terminalWriter):
        self._terminalWriter = terminalWriter

        scene = context.scene
        props = scene.SpritesheetPropertyGroup

        rotationRoot = props.rotationRoot if props.rotationRoot else props.targetObject

        self._action = props.targetObject.animation_data.action if props.targetObject.animation_data else None
        self._cameraLocation = props.renderCamera.location.copy()
        self._cameraOrthoScale = props.renderCamera.data.ortho_scale
        self._frame = scene.frame_current
        self._material = props.targetObject.data.materials[0] if len(props.targetObject.data.materials) > 0 else None
        self._rotation = rotationRoot.rotation_euler.copy()

    def restoreFromSnapshot(self, context):
        scene = context.scene
        props = scene.SpritesheetPropertyGroup

        rotationRoot = props.rotationRoot if props.rotationRoot else props.targetObject

        if props.targetObject.animation_data:
            props.targetObject.animation_data.action = self._action

        scene.frame_set(self._frame)

        if len(props.targetObject.data.materials) > 0:
            props.targetObject.data.materials[0] = self._material

        rotationRoot.rotation_euler = self._rotation

        #props.renderCamera.location = self._cameraLocation
        #props.renderCamera.data.ortho_scale = self._cameraOrthoScale
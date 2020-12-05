class SceneSnapshot:

    def __init__(self, context, terminalWriter):
        self._terminal_writer = terminalWriter

        scene = context.scene
        props = scene.SpritesheetPropertyGroup

        rotation_root = props.rotationRoot if props.rotationRoot else props.targetObject

        # TODO expand the amount we snapshot
        self._action = props.targetObject.animation_data.action if props.targetObject.animation_data else None
        self._camera_location = props.renderCamera.location.copy()
        self._camera_ortho_scale = props.renderCamera.data.ortho_scale
        self._frame = scene.frame_current
        self._material = props.targetObject.data.materials[0] if len(props.targetObject.data.materials) > 0 else None
        self._rotation = rotation_root.rotation_euler.copy()

    def restore_from_snapshot(self, context):
        scene = context.scene
        props = scene.SpritesheetPropertyGroup

        rotation_root = props.rotationRoot if props.rotationRoot else props.targetObject

        if props.targetObject.animation_data:
            props.targetObject.animation_data.action = self._action

        scene.frame_set(self._frame)

        if len(props.targetObject.data.materials) > 0:
            props.targetObject.data.materials[0] = self._material

        rotation_root.rotation_euler = self._rotation

        props.renderCamera.location = self._camera_location
        props.renderCamera.data.ortho_scale = self._camera_ortho_scale
import bpy
from mathutils import Vector
from typing import Dict, Set

class SceneSnapshot:

    def __init__(self, context: bpy.types.Context, snapshot_types: Set[str] = None):
        use_whitelist = snapshot_types is not None

        if use_whitelist:
            valid_opts = { 'ACTIONS', 'CAMERA', 'MATERIALS', 'ROTATIONS', 'SELECTIONS' }
            invalid_opts = snapshot_types.difference(valid_opts)

            if len(invalid_opts) > 0:
                raise ValueError(f"Unrecognized options {invalid_opts}")

        scene = context.scene
        props = scene.SpritesheetPropertyGroup

        # TODO expand the amount we snapshot

        # Check which things we're going to snapshot first
        self._should_snapshot_actions = props.animation_options.control_animations and (not use_whitelist or 'ACTIONS' in snapshot_types)
        self._should_snapshot_camera = props.camera_options.control_camera and (not use_whitelist or 'CAMERA' in snapshot_types)
        self._should_snapshot_materials = props.material_options.control_materials and (not use_whitelist or 'MATERIALS' in snapshot_types)
        self._should_snapshot_rotations = props.rotation_options.control_rotation and (not use_whitelist or 'ROTATIONS' in snapshot_types)
        self._should_snapshot_selections = (not use_whitelist or 'SELECTIONS' in snapshot_types)

        self._frame: int = scene.frame_current

        if self._should_snapshot_actions:
            self._snapshot_actions(context)

        if self._should_snapshot_camera:
            self._snapshot_camera(context)

        if self._should_snapshot_materials:
            self._snapshot_materials(context)

        if self._should_snapshot_rotations:
            self._snapshot_rotations(context)

        if self._should_snapshot_selections:
            self._snapshot_object_selections()

    def restore_from_snapshot(self, context):
        scene = context.scene

        scene.frame_set(self._frame)

        if self._should_snapshot_selections:
            self._restore_object_selections()

        if self._should_snapshot_camera:
            self._restore_camera(context)

        if self._should_snapshot_rotations:
            self._restore_rotations()

        if self._should_snapshot_actions:
            self._restore_actions()

        if self._should_snapshot_materials:
            self._restore_materials()

    def _restore_actions(self):
        for obj, action in self._actions.items():
            obj.animation_data.action = action

    def _restore_camera(self, context):
        props = context.scene.SpritesheetPropertyGroup

        props.camera_options.render_camera_obj.location = self._camera_location
        props.camera_options.render_camera.ortho_scale = self._camera_ortho_scale

    def _restore_materials(self):
        for obj, material in self._materials.items():
            obj.material_slots[0].material = material

    def _restore_object_selections(self):
        for obj, is_selected in self._object_selections.items():
            obj.select_set(is_selected)

    def _restore_rotations(self):
        for obj, rotation in self._rotations.items():
            obj.rotation_euler = rotation

    def _snapshot_actions(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        self._actions: Dict[bpy.types.Object, bpy.types.Action] = {}

        for animation_set in props.animation_options.animation_sets:
            objects = [a.target for a in animation_set.actions if a.target]

            for obj in objects:
                obj.animation_data_create()
                self._actions[obj] = obj.animation_data.action

    def _snapshot_camera(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        self._camera_location = Vector(props.camera_options.render_camera_obj.location)
        self._camera_ortho_scale = props.camera_options.render_camera.ortho_scale

    def _snapshot_materials(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        self._materials: Dict[bpy.types.Object, bpy.types.Material] = {}

        for material_set in props.material_options.material_sets:
            for prop in material_set.materials:
                self._materials[prop.target] = prop.target.material_slots[0].material if len(prop.target.material_slots) > 0 else None

    def _snapshot_object_selections(self):
        self._object_selections: Dict[bpy.types.Object, bool] = {}

        for obj in bpy.data.objects:
            self._object_selections[obj] = obj.select_get()

    def _snapshot_rotations(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        self._rotations: Dict[bpy.types.Object, Vector] = {}

        for target in props.rotation_options.targets:
            if target.target is not None:
                self._rotations[target.target] = Vector(target.target.rotation_euler)
import bpy
from mathutils import Vector
from typing import Dict

class SceneSnapshot:

    def __init__(self, context):
        scene = context.scene
        props = scene.SpritesheetPropertyGroup

        # TODO expand the amount we snapshot

        self._frame: int = scene.frame_current

        if props.camera_options.control_camera:
            self._snapshot_camera(context)

        if props.rotation_options.control_rotation:
            self._snapshot_rotations(context)

        if props.animation_options.control_animations:
            self._snapshot_actions(context)

        if props.material_options.control_materials:
            self._snapshot_materials(context)

    def restore_from_snapshot(self, context):
        scene = context.scene
        props = scene.SpritesheetPropertyGroup

        scene.frame_set(self._frame)

        if props.camera_options.control_camera:
            self._restore_camera(context)

        if props.rotation_options.control_rotation:
            self._restore_rotations()

        if props.animation_options.control_animations:
            self._restore_actions()

        if props.material_options.control_materials:
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

    def _restore_rotations(self):
        for obj, rotation in self._rotations.items():
            obj.rotation_euler = rotation

    def _snapshot_actions(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        self._actions: Dict[bpy.types.Object, bpy.types.Action] = {}

        for animation_set in props.animation_options.animation_sets:
            objects = [a.target for a in animation_set.actions]

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

    def _snapshot_rotations(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        self._rotations: Dict[bpy.types.Object, Vector] = {}

        for target in props.rotation_options.targets:
            self._rotations[target.target] = Vector(target.target.rotation_euler)
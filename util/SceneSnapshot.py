import bpy
from mathutils import Vector
from typing import Dict

class SceneSnapshot:

    def __init__(self, context):
        scene = context.scene
        props = scene.SpritesheetPropertyGroup

        # TODO expand the amount we snapshot

        self._frame = scene.frame_current

        if props.control_camera:
            self._snapshot_camera(context)

        if props.control_rotation:
            self._snapshot_rotations(context)

        if props.control_animations:
            self._snapshot_actions(context)

        if props.control_materials:
            self._snapshot_materials(context)

    def restore_from_snapshot(self, context):
        scene = context.scene
        props = scene.SpritesheetPropertyGroup

        scene.frame_set(self._frame)

        if props.control_camera:
            self._restore_camera(context)

        if props.control_rotation:
            self._restore_rotations()

        if props.control_animations:
            self._restore_actions()

        if props.control_materials:
            self._restore_materials()

    def _restore_actions(self):
        for obj, action in self._actions.items():
            obj.animation_data.action = action

    def _restore_camera(self, context):
        props = context.scene.SpritesheetPropertyGroup

        props.render_camera_obj.location = self._camera_location
        props.render_camera.ortho_scale = self._camera_ortho_scale

    def _restore_materials(self):
        for mesh, material in self._materials.items():
            mesh.materials[0] = material

    def _restore_rotations(self):
        for obj, rotation in self._rotations.items():
            obj.rotation_euler = rotation

    def _snapshot_actions(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        self._actions: Dict[bpy.types.Object, bpy.types.Action] = {}

        objects = [o.mesh_object for o in props.render_targets if o.mesh_object.animation_data is not None]

        for obj in objects:
            self._actions[obj] = obj.animation_data.action

    def _snapshot_camera(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        self._camera_location = Vector(props.render_camera_obj.location)
        self._camera_ortho_scale = props.render_camera.ortho_scale

    def _snapshot_materials(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        self._materials: Dict[bpy.types.Mesh, bpy.types.Material] = {}

        meshes_with_materials = [t.mesh for t in props.render_targets if len(t.mesh.materials) > 0]
        for mesh in meshes_with_materials:
            self._materials[mesh] = mesh.materials[0]

    def _snapshot_rotations(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        self._rotations: Dict[bpy.types.Object, Vector] = {}

        for target in props.render_targets:
            obj = target.rotation_root if target.rotation_root else target.mesh_object
            self._rotations[obj] = Vector(obj.rotation_euler)
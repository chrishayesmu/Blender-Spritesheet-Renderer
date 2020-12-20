import bpy

import preferences
import property_groups
import ui_panels
from util import Camera as CameraUtil, FileSystemUtil, ImageMagick, SceneSnapshot, UIUtil
import utils

class SPRITESHEET_OT_ConfigureRenderCameraOperator(bpy.types.Operator):
    bl_idname = "spritesheet.configure_render_camera"
    bl_label = "Configure Render Camera"
    bl_options = {'UNDO'}

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        if not props.camera_options.render_camera:
            return {"CANCELLED"}

        props.camera_options.render_camera.type = "ORTHO"
        return {'FINISHED'}

class SPRITESHEET_OT_LocateImageMagickOperator(bpy.types.Operator):
    bl_idname = "spritesheet.prefs_locate_imagemagick"
    bl_label = "Locate ImageMagick Installation"

    def execute(self, _):
        image_magick_path = ImageMagick.locate_image_magick_exe()

        if not image_magick_path:
            self.report({"ERROR"}, "Could not locate ImageMagick automatically. You will need to set the path in the add-on preferences manually.")
            return {"CANCELLED"}

        preferences.PrefsAccess.image_magick_path = image_magick_path
        self.report({"INFO"}, "Found ImageMagick installation at {}".format(image_magick_path))

        return {"FINISHED"}

class SPRITESHEET_OT_OpenDirectoryOperator(bpy.types.Operator):
    bl_idname = "spritesheet.open_directory"
    bl_label = "Open Directory"

    directory: bpy.props.StringProperty()

    def execute(self, _context):
        return {'FINISHED'} if FileSystemUtil.open_file_explorer(self.directory) else {'CANCELLED'}

class SPRITESHEET_OT_OptimizeCameraOperator(bpy.types.Operator):
    """Sets the Render Camera the same way it will be set while rendering the spritesheet, to help preview camera options.

This may have to iterate many frames of animation data, so this can take a long time if your scene is expensive to animate (e.g. modifiers such as subdivision surface)."""
    bl_idname = "spritesheet.optimize_camera"
    bl_label = "Optimize Camera for Spritesheet"
    bl_options = {'REGISTER', 'UNDO'}

    def get_animation_set_options(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        if not props.animation_options.control_animations:
            return [("0", "N/A", "")]

        options = []

        for index, animation_set in enumerate(props.animation_options.animation_sets):
            item = (str(index), f"Set {index} - {animation_set.name}", "")
            options.append(item)

        return options

    def get_rotation_angle_options(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        angles = props.rotation_options.get_rotations()
        options = []

        for angle in angles:
            item = (str(angle), f"{angle} degrees", "")
            options.append(item)

        return options

    animation_set: bpy.props.EnumProperty(
        name = "Animation Set",
        items = get_animation_set_options
    )

    control_mode: bpy.props.EnumProperty(
        name = "Control Style",
        items = property_groups.get_camera_control_mode_options
    )

    rotation_angle: bpy.props.EnumProperty(
        name = "Rotation Angle",
        items = get_rotation_angle_options
    )

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup

        is_valid, _ = props.camera_options.is_valid()

        return props.camera_options.control_camera and is_valid

    def invoke(self, context, _event):
        props = context.scene.SpritesheetPropertyGroup

        self.control_mode = props.camera_options.camera_control_mode

        return self.execute(context)

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        animation_sets = props.animation_options.get_animation_sets()
        rotations = props.rotation_options.get_rotations()

        # TODO: the shading mode of the viewport (e.g. wireframe, solid) actually makes a big difference in how long
        # it takes to iterate animation frames, but jsut setting it in this method doesn't help; it probably isn't
        # effective until end-of-frame. Rewriting this operator as modal and yielding after setting the shading
        # could cut the optimization time down a lot for complex scenes.

        snapshot = SceneSnapshot.SceneSnapshot(context, snapshot_types = {'ACTIONS', 'ROTATIONS', 'SELECTIONS'})

        if self.control_mode == "move_once":
            CameraUtil.optimize_for_all_frames(context, rotations, animation_sets)
        elif self.control_mode == "move_each_frame":
            CameraUtil.fit_camera_to_targets(context)
        elif self.control_mode == "move_each_animation":
            index = int(self.animation_set)
            animation_set = animation_sets[index]

            is_valid, _ = animation_set.is_valid()

            if not is_valid:
                # Don't report an error; it's visible in the operator's panel
                return {'CANCELLED'}

            CameraUtil.optimize_for_animation_set(context, animation_set)
        elif self.control_mode == "move_each_rotation":
            angle = int(self.rotation_angle)
            CameraUtil.optimize_for_rotation(context, angle, animation_sets)
        else:
            self.report({'ERROR'}, f"Unknown camera control mode {self.control_mode}")
            return {'CANCELLED'}

        snapshot.restore_from_snapshot(context)

        return {'FINISHED'}

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        animation_sets = props.animation_options.get_animation_sets()

        self.layout.use_property_decorate = False
        self.layout.use_property_split = True

        if self.control_mode == "move_each_animation":
            # Validate animation sets early so the error shows up on top
            index = int(self.animation_set)
            animation_set = animation_sets[index]
            is_valid, err = animation_set.is_valid()

            if not is_valid:
                UIUtil.message_box(context, self.layout, "Animation set is invalid: " + err, "ERROR")
                self.layout.separator()

        self.layout.prop(self, "control_mode")

        if self.control_mode == "move_each_animation":
            self.layout.prop(self, "animation_set")
        elif self.control_mode == "move_each_rotation":
            self.layout.prop(self, "rotation_angle")

########################################################
# Operators for previewing spritesheet props in scene
########################################################

class SPRITESHEET_OT_AssignMaterialSetOperator(bpy.types.Operator):
    """Assign all of the materials in this set to their respective targets, so they can be viewed together"""
    bl_idname = "spritesheet.assign_material_set"
    bl_label = "Assign Material Set in Scene"
    bl_options = {'UNDO'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return props.material_options.control_materials

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        assert 0 <= self.index < len(props.material_options.material_sets)

        material_set = props.material_options.material_sets[self.index]
        is_valid, err = material_set.is_valid()
        if not is_valid:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}

        material_set.assign_materials_to_targets()

        utils.tag_redraw_area(context, "VIEW_3D")

        return {'FINISHED'}

class SPRITESHEET_OT_PlayAnimationSetOperator(bpy.types.Operator):
    """Play this animation set in the viewport to preview how the animations look together"""
    bl_idname = "spritesheet.play_animation_set"
    bl_label = "Play Animation Set"

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return props.animation_options.control_animations

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        assert 0 <= self.index < len(props.animation_options.animation_sets)

        animation_set = props.animation_options.animation_sets[self.index]

        try:
            animation_set.assign_actions_to_targets()
        except Exception as e:
            message: str = utils.get_exception_message(e)

            self.report({'ERROR'}, message)
            print("Error in spritesheet.play_animation_set: " + message)
            return {'CANCELLED'}

        # Set frame data in the scene; it will loop automatically when started
        frame_data = animation_set.get_frame_data()
        context.scene.frame_start, context.scene.frame_end = frame_data.frame_min, frame_data.frame_max
        context.scene.frame_set(frame_data.frame_min)
        context.scene.render.fps = animation_set.output_frame_rate

        # For some reason animation_play will pause if something is playing, and that's not what we want for this operator
        if not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        # Update all other sets so their UI shows correctly
        for anim_set in props.animation_options.animation_sets:
            anim_set.is_previewing = False

        animation_set.is_previewing = True

        return {'FINISHED'}

########################################################
# Operators for modifying property groups
########################################################

#region Animation sets

class SPRITESHEET_OT_AddAnimationSetOperator(bpy.types.Operator):
    """Add a new animation set"""
    bl_idname = "spritesheet.add_animation_set"
    bl_label = "Add Animation Set"
    bl_options = {'UNDO'}

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        animation_set = props.animation_options.animation_sets.add()
        animation_set.actions.add()

        index = len(props.animation_options.animation_sets) - 1
        ui_panels.SPRITESHEET_PT_AnimationSetPanel.create_sub_panel(index)

        return {'FINISHED'}

class SPRITESHEET_OT_RemoveAnimationSetOperator(bpy.types.Operator):
    """Remove this animation set"""
    bl_idname = "spritesheet.remove_animation_set"
    bl_label = "Remove Animation Set"
    bl_options = {'UNDO'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return len(props.animation_options.animation_sets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        if self.index < 0 or self.index >= len(props.animation_options.animation_sets):
            return {'CANCELLED'}

        animation_set = props.animation_options.animation_sets[self.index]

        # Cancel animation if we're removing the active preview; not necessary but nice to have
        if animation_set.is_previewing and context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame = False)

        props.animation_options.animation_sets.remove(self.index)

        return {'FINISHED'}

class SPRITESHEET_OT_ModifyAnimationSetOperator(bpy.types.Operator):
    # TODO just replace this with add/remove/move operators like the other types
    bl_idname = "spritesheet.modify_animation_set"
    bl_label = "Modify Animation Set"
    bl_options = {'UNDO'}

    action_index: bpy.props.IntProperty(default = -1)

    animation_set_index: bpy.props.IntProperty(default = -1)

    operation: bpy.props.EnumProperty(
        items = [
            ("add_action", "", ""),
            ("move_action_up", "", ""),
            ("move_action_down", "", ""),
            ("remove_action", "", "")
        ]
    )

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        assert 0 <= self.animation_set_index < len(props.animation_options.animation_sets), f"animation_set_index {self.animation_set_index} out of range [0, {len(props.animation_options.animation_sets)}]"

        animation_set = props.animation_options.animation_sets[self.animation_set_index]

        if self.operation == "add_action":
            animation_set.actions.add()
            return {'FINISHED'}

        # All ops past this use action_index
        assert 0 <= self.action_index < len(animation_set.actions), f"action_index {self.action_index} out of range [0, {len(animation_set.actions)}]"

        if self.operation == "remove_action":
            if len(animation_set.actions) == 1:
                return {'CANCELLED'}

            if self.action_index == animation_set.selected_action_index:
                animation_set.selected_action_index = self.action_index - 1

            animation_set.actions.remove(self.action_index)
            return {'FINISHED'}

        if self.operation == "move_action_up":
            if self.action_index == 0:
                return {'CANCELLED'}

            animation_set.actions.move(self.action_index, self.action_index - 1)

            if self.action_index == animation_set.selected_action_index:
                animation_set.selected_action_index = self.action_index - 1

            return {'FINISHED'}

        if self.operation == "move_action_down":
            if self.action_index == len(animation_set.actions) - 1:
                return {'CANCELLED'}

            animation_set.actions.move(self.action_index, self.action_index + 1)

            if self.action_index == animation_set.selected_action_index:
                animation_set.selected_action_index = self.action_index + 1

            return {'FINISHED'}

        raise ValueError(f"Invalid operation: {self.operation}")

#endregion

#region Camera targets

class SPRITESHEET_OT_AddCameraTargetOperator(bpy.types.Operator):
    """Add a new camera target"""
    bl_idname = "spritesheet.add_camera_target"
    bl_label = "Add Camera Target"
    bl_options = {'UNDO'}

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        props.camera_options.targets.add()
        return {'FINISHED'}

class SPRITESHEET_OT_RemoveCameraTargetOperator(bpy.types.Operator):
    """Remove this camera target"""
    bl_idname = "spritesheet.remove_camera_target"
    bl_label = "Remove Camera Target"
    bl_options = {'UNDO'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return len(props.camera_options.targets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        if self.index < 0 or self.index >= len(props.camera_options.targets):
            return {'CANCELLED'}

        props.camera_options.targets.remove(self.index)

        if props.camera_options.selected_target_index == self.index:
            props.camera_options.selected_target_index = self.index - 1

        return {'FINISHED'}

class SPRITESHEET_OT_MoveCameraTargetUpOperator(bpy.types.Operator):
    """Moves the selected Camera Target up in the list (i.e. from index to index - 1)."""
    bl_idname = "spritesheet.move_camera_target_up"
    bl_label = "Move Camera Target Up"
    bl_options = {'UNDO_GROUPED'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return len(props.camera_options.targets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        if self.index <= 0 or self.index >= len(props.camera_options.targets):
            return {'CANCELLED'}

        new_index = self.index - 1

        props.camera_options.targets.move(self.index, new_index)

        if props.camera_options.selected_target_index == self.index:
            props.camera_options.selected_target_index = new_index

        return {'FINISHED'}

class SPRITESHEET_OT_MoveCameraTargetDownOperator(bpy.types.Operator):
    """Moves the selected Camera Target down in the list (i.e. from index to index + 1)."""
    bl_idname = "spritesheet.move_camera_target_down"
    bl_label = "Move Camera Target Down"
    bl_options = {'UNDO_GROUPED'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return len(props.camera_options.targets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        if self.index < 0 or self.index >= len(props.camera_options.targets) - 1:
            return {'CANCELLED'}

        new_index = self.index + 1

        props.camera_options.targets.move(self.index, new_index)

        if props.camera_options.selected_target_index == self.index:
            props.camera_options.selected_target_index = new_index

        return {'FINISHED'}

#endregion

#region Materials set

class SPRITESHEET_OT_AddMaterialSetOperator(bpy.types.Operator):
    """Add a new material set"""
    bl_idname = "spritesheet.add_material_set"
    bl_label = "Add Material Set"
    bl_options = {'UNDO'}

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        # Create new material set and give it a single entry to start
        material_set = props.material_options.material_sets.add()
        material_set.materials.add()

        # Register a new UI panel to display this material set
        index = len(props.material_options.material_sets) - 1
        ui_panels.SPRITESHEET_PT_MaterialSetPanel.create_sub_panel(index)

        return {'FINISHED'}

class SPRITESHEET_OT_RemoveMaterialSetOperator(bpy.types.Operator):
    """Remove this material set"""
    bl_idname = "spritesheet.remove_material_set"
    bl_label = "Remove Material Set"
    bl_options = {'UNDO'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        # Don't allow removing the last material set
        props = context.scene.SpritesheetPropertyGroup
        return len(props.material_options.material_sets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        if self.index < 0 or self.index >= len(props.material_options.material_sets):
            return {'CANCELLED'}

        props.material_options.material_sets.remove(self.index)

        return {'FINISHED'}

class SPRITESHEET_OT_ModifyMaterialSetOperator(bpy.types.Operator):
    # TODO just replace this with add/remove/move operators like the other types
    bl_idname = "spritesheet.modify_material_set"
    bl_label = "Modify Material Set"
    bl_options = {'UNDO'}

    material_set_index: bpy.props.IntProperty(default = -1)

    target_index: bpy.props.IntProperty(default = -1)

    operation: bpy.props.EnumProperty(
        items = [
            ("add_target", "", ""),
            ("move_target_up", "", ""),
            ("move_target_down", "", ""),
            ("remove_target", "", "")
        ]
    )

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        assert 0 <= self.material_set_index < len(props.material_options.material_sets), f"material_set_index {self.material_set_index} out of range [0, {len(props.material_options.material_sets)}]"

        material_set = props.material_options.material_sets[self.material_set_index]

        if self.operation == "add_target":
            material_set.materials.add()
            return {'FINISHED'}

        # All ops past this use target_index
        assert 0 <= self.target_index < len(material_set.materials), f"target_index {self.target_index} out of range [0, {len(material_set.materials)}]"

        if self.operation == "remove_target":
            if len(material_set.materials) == 1:
                return {'CANCELLED'}

            material_set.materials.remove(self.target_index)

            if self.target_index == material_set.selected_material_index:
                material_set.selected_material_index = self.target_index - 1

            return {'FINISHED'}

        if self.operation == "move_target_up":
            if self.target_index == 0:
                return {'CANCELLED'}

            material_set.materials.move(self.target_index, self.target_index - 1)

            if self.target_index == material_set.selected_material_index:
                material_set.selected_material_index = self.target_index - 1

            return {'FINISHED'}

        if self.operation == "move_target_down":
            if self.target_index == len(material_set.materials) - 1:
                return {'CANCELLED'}

            material_set.materials.move(self.target_index, self.target_index + 1)

            if self.target_index == material_set.selected_material_index:
                material_set.selected_material_index = self.target_index + 1

            return {'FINISHED'}

        raise ValueError(f"Invalid operation: {self.operation}")

#endregion

#region Rotation targets

class SPRITESHEET_OT_AddRotationTargetOperator(bpy.types.Operator):
    """Add a new rotation target"""
    bl_idname = "spritesheet.add_rotation_target"
    bl_label = "Add Rotation Target"
    bl_options = {'UNDO'}

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        props.rotation_options.targets.add()
        return {'FINISHED'}

class SPRITESHEET_OT_RemoveRotationTargetOperator(bpy.types.Operator):
    """Remove this rotation target"""
    bl_idname = "spritesheet.remove_rotation_target"
    bl_label = "Remove Rotation Target"
    bl_options = {'UNDO'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return len(props.rotation_options.targets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        if self.index < 0 or self.index >= len(props.rotation_options.targets):
            return {'CANCELLED'}

        props.rotation_options.targets.remove(self.index)

        if props.rotation_options.selected_target_index == self.index:
            props.rotation_options.selected_target_index = self.index - 1

        return {'FINISHED'}

class SPRITESHEET_OT_MoveRotationTargetUpOperator(bpy.types.Operator):
    """Moves the selected Rotation Target up in the list (i.e. from index to index - 1)."""
    bl_idname = "spritesheet.move_rotation_target_up"
    bl_label = "Move Rotation Target Up"
    bl_options = {'UNDO_GROUPED'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return len(props.rotation_options.targets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        if self.index <= 0 or self.index >= len(props.rotation_options.targets):
            return {'CANCELLED'}

        new_index = self.index - 1

        props.rotation_options.targets.move(self.index, new_index)

        if props.rotation_options.selected_target_index == self.index:
            props.rotation_options.selected_target_index = new_index

        return {'FINISHED'}

class SPRITESHEET_OT_MoveRotationTargetDownOperator(bpy.types.Operator):
    """Moves the selected Rotation Target down in the list (i.e. from index to index + 1)."""
    bl_idname = "spritesheet.move_rotation_target_down"
    bl_label = "Move Rotation Target Down"
    bl_options = {'UNDO_GROUPED'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return len(props.rotation_options.targets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        if self.index < 0 or self.index >= len(props.rotation_options.targets) - 1:
            return {'CANCELLED'}

        new_index = self.index + 1

        props.rotation_options.targets.move(self.index, new_index)

        if props.rotation_options.selected_target_index == self.index:
            props.rotation_options.selected_target_index = new_index

        return {'FINISHED'}

#endregion
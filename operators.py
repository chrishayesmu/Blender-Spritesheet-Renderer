import bpy

import preferences
import ui_panels
from util import FileSystemUtil
from util import ImageMagick

class SPRITESHEET_OT_ConfigureRenderCameraOperator(bpy.types.Operator):
    bl_idname = "spritesheet.configure_render_camera"
    bl_label = "Configure Render Camera"
    bl_options = {'UNDO'}

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        if not props.render_camera:
            return {"CANCELLED"}

        props.render_camera.type = "ORTHO"
        return {"FINISHED"}

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
        return {"FINISHED"} if FileSystemUtil.open_file_explorer(self.directory) else {"CANCELLED"}

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
        return props.control_materials

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        assert 0 <= self.index < len(props.material_sets)

        material_set = props.material_sets[self.index]
        if not material_set.is_valid():
            self.report({'ERROR'}, "All materials in this set need to be assigned first.")
            return {'CANCELLED'}

        material_set.assign_materials_to_targets(context)

        for area in context.window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

        return {'FINISHED'}

class SPRITESHEET_OT_PlayAnimationSetOperator(bpy.types.Operator):
    """Play this animation set in the viewport to preview how the animations look together."""
    bl_idname = "spritesheet.play_animation_set"
    bl_label = "Play Animation Set"

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return props.control_animations

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        assert 0 <= self.index < len(props.animation_sets)

        animation_set = props.animation_sets[self.index]

        try:
            animation_set.assign_actions_to_targets(context)
        except Exception as e:
            message: str = e.message if hasattr(e, "message") else str(e.args[0]) if len(e.args) > 0 else "An unknown error occurred."

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
        for anim_set in props.animation_sets:
            anim_set.is_previewing = False

        animation_set.is_previewing = True

        return {'FINISHED'}

########################################################
# Operators for modifying property groups
########################################################

class SPRITESHEET_OT_AddAnimationSetOperator(bpy.types.Operator):
    """Add a new animation set"""
    bl_idname = "spritesheet.add_animation_set"
    bl_label = "Add Animation Set"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return props.control_animations

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        animation_set = props.animation_sets.add()

        for _ in range(0, len(props.render_targets)):
            animation_set.actions.add()

        index = len(props.animation_sets) - 1
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
        return props.control_animations and len(props.animation_sets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        if self.index < 0 or self.index >= len(props.animation_sets):
            return {'CANCELLED'}

        animation_set = props.animation_sets[self.index]

        # Cancel animation if we're removing the active preview; not necessary but nice to have
        if animation_set.is_previewing and context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame = False)

        props.animation_sets.remove(self.index)

        return {'FINISHED'}

class SPRITESHEET_OT_AddMaterialSetOperator(bpy.types.Operator):
    """Add a new material set"""
    bl_idname = "spritesheet.add_material_set"
    bl_label = "Add Material Set"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return props.control_materials

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        material_set = props.material_sets.add()

        # Each material set should have a number of items equal to the number of render targets
        for _ in range (0, len(props.render_targets)):
            material_set.materials.add()

        # Register a new UI panel to display this material set
        index = len(props.material_sets) - 1
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
        return props.control_materials and len(props.material_sets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        if self.index < 0 or self.index >= len(props.material_sets):
            return {'CANCELLED'}

        props.material_sets.remove(self.index)

        return {'FINISHED'}

class SPRITESHEET_OT_MoveRenderTargetUpOperator(bpy.types.Operator):
    """Moves the selected Render Target up in the list (i.e. from index to index - 1)."""
    bl_idname = "spritesheet.move_render_target_up"
    bl_label = "Move Render Target Up"
    bl_options = {'UNDO_GROUPED'}

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return props.selected_render_target_index in range(1, len(props.render_targets))

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        index = props.selected_render_target_index
        new_index = index - 1

        props.render_targets.move(index, new_index)
        props.selected_render_target_index = new_index

        # Repeat this swap for material sets to stay in sync
        for material_set in props.material_sets:
            material_set.materials.move(index, new_index)

        return {'FINISHED'}

class SPRITESHEET_OT_MoveRenderTargetDownOperator(bpy.types.Operator):
    """Moves the selected Render Target down in the list (i.e. from index to index + 1)."""
    bl_idname = "spritesheet.move_render_target_down"
    bl_label = "Move Render Target Down"
    bl_options = {'UNDO_GROUPED'}

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return props.selected_render_target_index in range(0, len(props.render_targets) - 1)

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        index = props.selected_render_target_index
        new_index = index + 1

        props.render_targets.move(index, new_index)
        props.selected_render_target_index = new_index

        # Repeat this swap for material sets to stay in sync
        for material_set in props.material_sets:
            material_set.materials.move(index, new_index)

        return {'FINISHED'}

class SPRITESHEET_OT_AddRenderTargetOperator(bpy.types.Operator):
    """Adds a new, empty Render Target slot to the spritesheet render targets."""
    bl_idname = "spritesheet.add_render_target"
    bl_label = "Add Target Object"
    bl_options = {'UNDO'}

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        props.render_targets.add()

        # Iterate animation/material sets and add items to keep them in sync
        for animation_set in props.animation_sets:
            animation_set.actions.add()

        for material_set in props.material_sets:
            material_set.materials.add()

        return {'FINISHED'}

class SPRITESHEET_OT_RemoveRenderTargetOperator(bpy.types.Operator):
    """Removes the selected Render Target from the spritesheet render targets."""
    bl_idname = "spritesheet.remove_render_target"
    bl_label = "Remove Render Target"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        # Don't allow removing the last target
        props = context.scene.SpritesheetPropertyGroup
        return len(props.render_targets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        if props.selected_render_target_index < 0 or props.selected_render_target_index >= len(props.render_targets):
            return {'CANCELLED'}

        props.render_targets.remove(props.selected_render_target_index)

        for animation_set in props.animation_sets:
            animation_set.actions.remove(props.selected_render_target_index)

        for material_set in props.material_sets:
            material_set.materials.remove(props.selected_render_target_index)

        return {'FINISHED'}
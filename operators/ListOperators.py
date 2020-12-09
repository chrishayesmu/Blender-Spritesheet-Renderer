import bpy

import ui_panels

class SPRITESHEET_OT_AddMaterialSetOperator(bpy.types.Operator):
    bl_idname = "spritesheet.add_material_set"
    bl_label = "Add Material Set"

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return props.useMaterials

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        material_set = props.materialSets.add()

        # Each material set should have a number of items equal to the number of render targets
        for _ in range (0, len(props.render_targets)):
            material_set.objectMaterialPairs.add()

        # Register a new UI panel to display this material set
        index = len(props.materialSets) - 1
        ui_panels.SPRITESHEET_PT_MaterialSetPanel.create_sub_panel(index)

        return {'FINISHED'}

class SPRITESHEET_OT_RemoveMaterialSetOperator(bpy.types.Operator):
    bl_idname = "spritesheet.remove_material_set"
    bl_label = "Remove Material Set"

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        # Don't allow removing the last material set
        props = context.scene.SpritesheetPropertyGroup
        return props.useMaterials and len(props.materialSets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        if self.index < 0 or self.index >= len(props.materialSets):
            return {'CANCELLED'}

        props.materialSets.remove(self.index)

        return {'FINISHED'}

class SPRITESHEET_OT_MoveRenderTargetUpOperator(bpy.types.Operator):
    """Moves the selected Render Target up in the list (i.e. from index to index - 1)."""
    bl_idname = "spritesheet.move_render_target_up"
    bl_label = "Move Render Target Up"

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
        for material_set in props.materialSets:
            material_set.objectMaterialPairs.move(index, new_index)

        return {'FINISHED'}

class SPRITESHEET_OT_MoveRenderTargetDownOperator(bpy.types.Operator):
    """Moves the selected Render Target down in the list (i.e. from index to index + 1)."""
    bl_idname = "spritesheet.move_render_target_down"
    bl_label = "Move Render Target Down"

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
        for material_set in props.materialSets:
            material_set.objectMaterialPairs.move(index, new_index)

        return {'FINISHED'}

class SPRITESHEET_OT_AddRenderTargetOperator(bpy.types.Operator):
    """Adds a new, empty Render Target slot to the spritesheet render targets."""
    bl_idname = "spritesheet.add_render_target"
    bl_label = "Add Target Object"

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        props.render_targets.add()

        # Iterate material sets and add items to keep them in sync
        for material_set in props.materialSets:
            material_set.objectMaterialPairs.add()

        return {'FINISHED'}

class SPRITESHEET_OT_RemoveRenderTargetOperator(bpy.types.Operator):
    """Removes the selected Render Target from the spritesheet render targets."""
    bl_idname = "spritesheet.remove_render_target"
    bl_label = "Remove Render Target"

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

        for material_set in props.materialSets:
            material_set.objectMaterialPairs.remove(props.selected_render_target_index)

        return {'FINISHED'}
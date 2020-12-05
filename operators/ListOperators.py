import bpy

from ui.MaterialSetPanel import SPRITESHEET_PT_MaterialSetPanel as MaterialSetPanel
from util import UIUtil

class SPRITESHEET_OT_AddMaterialSetOperator(bpy.types.Operator):
    bl_idname = "spritesheet.add_material_set"
    bl_label = "Add Material Set"

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup
        return props.useMaterials

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        materialSet = props.materialSets.add()

        # Each material set should have a number of items equal to the number of render targets
        for i in range (0, len(props.targetObjects)):
            materialSet.objectMaterialPairs.add()

        # Register a new UI panel to display this material set
        index = len(props.materialSets) - 1
        MaterialSetPanel.createSubPanel(index)

        return {"FINISHED"}

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
            return {"CANCELLED"}

        props.materialSets.remove(self.index)

        return {"FINISHED"}

class SPRITESHEET_OT_AddRenderTargetOperator(bpy.types.Operator):
    """Adds a new, empty Target Object slot to the spritesheet render targets."""
    bl_idname = "spritesheet.add_render_target"
    bl_label = "Add Target Object"

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        props.targetObjects.add()

        # Iterate material sets and add items to keep them in sync
        for materialSet in props.materialSets:
            materialSet.objectMaterialPairs.add()

        return {"FINISHED"}

class SPRITESHEET_OT_RemoveRenderTargetOperator(bpy.types.Operator):
    """Removes the selected Target Object from the spritesheet render targets."""
    bl_idname = "spritesheet.remove_render_target"
    bl_label = "Remove Target Object"

    @classmethod
    def poll(cls, context):
        # Don't allow removing the last target object
        props = context.scene.SpritesheetPropertyGroup
        return len(props.targetObjects) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        if props.selectedTargetObjectIndex < 0 or props.selectedTargetObjectIndex >= len(props.targetObjects):
            return {"CANCELLED"}

        props.targetObjects.remove(props.selectedTargetObjectIndex)

        for materialSet in props.materialSets:
            materialSet.objectMaterialPairs.remove(props.selectedTargetObjectIndex)

        return {"FINISHED"}
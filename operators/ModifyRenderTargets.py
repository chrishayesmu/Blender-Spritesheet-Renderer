import bpy

from ui.MaterialSetPanel import MaterialSetPanel
from util import UIUtil

class AddMaterialSetOperator(bpy.types.Operator):
    bl_idname = "spritesheet.add_material_set"
    bl_label = "Add Material Set"

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

class RemoveMaterialSetOperator(bpy.types.Operator):
    bl_idname = "spritesheet.remove_material_set"
    bl_label = "Remove Material Set"

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        # Don't allow removing the last material set; we always need at least one
        props = context.scene.SpritesheetPropertyGroup
        return len(props.materialSets) > 1

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        if self.index < 0 or self.index >= len(props.materialSets):
            return {"CANCELLED"}

        props.materialSets.remove(self.index)

        return {"FINISHED"}

class AddRenderTargetOperator(bpy.types.Operator):
    bl_idname = "spritesheet.add_render_target"
    bl_label = "Add Target Object"

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        props.targetObjects.add()

        # Iterate material sets and add items to keep them in sync
        for materialSet in props.materialSets:
            materialSet.objectMaterialPairs.add()

        return {"FINISHED"}

class RemoveRenderTargetOperator(bpy.types.Operator):
    bl_idname = "spritesheet.remove_render_target"
    bl_label = "Remove Target Object"

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup
        if props.selectedTargetObjectIndex < 0 or props.selectedTargetObjectIndex >= len(props.targetObjects):
            return {"CANCELLED"}

        props.targetObjects.remove(props.selectedTargetObjectIndex)

        # TODO iterate material sets and remove matching item
        for materialSet in props.materialSets:
            materialSet.objectMaterialPairs.remove(props.selectedTargetObjectIndex)

        return {"FINISHED"}
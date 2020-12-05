import bpy

from ui.BaseAddonPanel import BaseAddonPanel
from util import UIUtil

class SPRITESHEET_PT_MaterialSetPanel():
    """UI Panel for material sets.

    Since this panel is shown multiple times, it is instantiated as multiple sub-types, and this specific class
    is never actually instantiated. Hence, it does not need to extend any classes like the other panels do, since
    those will be mixed in at runtime."""

    bl_label = "" # hidden; see draw_header
    bl_parent_id = "SPRITESHEET_PT_materials"

    index = 0

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup

        return cls.index < len(props.materialSets)

    @classmethod
    def createSubPanel(cls, index):
        UIUtil.createPanelType(cls, index)

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        materialSet = props.materialSets[self.index]

        self.layout.active = props.useMaterials

        row = self.layout.row()
        row.operator("spritesheet.remove_material_set", text = "Remove Set", icon = "REMOVE").index = self.index

        row = self.layout.row()
        row.prop(materialSet, "name")

        row = self.layout.row()
        row.prop(materialSet, "role")

        row = self.layout.row()
        self.template_list(row,
                           "SPRITESHEET_UL_ObjectMaterialPairPropertyList", # Class name
                           "", # List ID (blank to generate)
                           materialSet, # List items property source
                           "objectMaterialPairs", # List items property name
                           materialSet, # List index property source
                           "selectedObjectMaterialPair", # List index property name
        )

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup
        materialSet = props.materialSets[self.index]

        setLabel = f"Material Set {self.index + 1}"

        if materialSet.name:
            setLabel = setLabel + " - " + materialSet.name

        self.layout.label(text = setLabel)
import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class MaterialsPanel(BaseAddonPanel, bpy.types.Panel):
    """UI Panel for materials"""
    bl_idname = "SPRITESHEET_PT_materials"
    bl_label = "Control Materials"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "useMaterials", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.useMaterials

        row = self.layout.row(align = True)
        row.operator("spritesheet.add_material_set", text = "Add Material Set", icon = "ADD")


#        row = self.layout.row()
#        row.template_list("UI_UL_MaterialSelectionPropertyList", # Class name
#                        "", # List ID (blank to generate)
#                        props, # List items property source
#                        "materialSelections", # List items property name
#                        props, # List index property source
#                        "activeMaterialSelectionIndex", # List index property name
#                        rows = min(5, max(1, len(props.materialSelections))),
#                        maxrows = 5
#        )

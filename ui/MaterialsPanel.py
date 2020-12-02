import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class MaterialsPanel(BaseAddonPanel, bpy.types.Panel):
    """UI Panel for materials"""
    bl_idname = "SPRITESHEET_PT_materials"
    bl_label = "Material Data"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        row = self.layout.row()
        row.prop(props, "useMaterials")

        if props.useMaterials:
            if len(props.materialSelections) > 0:
                self.layout.separator()

                row = self.layout.row()
                split = row.split(factor = 0.075)
                split.scale_y = 0.4
                col1, col2 = (split.column(), split.column())
                
                split = col2.split(factor = 0.6)
                col2, col3 = (split.column(), split.column())

                col1.label(text = "Use")
                col2.label(text = "Material")
                col3.label(text = "Purpose")

                row = self.layout.row()
                row.template_list("UI_UL_MaterialSelectionPropertyList", # Class name
                                "", # List ID (blank to generate)
                                props, # List items property source
                                "materialSelections", # List items property name
                                props, # List index property source
                                "activeMaterialSelectionIndex", # List index property name
                                rows = min(5, len(props.materialSelections)),
                                maxrows = 5
                )
            else:
                row = self.layout.row()
                box = row.box()
                box.label(text = "No materials are in this scene.", icon = "ERROR")

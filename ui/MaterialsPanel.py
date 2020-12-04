import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class SPRITESHEET_PT_MaterialsPanel(BaseAddonPanel, bpy.types.Panel):
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
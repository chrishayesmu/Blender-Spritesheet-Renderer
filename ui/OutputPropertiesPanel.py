import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class SPRITESHEET_PT_OutputPropertiesPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_outputproperties"
    bl_label = "Output Properties"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False
        self.layout.alignment = "LEFT"

        #row = self.layout.row()
        self.layout.prop(props, "spriteSize")

        row = self.layout.row(heading = "Output Size")
        row.prop(props, "padToPowerOfTwo")

        self.layout.separator()

       #row = self.layout.row()

        col = self.layout.column(heading = "Separate Files by", align = True)
        col.prop(props, "separateFilesPerAnimation", text = "Animation")
        col.prop(props, "separateFilesPerRotation", text = "Rotation")

        subcol = col.column()
        subcol.enabled = False
        subcol.prop(props, "separateFilesPerMaterial", text = "Material Set")
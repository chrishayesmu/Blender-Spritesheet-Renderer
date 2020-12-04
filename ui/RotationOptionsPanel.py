import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class SPRITESHEET_PT_RotationOptionsPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_rotationoptions"
    bl_label = "Control Rotation"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "rotateObject", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.rotateObject

        row = self.layout.row()
        row.prop(props, "rotationNumber")

        row = self.layout.row()
        self.template_list(row,
                    "SPRITESHEET_UL_RotationRootPropertyList", # Class name
                    "spritesheet_RotationOptionsPanel_rotation_root_list", # List ID (blank to generate)
                    props, # List items property source
                    "targetObjects", # List items property name
                    props, # List index property source
                    "selectedRotationRootIndex", # List index property name
        )
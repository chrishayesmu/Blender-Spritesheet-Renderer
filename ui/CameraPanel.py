import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class SPRITESHEET_PT_CameraPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_camera"
    bl_label = "Control Camera"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "controlCamera", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.controlCamera

        row = self.layout.row()
        row.prop_search(props, "renderCamera", bpy.data, "objects")

        row = self.layout.row()
        row.prop(props, "cameraControlMode")
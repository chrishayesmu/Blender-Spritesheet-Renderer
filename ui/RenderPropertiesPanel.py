import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class RenderPropertiesPanel(BaseAddonPanel, bpy.types.Panel):
    """UI Panel for render properties"""
    bl_idname = "SPRITESHEET_PT_renderproperties"
    bl_label = "Render Properties"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        
        # TODO move to file output panel
        row = self.layout.row()
        row.prop(props, "spriteSize")

        row = self.layout.row()
        row.prop(props, "padToPowerOfTwo")

        # TODO rename this for its own camera-specific panel
        row = self.layout.row()
        row.prop(props, "controlCamera")

        if props.controlCamera:
            row.prop(props, "cameraControlMode")
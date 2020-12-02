import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class RenderPropertiesPanel(BaseAddonPanel, bpy.types.Panel):
    """UI Panel for render properties"""
    bl_idname = "SPRITESHEET_PT_renderproperties"
    bl_label = "Render Properties"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        
        row = self.layout.row()
        row.prop(props, "spriteSize")

        row = self.layout.row()
        row.prop(props, "padToPowerOfTwo")

        row = self.layout.row()
        row.prop(props, "controlCamera")

        if props.controlCamera:
            row.prop(props, "cameraControlMode")

        row = self.layout.row()
        split = row.split(factor = 0.3)
        col1, col2 = (split.column(), split.column())
        col1.prop(props, "rotateObject")
        
        if props.rotateObject:
            col2.prop(props, "rotationNumber")

            split = col2.split(factor = 0.3)
            split.label(text = "Rotation Root")
            split.prop_search(props, "rotationRoot", bpy.data, "objects")
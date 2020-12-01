import bpy
import textwrap

from custom_operators import spritesheetRenderModal as Render
from util import UIUtil


class ScenePropertiesPanel(bpy.types.Panel):
    """UI Panel for 2D Spritesheet Renderer"""
    bl_idname = "SPRITESHEET_PT_sceneproperties"
    bl_label = "Scene Properties"
    bl_category = "Spritesheet"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        
        row = self.layout.row()
        row.prop_search(props, "targetObject", bpy.data, "objects")

        row = self.layout.row()
        row.prop_search(props, "renderCamera", bpy.data, "objects")

        row = self.layout.row()
        row.operator("spritesheet.render", text = "Start Render")

        if Render.SpritesheetRenderModalOperator.renderDisabledReason:
            row = self.layout.row()
            box = row.box()

            # First column just has an error icon
            row = box.row()
            row.scale_y = 0.7 # shrink so lines of text appear closer together

            col = row.column()
            col.label(icon = "ERROR")
            col.scale_x = .75 # adjust spacing from icon to text

            col = row.column() # text column

            wrappedMessageLines = UIUtil.wrapTextInRegion(context, Render.SpritesheetRenderModalOperator.renderDisabledReason)
            for line in wrappedMessageLines:
                row = col.row()
                row.label(text = line)

            # Hacky: check for keywords in the error string to expose some functionality
            reasonLower = Render.SpritesheetRenderModalOperator.renderDisabledReason.lower()
            if "addon preferences" in reasonLower:
                row = box.row()
                row.operator("spritesheet.showprefs", text = "Show Addon Preferences")

                # Right now the only addon preference is ImageMagick location, but let's future proof a little
                if "imagemagick" in reasonLower:
                    row = box.row()
                    row.operator("spritesheet._misc", text = "Locate Automatically").action = "locateImageMagick"
            elif "orthographic" in reasonLower:
                row = box.row()
                row.operator("spritesheet._misc", text = "Make Camera Ortho").action = "makeRenderCameraOrtho"
import bpy
import textwrap

from operators.RenderSpritesheet import RenderSpritesheetOperator
from ui.BaseAddonPanel import BaseAddonPanel
from util import UIUtil

class ScenePropertiesPanel(BaseAddonPanel, bpy.types.Panel):
    """UI Panel for 2D Spritesheet Renderer"""
    bl_idname = "SPRITESHEET_PT_sceneproperties"
    bl_label = "Scene Properties"
    bl_options = set() # override parent's DEFAULT_CLOSED

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        row = self.layout.row()
        row.label(text = "Objects to Render")
        #row.prop_search(props, "targetObject", bpy.data, "objects")

        row = self.layout.row()
        self.template_list(row,
                          "SPRITESHEET_UL_RenderTargetPropertyList", # Class name
                          "spritesheet_ScenePropertiesPanel_target_objects_list", # List ID (blank to generate)
                          props, # List items property source
                          "targetObjects", # List items property name
                          props, # List index property source
                          "selectedTargetObjectIndex", # List index property name,
                          add_op = "spritesheet.add_render_target",
                          remove_op = "spritesheet.remove_render_target"
        )

        row = self.layout.row()
        row.prop_search(props, "renderCamera", bpy.data, "objects")

        row = self.layout.row()
        row.operator("spritesheet.render", text = "Start Render")

        if RenderSpritesheetOperator.renderDisabledReason:
            row = self.layout.row()
            box = row.box()

            # First column just has an error icon
            row = box.row()
            row.scale_y = 0.7 # shrink so lines of text appear closer together

            col = row.column()
            col.label(icon = "ERROR")
            col.scale_x = .75 # adjust spacing from icon to text

            col = row.column() # text column

            wrappedMessageLines = UIUtil.wrapTextInRegion(context, RenderSpritesheetOperator.renderDisabledReason)
            for line in wrappedMessageLines:
                row = col.row()
                row.label(text = line)

            # Hacky: check for keywords in the error string to expose some functionality
            reasonLower = RenderSpritesheetOperator.renderDisabledReason.lower()
            if "addon preferences" in reasonLower:
                row = box.row()
                row.operator("spritesheet.showprefs", text = "Show Addon Preferences")

                if "imagemagick" in reasonLower:
                    row = box.row()
                    row.operator("spritesheet.prefs_locate_imagemagick", text = "Locate Automatically")
            elif "orthographic" in reasonLower:
                row = box.row()
                row.operator("spritesheet.configure_render_camera", text = "Make Camera Ortho")
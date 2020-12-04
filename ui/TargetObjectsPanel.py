import bpy

from ui.BaseAddonPanel import BaseAddonPanel
from util import UIUtil

class SPRITESHEET_PT_TargetObjectsPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_targetobjects"
    bl_label = "Target Objects"
    bl_options = set() # override parent's DEFAULT_CLOSED

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        row = self.layout.row()
        self.template_list(row,
                          "SPRITESHEET_UL_RenderTargetPropertyList", # Class name
                          "spritesheet_TargetObjectsPanel_target_objects_list", # List ID (blank to generate)
                          props, # List items property source
                          "targetObjects", # List items property name
                          props, # List index property source
                          "selectedTargetObjectIndex", # List index property name,
                          add_op = "spritesheet.add_render_target",
                          remove_op = "spritesheet.remove_render_target"
        )
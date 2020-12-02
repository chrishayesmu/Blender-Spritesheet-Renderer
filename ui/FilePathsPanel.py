import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class FilePathsPanel(BaseAddonPanel, bpy.types.Panel):
    """UI Panel for file paths"""
    bl_idname = "SPRITESHEET_PT_filepaths"
    bl_label = "File Paths"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        row = self.layout.row()
        row.prop(props, "separateFilesPerAnimation")

        row = self.layout.row()
        row.prop(props, "separateFilesPerRotation")

        row = self.layout.row()
        row.enabled = False
        row.prop(props, "separateFilesPerMaterial")
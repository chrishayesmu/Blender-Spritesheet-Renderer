import bpy

class FilePathsPanel(bpy.types.Panel):
    """UI Panel for file paths"""
    bl_idname = "SPRITESHEET_PT_filepaths"
    bl_label = "File Paths"
    bl_category = "Spritesheet"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        row = self.layout.row()
        row.prop(props, "separateFilesPerAnimation")

        row = self.layout.row()
        row.prop(props, "separateFilesPerRotation")

        row = self.layout.row()
        row.enabled = False
        row.prop(props, "separateFilesPerMaterial")
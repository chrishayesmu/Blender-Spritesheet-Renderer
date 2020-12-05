import bpy

from util import FileSystemUtil

class SPRITESHEET_OT_OpenDirectoryOperator(bpy.types.Operator):
    bl_idname = "spritesheet.open_directory"
    bl_label = "Open Directory"

    directory: bpy.props.StringProperty()

    def execute(self, _context):
        return {"FINISHED"} if FileSystemUtil.open_file_explorer(self.directory) else {"CANCELLED"}

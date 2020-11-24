import bpy
import subprocess
from shutil import which

def CheckFileExplorerType():
    """Attempts to determine what type of system we're on and what file explorer is available"""

    if which("explorer") is not None:
        return "windows"

    return "none"

class OpenDirectoryOperator(bpy.types.Operator):
    """Operator for opening a directory in the file explorer"""
    bl_idname = "spritesheet.opendirectory"
    bl_label = "Open Directory"
    bl_description = ""

    directory: bpy.props.StringProperty()

    def execute(self, context):
        if not self.directory:
            return {"CANCELLED"}

        reportingProps = context.scene.ReportingPropertyGroup
        if reportingProps.fileExplorerType == "unknown":
            reportingProps.fileExplorerType = CheckFileExplorerType()

        if reportingProps.fileExplorerType == "windows":
            subprocess.Popen('explorer "{}"'.format(self.directory))
            return {"FINISHED"}

        return {"CANCELLED"}
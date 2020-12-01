import bpy
import platform
import subprocess

from util import FileSystemUtil
from util import ImageMagick
from preferences import SpritesheetAddonPreferences as Prefs

class MiscOperator(bpy.types.Operator):
    # Generic operator which can do multiple small things depending on the 'action' parameter.
    # This operator exists in lieu of making a lot of small operators to do specialized tasks.
    # (We aren't using a multi-line string to document here because Blender will make it the tooltip
    # for buttons using this operator, and we can't override that on the UI side.)

    bl_idname = "spritesheet._misc"
    bl_label = "__unused label__"

    action: bpy.props.EnumProperty(
        items = [
            ("unset", "", ""), # if called with an unknown value, Blender defaults to the first one; this makes debugging simpler
            ("locateImageMagick", "", ""),
            ("openDir", "", ""),
            ("makeRenderCameraOrtho", "", "")
        ]
    )

    directory: bpy.props.StringProperty() # for use with "openDir" action

    def invoke(self, context, event):
        # Have to set up the mapping here instead of statically since we're using instance methods
        self.__actionMappings = {
            "unset": self.__unset,
            "locateImageMagick": self._tryToFindImageMagick,
            "openDir": self._openDir,
            "makeRenderCameraOrtho": self._makeRenderCameraOrtho
        }

        return self.execute(context)

    def execute(self, context):
        if not self.action in self.__actionMappings:
            raise ValueError("Operator {} called with invalid action parameter {}".format(self.bl_idname, self.action))

        return self.__actionMappings[self.action](context)

    def _openDir(self, context):
        reportingProps = context.scene.ReportingPropertyGroup
        if reportingProps.systemType == "unchecked":
            reportingProps.systemType = FileSystemUtil.getSystemType()

        return {"FINISHED"} if FileSystemUtil.openFileExplorer(self.directory) else {"CANCELLED"}

    def _makeRenderCameraOrtho(self, context):
        props = context.scene.SpritesheetPropertyGroup

        if props.renderCamera:
            props.renderCamera.data.type = "ORTHO"

        return {"FINISHED"} if props.renderCamera else {"CANCELLED"}

    def _tryToFindImageMagick(self, context):
        imageMagickPath = ImageMagick.locateImageMagickExe()

        if not imageMagickPath:
            self.report({"ERROR"}, "Could not locate ImageMagick automatically. You will need to set the path in the add-on preferences manually.")
            return {"CANCELLED"}

        bpy.context.preferences.addons[Prefs.SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath = imageMagickPath
        self.report({"INFO"}, "Found ImageMagick installation at {}".format(imageMagickPath))

        return {"FINISHED"}

    def __unset(self, context):
        self.report({"ERROR"}, "Misc operator called incorrectly in Spritesheet Renderer addon; most likely this is an addon bug.")
        return {"CANCELLED"}
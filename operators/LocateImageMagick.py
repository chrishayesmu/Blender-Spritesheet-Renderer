import bpy

from preferences import SpritesheetAddonPreferences as Prefs
from util import ImageMagick

class LocateImageMagickOperator(bpy.types.Operator):
    bl_idname = "spritesheet.prefs_locate_imagemagick"
    bl_label = "Locate ImageMagick Installation"

    def execute(self, context):
        imageMagickPath = ImageMagick.locateImageMagickExe()

        if not imageMagickPath:
            self.report({"ERROR"}, "Could not locate ImageMagick automatically. You will need to set the path in the add-on preferences manually.")
            return {"CANCELLED"}

        bpy.context.preferences.addons[Prefs.SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath = imageMagickPath
        self.report({"INFO"}, "Found ImageMagick installation at {}".format(imageMagickPath))

        return {"FINISHED"}
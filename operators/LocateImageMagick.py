import bpy

from preferences import SpritesheetAddonPreferences as Prefs
from util import ImageMagick

class SPRITESHEET_OT_LocateImageMagickOperator(bpy.types.Operator):
    bl_idname = "spritesheet.prefs_locate_imagemagick"
    bl_label = "Locate ImageMagick Installation"

    def execute(self, _):
        image_magick_path = ImageMagick.locate_image_magick_exe()

        if not image_magick_path:
            self.report({"ERROR"}, "Could not locate ImageMagick automatically. You will need to set the path in the add-on preferences manually.")
            return {"CANCELLED"}

        bpy.context.preferences.addons[Prefs.SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath = image_magick_path
        self.report({"INFO"}, "Found ImageMagick installation at {}".format(image_magick_path))

        return {"FINISHED"}
import bpy
import os

class SpritesheetAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = os.path.basename(os.path.dirname(os.path.dirname(__file__)))

    # TODO: this isn't persisting when re-installing the addon, hence the default
    imageMagickPath: bpy.props.StringProperty(
        name = "ImageMagick Path",
        subtype = "FILE_PATH",
        description = "The path to magick.exe in the ImageMagick directory",
        default = "C:\Program Files\ImageMagick-7.0.10-Q16-HDRI\magick.exe"
    )

    def draw(self, context):
        self.layout.prop(self, "imageMagickPath")
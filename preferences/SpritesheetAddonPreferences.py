import bpy
import os

class SpritesheetAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = os.path.basename(os.path.dirname(os.path.dirname(__file__)))

    imageMagickPath: bpy.props.StringProperty(
        name = "ImageMagick Path",
        subtype = "FILE_PATH",
        description = "The path to magick.exe in the ImageMagick directory"
    )

    def draw(self, context):
        row = self.layout.row()
        row.prop(self, "imageMagickPath")

        row = self.layout.row()
        row.operator("spritesheet._misc", text = "Locate Automatically").action = "locateImageMagick"

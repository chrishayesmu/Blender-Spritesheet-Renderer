import bpy
import json
import os

def _getter(key, defaultValue):
    return lambda self: self._prefs[key] if key in self._prefs else defaultValue

def _setter(key):
    return (lambda self, value: _set(self, key, value))

def _set(obj, key, value):
    obj._prefs[key] = value

def _onUpdate(self, context, reloadAddonOnChange):
    with open(self.prefsFile, "w") as f:
        json.dump(self._prefs, f)

    if reloadAddonOnChange:
        bpy.ops.preferences.addon_enable(module=SpritesheetAddonPreferences.bl_idname)

def _updater(reloadAddonOnChange = False):
    return lambda self, context: _onUpdate(self, context, reloadAddonOnChange)

class SpritesheetAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = os.path.basename(os.path.dirname(os.path.dirname(__file__)))

    prefsFile = os.path.join(os.path.dirname(__file__), "__prefs.json")
    _prefs = {}

    imageMagickPath: bpy.props.StringProperty(
        name = "ImageMagick Path",
        subtype = "FILE_PATH",
        description = "The path to magick.exe in the ImageMagick directory",
        get = _getter("imageMagickPath", ""),
        set = _setter("imageMagickPath"),
        update = _updater()
    )

    # TODO: see about reloading the addon if this changes
    displayArea: bpy.props.EnumProperty(
        name = "Addon Display Area",
        description = "Choose where the addon's UI should be displayed",
        items = [
            ("view3d", "3D Viewport", "The addon will be in the 'Spritesheet' tab in any 3D viewport"),
            ("render_properties", "Render Properties", "The addon will be in the 'Render Properties' tab alongside other render options, such as the active render engine")
        ],
        get = _getter("displayArea", 0),
        set = _setter("displayArea"),
        update = _updater(reloadAddonOnChange = True)
    )

    @classmethod
    def register(cls):
        try:
            if os.path.isfile(cls.prefsFile):
                with open(cls.prefsFile) as f:
                    cls._prefs = json.load(f)
        except:
            # If the JSON file is malformed, we'll just load defaults
            pass

    def draw(self, context):
        row = self.layout.row()
        row.prop(self, "displayArea")

        row = self.layout.row()
        row.prop(self, "imageMagickPath")

        row = self.layout.row()
        row.operator("spritesheet.prefs_locate_imagemagick", text = "Locate Automatically")
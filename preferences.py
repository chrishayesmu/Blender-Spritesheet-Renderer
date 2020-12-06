import bpy
import json
import os
from typing import Any, Callable, Dict

def _getter(key: str, default_value: Any) -> Callable[[SpritesheetAddonPreferences], Any]:
    #pylint: disable=protected-access
    return lambda self: self._prefs[key] if key in self._prefs else default_value

def _setter(key: str) -> Callable[[SpritesheetAddonPreferences, Any], None]:
    return (lambda self, value: _set(self, key, value))

def _set(obj: SpritesheetAddonPreferences, key: str, value: Any):
    #pylint: disable=protected-access
    obj._prefs[key] = value

def _on_update(self: SpritesheetAddonPreferences, _context: bpy.types.Context, reload_addon_on_change: bool = False):
    #pylint: disable=protected-access
    with open(self.prefsFile, "w") as f:
        json.dump(self._prefs, f)

    if reload_addon_on_change:
        bpy.ops.preferences.addon_enable(module=SpritesheetAddonPreferences.bl_idname)

def _updater(reload_addon_on_change = False) -> Callable[[SpritesheetAddonPreferences, bpy.types.Context], None]:
    return lambda self, context: _on_update(self, context, reload_addon_on_change)

class SpritesheetAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = os.path.basename(os.path.dirname(__file__))

    prefsFile: str = os.path.join(os.path.dirname(__file__), "__prefs.json")
    _prefs: Dict[str, Any] = {}

    displayArea: bpy.props.EnumProperty(
        name = "Addon Display Area",
        description = "Choose where the addon's UI should be displayed",
        items = [
            ("view3d", "3D Viewport", "The addon will be in the 'Spritesheet' tab in any 3D viewport"),
            ("render_properties", "Render Properties", "The addon will be in the 'Render Properties' tab alongside other render options, such as the active render engine")
        ],
        get = _getter("displayArea", 0),
        set = _setter("displayArea"),
        update = _updater(reload_addon_on_change = True)
    )

    imageMagickPath: bpy.props.StringProperty(
        name = "ImageMagick Path",
        subtype = "FILE_PATH",
        description = "The path to magick.exe in the ImageMagick directory",
        get = _getter("imageMagickPath", ""),
        set = _setter("imageMagickPath"),
        update = _updater()
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

    def draw(self, _context):
        row = self.layout.row()
        row.prop(self, "displayArea")

        row = self.layout.row()
        row.prop(self, "imageMagickPath")

        row = self.layout.row()
        row.operator("spritesheet.prefs_locate_imagemagick", text = "Locate Automatically")

class PrefsAccess():
    """Convenience class to simplify accessing addon preferences."""
    #pylint: disable=no-self-use

    @property
    def display_area(self):
        return bpy.context.preferences.addons[SpritesheetAddonPreferences.bl_idname].preferences.displayArea

    @property
    def image_magick_path(self):
        return bpy.context.preferences.addons[SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath

    @image_magick_path.setter
    def image_magick_path(self, value: str):
        bpy.context.preferences.addons[SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath = value

# Replace class with a singleton instance
PrefsAccess = PrefsAccess()
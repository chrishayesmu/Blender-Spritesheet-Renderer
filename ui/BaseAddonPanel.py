import bpy

from preferences import SpritesheetAddonPreferences as Prefs

class BaseAddonPanel:
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def preregister(cls):
        displayArea = bpy.context.preferences.addons[Prefs.SpritesheetAddonPreferences.bl_idname].preferences.displayArea

        # Despite reloading all the modules, somehow some of this class data is being retained between
        # disabling/re-enabling the addon, so we set everything each time to be safe
        if displayArea == "render_properties":
            cls.bl_parent_id = "DATA_PT_AddonPanel"
            cls.bl_space_type = "PROPERTIES"
            cls.bl_region_type = "WINDOW"
            cls.bl_context = "render"
            cls.bl_category = ""
        elif displayArea == "view3d":
            cls.bl_space_type = "VIEW_3D"
            cls.bl_region_type = "UI"
            cls.bl_context = ""
            cls.bl_category = "Spritesheet"
            cls.bl_parent_id = ""
        else:
            raise ValueError("Unrecognized displayArea value: {}".format(displayArea))

class DATA_PT_AddonPanel(bpy.types.Panel):
    """Parent panel that holds all other addon panels when the UI is in the Render Properties area"""
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_label = "Spritesheet Renderer"

    def draw(self, context):
        pass
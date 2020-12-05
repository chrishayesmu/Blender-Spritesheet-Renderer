import bpy

from preferences import SpritesheetAddonPreferences as Prefs

class BaseAddonPanel:
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def preregister(cls):
        display_area = Prefs.PrefsAccess.display_area

        # Despite reloading all the modules, somehow some of this class data is being retained between
        # disabling/re-enabling the addon, so we set everything each time to be safe
        if display_area == "render_properties":
            cls.bl_parent_id = "SPRITESHEET_PT_AddonPanel"
            cls.bl_space_type = "PROPERTIES"
            cls.bl_region_type = "WINDOW"
            cls.bl_context = "render"
            cls.bl_category = ""
        elif display_area == "view3d":
            cls.bl_space_type = "VIEW_3D"
            cls.bl_region_type = "UI"
            cls.bl_context = ""
            cls.bl_category = "Spritesheet"
            cls.bl_parent_id = ""
        else:
            raise ValueError("Unrecognized displayArea value: {}".format(display_area))

    def template_list(self, layout, listtype_name, list_id, dataptr, propname, active_dataptr, active_propname, add_op = None, remove_op = None):
        list_obj = getattr(dataptr, propname)

        # Mostly passthrough but with a couple of standardized params
        layout.template_list(listtype_name, list_id, dataptr, propname, active_dataptr, active_propname, rows = min(5, max(1, len(list_obj))), maxrows = 5)

        if add_op or remove_op:
            col = layout.column(align = True)

            if add_op:
                col.operator(add_op, text = "", icon = "ADD")

            if remove_op:
                col.operator(remove_op, text = "", icon = "REMOVE")

class SPRITESHEET_PT_AddonPanel(bpy.types.Panel):
    """Parent panel that holds all other addon panels when the UI is in the Render Properties area"""
    bl_idname = "SPRITESHEET_PT_AddonPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_label = "Spritesheet Renderer"

    def draw(self, context):
        pass
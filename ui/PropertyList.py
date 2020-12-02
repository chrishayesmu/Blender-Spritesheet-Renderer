import bpy

class UI_UL_AnimationSelectionPropertyList(bpy.types.UIList):
    """ """
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()

        row.active = item.isSelectedForExport
        row.prop(item, "isSelectedForExport")
        row.label(text = item.name)
        row.label(text = "{} frames".format(item.numFrames))

class UI_UL_MaterialSelectionPropertyList(bpy.types.UIList):
    """ """
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()

        row.active = item.isSelectedForExport
        row.prop(item, "isSelectedForExport")
        row.label(text = item.name)
        row.prop(item, "role")

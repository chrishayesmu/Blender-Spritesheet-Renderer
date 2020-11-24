import bpy

class UI_UL_AnimationSelectionPropertyList(bpy.types.UIList):
    """ """
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        split = row.split(factor = 0.075)
        col1, col2 = (split.column(), split.column())
        
        split = col2.split(factor = 0.75)
        col2, col3 = (split.column(), split.column())

        col1.prop(item, "isSelectedForExport")
        col2.label(text = item.name)
        col3.label(text = "{} frames".format(item.numFrames))

        

class UI_UL_MaterialSelectionPropertyList(bpy.types.UIList):
    """ """

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        split = row.split(factor = 0.075)
        col1, col2 = (split.column(), split.column())
        
        split = col2.split(factor = 0.6)
        col2, col3 = (split.column(), split.column())

        col1.prop(item, "isSelectedForExport")
        col2.label(text = item.name)
        col3.prop(item, "role")
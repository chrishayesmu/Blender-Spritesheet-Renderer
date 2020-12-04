import bpy

class UI_UL_AnimationSelectionPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.active = item.isSelectedForExport
        layout.prop(item, "isSelectedForExport")
        layout.label(text = item.name)
        layout.label(text = "{} frames".format(item.numFrames))

class UI_UL_MaterialSelectionPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.active = item.isSelectedForExport
        layout.prop(item, "isSelectedForExport")
        layout.label(text = item.name)
        layout.prop(item, "role")

class SPRITESHEET_UL_ObjectMaterialPairPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        props = context.scene.SpritesheetPropertyGroup

        if props.targetObjects[index].object:
            layout.label(text = props.targetObjects[index].object.name, icon = "OBJECT_DATA")
            layout.prop(item, "materialName", text = "", icon = "MATERIAL")
        else:
            layout.active = False
            layout.label(text = f"No Object Selected in Slot {index + 1}", icon = "OBJECT_DATA")

class SPRITESHEET_UL_RenderTargetPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text = "", icon = "GRIP")
        layout.prop_search(item, "object", bpy.data, "objects", text = "")
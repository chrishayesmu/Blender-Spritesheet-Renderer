import bpy

class SPRITESHEET_UL_AnimationSelectionPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        row = layout.row()
        row.prop(item, "isSelectedForExport", text = " " + item.name)

        col = row.column()
        col.active = item.isSelectedForExport
        col.alignment = "RIGHT"
        col.label(text = f"{item.numFrames} frames")

class SPRITESHEET_UL_ObjectMaterialPairPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        props = context.scene.SpritesheetPropertyGroup

        if props.targetObjects[index].object:
            layout.label(text = props.targetObjects[index].object.name, icon = "OBJECT_DATA")
            layout.prop(item, "materialName", text = "", icon = "MATERIAL")
        else:
            layout.active = False
            layout.label(text = f"No Object Selected in Slot {index + 1}", icon = "OBJECT_DATA")

class SPRITESHEET_UL_RenderTargetPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        layout.label(text = "", icon = "GRIP")
        layout.prop_search(item, "object", bpy.data, "objects", text = "")

class SPRITESHEET_UL_RotationRootPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        if item.object:
            layout.label(text = item.object.name, icon = "OBJECT_DATA")
            layout.label(text = "rotates around")
            layout.prop_search(item, "rotationRoot", bpy.data, "objects", text = "")
        else:
            layout.active = False
            layout.label(text = f"No Object Selected in Slot {index + 1}", icon = "OBJECT_DATA")
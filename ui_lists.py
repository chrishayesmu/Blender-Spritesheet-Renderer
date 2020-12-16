import bpy

class SPRITESHEET_UL_AnimationActionPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        layout.label(text = item.target.name if item.target else "N/A", icon = "OBJECT_DATA")

        split = layout.split(factor = 0.7)
        split.label(text = item.action.name if item.action else "N/A", icon = "ACTION")

        sub = split.column()
        sub.label(text = f"Frames {item.min_frame}-{item.max_frame}" if item.action else " ")

class SPRITESHEET_UL_CameraTargetPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        layout.label(text = "", icon = "DECORATE")
        layout.prop_search(item, "target", bpy.data, "objects", text = "")

class SPRITESHEET_UL_MaterialSetTargetPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data: "MaterialSetPropertyGroup", item: "MaterialSetTargetPropertyGroup", icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        target_name = item.target.name if item.target else "N/A"
        material_name = "Shared material" if data.mode == "shared" else item.material.name if item.material else "N/A"

        layout.label(text = target_name,  icon = "OBJECT_DATA")

        sub = layout.column()
        sub.enabled = data.mode == "individual" # fade out shared material name for clarity that this won't be modifiable per-row
        sub.label(text = material_name, icon = "MATERIAL")

class SPRITESHEET_UL_RotationTargetPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        layout.label(text = "", icon = "DECORATE")
        layout.prop_search(item, "target", bpy.data, "objects", text = "")
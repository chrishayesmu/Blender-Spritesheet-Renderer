import bpy

class SPRITESHEET_UL_AnimationActionPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        # Three column layout: mesh name, action and # of frames in action,
        # with the action selection being the largest item
        col_size = .4
        split = layout.split(factor = col_size)
        split.prop_search(item, "target", bpy.data, "objects", text = "")

        # Split second half so its left column is the same as the first column
        sub = split.split(factor = col_size / (1 - col_size))
        sub.prop_search(item, "action", bpy.data, "actions", text = "")

        sub = sub.column()
        sub.alignment = "RIGHT"
        sub.label(text = f"Frames {item.min_frame}-{item.max_frame}" if item.action else "")

class SPRITESHEET_UL_RenderTargetMaterialPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        layout.prop_search(item, "target", bpy.data, "objects", text = "", icon = "OBJECT_DATA")
        layout.prop_search(item, "material", bpy.data, "materials", text = "")

class SPRITESHEET_UL_RenderTargetPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        layout.label(text = "", icon = "DECORATE")
        layout.prop_search(item, "mesh", bpy.data, "meshes", text = "")

class SPRITESHEET_UL_RotationRootPropertyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        #pylint: disable=unused-argument,no-self-use

        if item.mesh:
            layout.label(text = item.mesh.name, icon = "MESH_DATA")
            layout.label(text = "rotates around")
            layout.prop_search(item, "rotation_root", bpy.data, "objects", text = "")
        else:
            layout.active = False
            layout.label(text = f"No Mesh Selected in Slot {index + 1}", icon = "MESH_DATA")
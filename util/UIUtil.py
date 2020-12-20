import bpy
import textwrap
from typing import List, Type

import ui_panels
from util import Register

_created_types: List[Type[bpy.types.Panel]] = []

def create_panel_type(panel_type: Type[bpy.types.Panel], index: int, label: str = None):
    """Dynamically defines a new Panel type based on the type provided."""

    bl_id: str = panel_type.bl_idname if hasattr(panel_type, "bl_idname") else panel_type.__name__

    bl_id = f"{bl_id}_{index}"

    # Make sure this type/index combo isn't already created. Even if it is, we want
    # to attempt to register it again, because sometimes Blender loses them on loads.
    new_type: Type[bpy.types.Panel] = None
    for cls in panel_type.__subclasses__():
        if cls.bl_idname == bl_id:
            new_type = cls

    if not label:
        label = panel_type.bl_label

    if not new_type:
        new_type = type(bl_id, # new type name
                        (bpy.types.Panel, panel_type, ui_panels.BaseAddonPanel), # base types
                        { "bl_idname": bl_id, "bl_label": label, "index": index } # new type properties
                   )

    if new_type not in _created_types:
        _created_types.append(new_type)

    # We need to run preregister ourselves, so we can overwrite some stuff it does
    Register.preregister(new_type)
    new_type.bl_parent_id = panel_type.bl_parent_id if panel_type.bl_parent_id else new_type.bl_parent_id

    Register.register_class(new_type, run_preregister = False)

    return new_type

def message_box(context: bpy.types.Context, layout: bpy.types.UILayout, text: str, icon: str = "NONE") -> bpy.types.UILayout:
    box = layout.box()
    sub = box

    if icon:
        row = box.row(align = True)
        row.label(text = "", icon = icon)
        sub = row

    wrapped_label(context, sub, text)

    return box

def unregister_subpanels():
    for cls in _created_types:
        Register.unregister_class(cls)

    _created_types.clear()

def wrapped_label(context: bpy.types.Context, layout: bpy.types.UILayout, text: str):
    lines = wrap_text_in_region(context, text)

    col = layout.column(align = True)
    col.scale_y = .7 # bring text lines a little closer together

    for line in lines:
        col.label(text = line)

def wrap_text_in_region(context: bpy.types.Context, text: str):
    width = context.region.width
    wrapper = textwrap.TextWrapper(width = int(width / 6.5))
    return wrapper.wrap(text = text)
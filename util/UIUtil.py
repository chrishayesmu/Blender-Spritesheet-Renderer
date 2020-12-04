import bpy
import textwrap

from ui.BaseAddonPanel import BaseAddonPanel
from util import Register

def createPanelType(panelType, index, label = None, register = True):
    """Dynamically defines a new Panel type based on the type provided."""

    id = f"{panelType.bl_idname}_{index}"

    # Make sure this type/index combo isn't already created
    for cls in panelType.__subclasses__():
        if cls.bl_idname == id:
            return cls

    if not label:
        label = panelType.bl_label

    newType = type(id, # new type name
                   (bpy.types.Panel, panelType, BaseAddonPanel), # base types
                   { "bl_idname": id, "bl_label": label, "index": index } # new type properties
            )

    if register:
        # We need to run preregister ourselves, so we can overwrite some stuff it does
        Register.preregister(newType)
        newType.bl_parent_id = panelType.bl_parent_id if panelType.bl_parent_id else newType.bl_parent_id

        Register.register_class(newType, runPreregister = False)

    return newType

def unregisterSubPanels(panelType):
    for cls in panelType.__subclasses__():
        Register.unregister_class(cls)

def wrapTextInRegion(context, text):
    width = context.region.width - 10
    wrapper = textwrap.TextWrapper(width = int(width / 7))
    return wrapper.wrap(text = text)
import bpy
import textwrap

from ui.BaseAddonPanel import BaseAddonPanel
from util import Register

_createdTypes = []

def createPanelType(panelType, index, label = None):
    """Dynamically defines a new Panel type based on the type provided."""

    id = panelType.bl_idname if hasattr(panelType, "bl_idname") else panelType.__name__

    id = f"{id}_{index}"

    # Make sure this type/index combo isn't already created. Even if it is, we want
    # to attempt to register it again, because sometimes Blender loses them on loads.
    newType = None
    for cls in panelType.__subclasses__():
        if cls.bl_idname == id:
            newType = cls

    if not label:
        label = panelType.bl_label

    if not newType:
        newType = type(id, # new type name
                    (bpy.types.Panel, panelType, BaseAddonPanel), # base types
                    { "bl_idname": id, "bl_label": label, "index": index } # new type properties
                )

    if newType not in _createdTypes:
        _createdTypes.append(newType)

    # We need to run preregister ourselves, so we can overwrite some stuff it does
    Register.preregister(newType)
    newType.bl_parent_id = panelType.bl_parent_id if panelType.bl_parent_id else newType.bl_parent_id

    Register.register_class(newType, runPreregister = False)

    return newType

def unregisterSubPanels(panelType):
    for cls in _createdTypes:
        Register.unregister_class(cls)

    _createdTypes.clear()

def wrapTextInRegion(context, text):
    width = context.region.width - 10
    wrapper = textwrap.TextWrapper(width = int(width / 7))
    return wrapper.wrap(text = text)
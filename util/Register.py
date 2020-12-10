import bpy
from typing import Type

def preregister(cls: Type):
    preregister_func = getattr(cls, "preregister", None)
    if callable(preregister_func):
        preregister_func()

def register_class(cls: Type, run_preregister: bool = True):
    # bpy.utils.register_class will call a "register" method before registration if it exists,
    # but it does some validations first that prevent use cases we need in ui.BaseAddonPanel
    if run_preregister:
        preregister(cls)

    try:
        bpy.utils.register_class(cls)
    except:
        pass

def unregister_class(cls: Type):
    # Blender has trouble with some of our dynamically-created types if unregistering after
    # opening a different file, so this try/except is just to bypass those situations
    try:
        bpy.utils.unregister_class(cls)
    except:
        pass
import bpy

def preregister(cls):
    preregisterFunc = getattr(cls, "preregister", None)
    if callable(preregisterFunc):
        preregisterFunc()

def register_class(cls, runPreregister = True):
    # bpy.utils.register_class will call a "register" method before registration if it exists,
    # but it does some validations first that prevent use cases we need in ui.BaseAddonPanel
    if runPreregister:
        preregister(cls)

    bpy.utils.register_class(cls)

def unregister_class(cls):
    if hasattr(bpy.types, cls.bl_idname):
        bpy.utils.unregister_class(cls)
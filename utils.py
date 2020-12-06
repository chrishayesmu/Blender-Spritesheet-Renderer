import bpy

def find_object_data_for_camera(camera: bpy.types.Camera) -> bpy.types.Object:
    objects_by_camera = bpy.data.user_map([camera], key_types = {"CAMERA"}, value_types = {"OBJECT"})

    if len(objects_by_camera[camera]) == 0:
        raise LookupError(f"Could not find any object data matching the camera {camera}")

    if len(objects_by_camera[camera]) > 1:
        raise LookupError(f"Camera {camera} is linked to multiple object blocks")

    return objects_by_camera[camera]
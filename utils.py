import bpy

def enum_display_name_from_identifier(prop_group: bpy.types.PropertyGroup, prop_name: str, prop_identifier: str) -> str:
    assert hasattr(prop_group, "bl_rna"), "Incorrect item passed for enum_prop"
    assert prop_name in prop_group.bl_rna.properties, "Incorrect string passed for prop_name"
    assert isinstance(prop_group.bl_rna.properties[prop_name], bpy.types.EnumProperty), "Provided property is not an EnumProperty"

    # Throws if the identifier given isn't in the property
    return [item.name for item in prop_group.bl_rna.properties[prop_name].enum_items if item.identifier == prop_identifier][0]

def find_object_data_for_camera(camera: bpy.types.Camera) -> bpy.types.Object:
    objects_by_camera = bpy.data.user_map([camera], key_types = {"CAMERA"}, value_types = {"OBJECT"})

    if len(objects_by_camera[camera]) == 0:
        raise LookupError(f"Could not find any object data matching the camera {camera}")

    if len(objects_by_camera[camera]) > 1:
        raise LookupError(f"Camera {camera} is linked to multiple object blocks")

    return objects_by_camera[camera]
import bpy
import math
import os
from typing import Any, Iterable, Optional

def blend_file_name(default_value: Optional[str] = None) -> Optional[str]:
    """Returns the .blend file name without its extension if the file has been saved, or default_value if not."""
    if not bpy.data.filepath:
        return default_value

    base = os.path.basename(bpy.data.filepath)
    filename, _ = os.path.splitext(base)
    return filename

def enum_display_name_from_identifier(prop_group: bpy.types.PropertyGroup, prop_name: str, prop_identifier: str) -> str:
    assert hasattr(prop_group, "bl_rna"), "Incorrect item passed for enum_prop"
    assert prop_name in prop_group.bl_rna.properties, "Incorrect string passed for prop_name"
    assert isinstance(prop_group.bl_rna.properties[prop_name], bpy.types.EnumProperty), "Provided property is not an EnumProperty"

    # Throws if the identifier given isn't in the property
    return [item.name for item in prop_group.bl_rna.properties[prop_name].enum_items if item.identifier == prop_identifier][0]

def get_exception_message(e: Exception) -> str:
    return e.message if hasattr(e, "message") else str(e.args[0]) if len(e.args) > 0 else "An unknown error occurred."

def find_object_data_for_camera(camera: bpy.types.Camera) -> bpy.types.Object:
    objects_by_camera = bpy.data.user_map([camera], key_types = {"CAMERA"}, value_types = {"OBJECT"})

    if len(objects_by_camera[camera]) == 0:
        raise LookupError(f"Could not find any object data matching the camera {camera}")

    if len(objects_by_camera[camera]) > 1:
        raise LookupError(f"Camera {camera} is linked to multiple object blocks")

    return next(iter(objects_by_camera[camera]))

def find_object_data_for_mesh(mesh: bpy.types.Mesh) -> bpy.types.Object:
    objects_by_mesh = bpy.data.user_map([mesh], key_types = {"MESH"}, value_types = {"OBJECT"})

    if len(objects_by_mesh[mesh]) == 0:
        raise LookupError(f"Could not find any object data matching the mesh {mesh}")

    if len(objects_by_mesh[mesh]) > 1:
        raise LookupError(f"Mesh {mesh} is linked to multiple object blocks")

    return next(iter(objects_by_mesh[mesh]))

def repeated_entries(iterable: Iterable[Any]) -> Iterable[Any]:
    seen = []
    repeats = []

    for val in iterable:
        if val in seen and val not in repeats:
            repeats.append(val)

        seen.append(val)

    return repeats

def rotate_objects(objects: Iterable[bpy.types.Object], x_rot_degrees: Optional[float] = None, y_rot_degrees: Optional[float] = None, z_rot_degrees: Optional[float] = None):
    assert not (x_rot_degrees is None and y_rot_degrees is None and z_rot_degrees is None), "No rotation values were passed"

    for obj in objects:
        # None values indicate to preserve the existing rotation on that axis
        x_rot: float = math.radians(x_rot_degrees) if x_rot_degrees is not None else obj.rotation_euler[0]
        y_rot: float = math.radians(y_rot_degrees) if y_rot_degrees is not None else obj.rotation_euler[1]
        z_rot: float = math.radians(z_rot_degrees) if z_rot_degrees is not None else obj.rotation_euler[2]

        obj.rotation_euler = (x_rot, y_rot, z_rot)
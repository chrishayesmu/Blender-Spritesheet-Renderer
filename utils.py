import bpy
import math
import os
from typing import Optional

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

def rotate_render_targets(props: "SpritesheetPropertyGroup", x_rot_degrees: Optional[float] = None, y_rot_degrees: Optional[float] = None, z_rot_degrees: Optional[float] = None):
    assert not (x_rot_degrees is None and y_rot_degrees is None and z_rot_degrees is None), "No rotation values were passed"

    for render_target in props.render_targets:
        rotation_root = render_target.rotation_root if render_target.rotation_root else render_target.mesh_object

        # None values indicate to preserve the existing rotation on that axis
        x_rot: float = math.radians(x_rot_degrees) if x_rot_degrees is not None else rotation_root.rotation_euler[0]
        y_rot: float = math.radians(y_rot_degrees) if y_rot_degrees is not None else rotation_root.rotation_euler[1]
        z_rot: float = math.radians(z_rot_degrees) if z_rot_degrees is not None else rotation_root.rotation_euler[2]

        rotation_root.rotation_euler = (x_rot, y_rot, z_rot)
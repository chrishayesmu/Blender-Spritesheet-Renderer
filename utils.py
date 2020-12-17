import bpy
import math
import os
import sys
from typing import Any, Iterable, Optional

def blend_file_name(default_value: Optional[str] = None) -> Optional[str]:
    """Returns the .blend file name without its extension if the file has been saved, or default_value if not."""
    if not bpy.data.filepath:
        return default_value

    base = os.path.basename(bpy.data.filepath)
    filename, _ = os.path.splitext(base)
    return filename

def close_stdout():
    class StdoutContextManager:
        def __enter__(self):
            # Get the original stdout file, close its fd, and open devnull in its place
            self._original_stdout = os.dup(1)
            sys.stdout.flush()
            os.close(1)
            os.open(os.devnull, os.O_WRONLY)

        def __exit__(self, exc_type, exc_val, exc_tb):
            # Close the devnull stdout, duplicate the original (giving it fd 1), and close the duplicate
            os.close(1)
            os.dup(self._original_stdout)
            os.close(self._original_stdout)

    return StdoutContextManager()

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

def force_redraw_ui():
    # Frustratingly, this seems to be the only way to actually get Blender to redraw our panels -
    # tagging the areas/regions for redraw doesn't do it. So, even though this is bad practice,
    # we do it so the UI actually reflects what's going on.
    #
    # Also, this op prints some timing info to stdout, so we just suppress that too.
    with close_stdout():
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

def repeated_entries(iterable: Iterable[Any]) -> Iterable[Any]:
    seen = []
    repeats = []

    for val in iterable:
        if val in seen and val not in repeats:
            repeats.append(val)

        seen.append(val)

    return repeats

def rotate_objects(objects: Iterable[bpy.types.Object], x_rot_degrees: Optional[float] = None, y_rot_degrees: Optional[float] = None, z_rot_degrees: Optional[float] = None):
    # TODO: move this logic into the RotationOptionsPropertyGroup
    assert not (x_rot_degrees is None and y_rot_degrees is None and z_rot_degrees is None), "No rotation values were passed"

    for obj in objects:
        # None values indicate to preserve the existing rotation on that axis
        x_rot: float = math.radians(x_rot_degrees) if x_rot_degrees is not None else obj.rotation_euler[0]
        y_rot: float = math.radians(y_rot_degrees) if y_rot_degrees is not None else obj.rotation_euler[1]
        z_rot: float = math.radians(z_rot_degrees) if z_rot_degrees is not None else obj.rotation_euler[2]

        obj.rotation_euler = (x_rot, y_rot, z_rot)

def tag_redraw_area(context: bpy.types.Context, area_type: str):
    for area in context.window.screen.areas:
        if area.type == area_type:
            area.tag_redraw()

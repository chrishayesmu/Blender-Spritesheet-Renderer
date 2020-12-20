import bpy
from bpy.app.handlers import persistent
import functools
import importlib
import math
import os
import sys
from typing import Any, Callable, List, Type, Union

# Disable undefined-variable because our module imports are dynamic
#pylint: disable=undefined-variable

bl_info = {
    "name": "Spritesheet Renderer",
    "description": "Add-on automating the process of rendering a 3D model as a spritesheet.",
    "author": "Chris Hayes",
    "version": (2, 1, 0),
    "blender": (2, 90, 0),
    "location": "View3D > UI > Spritesheet",
    "support": "COMMUNITY",
    "tracker": "https://github.com/chrishayesmu/Blender-Spritesheet-Renderer/issues",
    "category": "Animation"
}

# Local files
ADDON_DIR = os.path.dirname(os.path.realpath(__file__))
if not ADDON_DIR in sys.path:
    sys.path.append(ADDON_DIR)

# Pretty hacky here: we define all the modules as strings and load them dynamically so that we can easily reload them multiple times
# Otherwise we have to load and reload them in dependency order and frequently we find our changes not taking effect during development
module_defs = [
    "utils",
    "property_groups",
    "operators",
    "render_operator",
    "preferences",
    "ui_lists",
    "ui_panels",
    ("util", ["Bounds", "Camera", "FileSystemUtil", "ImageMagick", "Register", "SceneSnapshot", "StringUtil", "TerminalOutput", "UIUtil"])
]

_locals = locals()
_modules = []
for module_def in module_defs:
    if isinstance(module_def, str):
        module = importlib.import_module(module_def)
        importlib.reload(module)

        _locals[module_def] = module
        _modules.append(module)
    elif isinstance(module_def, tuple):
        module_name = module_def[0]
        submods = module_def[1]

        # Don't add the parent module into locals, only submodules
        root_module = importlib.import_module(module_name)
        importlib.reload(root_module)

        for submod_name in submods:
            submodule = getattr(root_module, submod_name)
            importlib.reload(submodule)

            _locals[submod_name] = submodule
            _modules.append(submodule)

# Reload everything again just to be sure the latest changes are picked up
for mod in _modules:
    importlib.reload(mod)

# This operator is in the main file so it has the correct module path
class SPRITESHEET_OT_ShowAddonPrefsOperator(bpy.types.Operator):
    bl_idname = "spritesheet.showprefs"
    bl_label = "Open Addon Preferences"
    bl_description = "Opens the addon preferences for Spritesheet Renderer"

    def execute(self, _context):
        bpy.ops.preferences.addon_show(module = __package__)
        return {'FINISHED'}

def check_animation_state():
    # Periodically check whether animations are playing so we can keep our animation set
    # status up-to-date. Unfortunately there's no event handler for animation playback starting/stopping.
    if not bpy.context.screen.is_animation_playing:
        props = bpy.context.scene.SpritesheetPropertyGroup

        for animation_set in props.animation_options.animation_sets:
            animation_set.is_previewing = False

    return 1.0 # check every second for responsiveness, since this is cheap

def find_image_magick_exe():
    # Only look for the exe if the path isn't already set
    if not preferences.PrefsAccess.image_magick_path:
        bpy.ops.spritesheet.prefs_locate_imagemagick()

@persistent
def initialize_collections(_unused: None):
    """Initializes certain CollectionProperty objects that otherwise would be empty."""
    props = bpy.context.scene.SpritesheetPropertyGroup

    if len(props.camera_options.targets) == 0:
        props.camera_options.targets.add()

    if len(props.rotation_options.targets) == 0:
        props.rotation_options.targets.add()

    ### Initialize animation sets
    if len(props.animation_options.animation_sets) == 0:
        # spritesheet.add_animation_set's poll method requires control_animations to be true, so temporarily set it
        control_animations = props.animation_options.control_animations
        props.animation_options.control_animations = True
        bpy.ops.spritesheet.add_animation_set()
        props.animation_options.control_animations = control_animations

    for i in range(0, len(props.animation_options.animation_sets)):
        ui_panels.SPRITESHEET_PT_AnimationSetPanel.create_sub_panel(i)

    ### Initialize material sets

    if len(props.material_options.material_sets) == 0:
        # spritesheet.add_material_set's poll method requires control_materials to be true, so temporarily set it
        control_materials = props.material_options.control_materials
        props.material_options.control_materials = True
        bpy.ops.spritesheet.add_material_set()
        props.material_options.control_materials = control_materials

    for i in range(0, len(props.material_options.material_sets)):
        ui_panels.SPRITESHEET_PT_MaterialSetPanel.create_sub_panel(i)

@persistent
def reset_reporting_props(_unused: None):
    reporting_props = bpy.context.scene.ReportingPropertyGroup

    reporting_props.current_frame_num = 0
    reporting_props.elapsed_time = 0
    reporting_props.has_any_job_started = False
    reporting_props.job_in_progress = False
    reporting_props.last_error_message = ""
    reporting_props.output_directory = ""
    reporting_props.total_num_frames = 0

classes: List[Union[Type[bpy.types.Panel], Type[bpy.types.UIList], Type[bpy.types.Operator]]] = [
    # Property groups
    property_groups.AnimationSetTargetPropertyGroup,
    property_groups.AnimationSetPropertyGroup,
    property_groups.AnimationOptionsPropertyGroup,
    property_groups.CameraTargetPropertyGroup,
    property_groups.CameraOptionsPropertyGroup,
    property_groups.MaterialSetTargetPropertyGroup,
    property_groups.MaterialSetPropertyGroup,
    property_groups.MaterialOptionsPropertyGroup,
    property_groups.ReportingPropertyGroup,
    property_groups.RotationTargetPropertyGroup,
    property_groups.RotationOptionsPropertyGroup,
    property_groups.SpritesheetPropertyGroup,

    preferences.SpritesheetAddonPreferences,

    # Operators
    SPRITESHEET_OT_ShowAddonPrefsOperator,
    operators.SPRITESHEET_OT_AddAnimationSetOperator,
    operators.SPRITESHEET_OT_AddCameraTargetOperator,
    operators.SPRITESHEET_OT_AddMaterialSetOperator,
    operators.SPRITESHEET_OT_AddRotationTargetOperator,
    operators.SPRITESHEET_OT_AssignMaterialSetOperator,
    operators.SPRITESHEET_OT_ConfigureRenderCameraOperator,
    operators.SPRITESHEET_OT_LocateImageMagickOperator,
    operators.SPRITESHEET_OT_ModifyAnimationSetOperator,
    operators.SPRITESHEET_OT_ModifyMaterialSetOperator,
    operators.SPRITESHEET_OT_MoveCameraTargetDownOperator,
    operators.SPRITESHEET_OT_MoveCameraTargetUpOperator,
    operators.SPRITESHEET_OT_MoveRotationTargetDownOperator,
    operators.SPRITESHEET_OT_MoveRotationTargetUpOperator,
    operators.SPRITESHEET_OT_OpenDirectoryOperator,
    operators.SPRITESHEET_OT_OptimizeCameraOperator,
    operators.SPRITESHEET_OT_PlayAnimationSetOperator,
    operators.SPRITESHEET_OT_RemoveAnimationSetOperator,
    operators.SPRITESHEET_OT_RemoveCameraTargetOperator,
    operators.SPRITESHEET_OT_RemoveMaterialSetOperator,
    operators.SPRITESHEET_OT_RemoveRotationTargetOperator,

    render_operator.SPRITESHEET_OT_RenderSpritesheetOperator,

    # UI property lists
    ui_lists.SPRITESHEET_UL_AnimationActionPropertyList,
    ui_lists.SPRITESHEET_UL_CameraTargetPropertyList,
    ui_lists.SPRITESHEET_UL_MaterialSetTargetPropertyList,
    ui_lists.SPRITESHEET_UL_RotationTargetPropertyList,

    # UI panels
    ui_panels.SPRITESHEET_PT_AddonPanel,
    ui_panels.SPRITESHEET_PT_OutputPropertiesPanel,
    ui_panels.SPRITESHEET_PT_AnimationsPanel,
    ui_panels.SPRITESHEET_PT_CameraPanel,
    ui_panels.SPRITESHEET_PT_MaterialsPanel,
    ui_panels.SPRITESHEET_PT_RotationOptionsPanel,
    ui_panels.SPRITESHEET_PT_JobManagementPanel
]

def register():
    for cls in classes:
        Register.register_class(cls)

    bpy.types.Scene.SpritesheetPropertyGroup = bpy.props.PointerProperty(type = property_groups.SpritesheetPropertyGroup)
    bpy.types.Scene.ReportingPropertyGroup = bpy.props.PointerProperty(type = property_groups.ReportingPropertyGroup)

    # Most handlers need to happen when the addon is enabled and also when a new .blend file is opened
    start_timer(check_animation_state, first_interval = .1, is_persistent = True)
    start_timer(find_image_magick_exe, first_interval = .1)
    start_timer(initialize_collections, make_partial = True)
    start_timer(reset_reporting_props, make_partial = True)

    bpy.app.handlers.load_post.append(initialize_collections)
    bpy.app.handlers.load_post.append(reset_reporting_props)

def unregister():
    for timer in timers:
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)

    bpy.app.handlers.load_post.remove(initialize_collections)
    bpy.app.handlers.load_post.remove(reset_reporting_props)

    del bpy.types.Scene.ReportingPropertyGroup
    del bpy.types.Scene.SpritesheetPropertyGroup

    UIUtil.unregister_subpanels()

    for cls in reversed(classes):
        Register.unregister_class(cls)

timers: List[Callable] = []

def start_timer(func: Callable, make_partial: bool = False, first_interval: float = 0, is_persistent: bool = False):
    if make_partial:
        func = functools.partial(func, None)

    bpy.app.timers.register(func, first_interval = first_interval, persistent = is_persistent)
    timers.append(func)

# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
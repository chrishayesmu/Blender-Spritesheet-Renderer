import bpy
from bpy.app.handlers import persistent
import functools
import importlib
import math
import os
import sys
from typing import Any, Callable, List, Type, Union

bl_info = {
    "name": "Spritesheet Renderer",
    "description": "Add-on automating the process of rendering a 3D model as a spritesheet.",
    "author": "Chris Hayes",
    "version": (1, 0, 1),
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

from operators import ConfigureRenderCamera
importlib.reload(ConfigureRenderCamera)
from operators import ListOperators
importlib.reload(ListOperators)
from operators import LocateImageMagick
importlib.reload(LocateImageMagick)
from operators import OpenDirectory
importlib.reload(OpenDirectory)
from operators import RenderSpritesheet
importlib.reload(RenderSpritesheet)

import preferences
importlib.reload(preferences)

import property_groups
importlib.reload(property_groups)

import ui_lists
importlib.reload(ui_lists)
import ui_panels
importlib.reload(ui_panels)

from util import Bounds
importlib.reload(Bounds)
from util import Camera
importlib.reload(Camera)
from util import FileSystemUtil
importlib.reload(FileSystemUtil)
from util import ImageMagick
importlib.reload(ImageMagick)
from util import Register
importlib.reload(Register)
from util import SceneSnapshot
importlib.reload(SceneSnapshot)
from util import StringUtil
importlib.reload(StringUtil)
from util import TerminalOutput
importlib.reload(TerminalOutput)
from util import UIUtil
importlib.reload(UIUtil)

import utils
importlib.reload(utils)

# This operator is in the main file so it has the correct module path
class SPRITESHEET_OT_ShowAddonPrefsOperator(bpy.types.Operator):
    bl_idname = "spritesheet.showprefs"
    bl_label = "Open Addon Preferences"
    bl_description = "Opens the addon preferences for Spritesheet Renderer"

    def execute(self, _context):
        bpy.ops.preferences.addon_show(module = __package__)
        return {'FINISHED'}

def find_image_magick_exe():
    # Only look for the exe if the path isn't already set
    if not preferences.PrefsAccess.image_magick_path:
        bpy.ops.spritesheet.prefs_locate_imagemagick()

@persistent
def initialize_collections(_unused: None):
    """Initializes certain CollectionProperty objects that otherwise would be empty."""
    props = bpy.context.scene.SpritesheetPropertyGroup

    if len(props.render_targets) == 0:
        bpy.ops.spritesheet.add_render_target()

    if len(props.materialSets) == 0:
        # spritesheet.add_material_set's poll method requires useMaterials to be true, so temporarily set it
        use_materials = props.useMaterials
        props.useMaterials = True
        bpy.ops.spritesheet.add_material_set()
        props.useMaterials = use_materials

    # Each material set should have the same number of items as there are render targets
    num_render_targets = len(props.render_targets)
    for material_set in props.materialSets:
        assert len(material_set.objectMaterialPairs) <= num_render_targets, f"There are more objectMaterialPairs in material set {material_set} than there are render targets"

        while len(material_set.objectMaterialPairs) < num_render_targets:
            pair = material_set.objectMaterialPairs.add()
            pair.set_material_from_mesh(bpy.context, len(material_set.objectMaterialPairs) - 1)

    for i in range(0, len(props.materialSets)):
        ui_panels.SPRITESHEET_PT_MaterialSetPanel.create_sub_panel(i)

@persistent
def populate_animation_selections(_unused: None):
    scene = bpy.context.scene
    props = scene.SpritesheetPropertyGroup
    props.animationSelections.clear()

    for _, action in enumerate(bpy.data.actions):
        selection = props.animationSelections.add()
        selection.name = action.name
        selection.numFrames = math.ceil(action.frame_range[1]) - math.floor(action.frame_range[0])

    return 10.0

@persistent
def reset_reporting_props(_unused: None):
    reporting_props = bpy.context.scene.ReportingPropertyGroup

    reporting_props.currentFrameNum = 0
    reporting_props.elapsedTime = 0
    reporting_props.hasAnyJobStarted = False
    reporting_props.jobInProgress = False
    reporting_props.lastErrorMessage = ""
    reporting_props.outputDirectory = ""
    reporting_props.systemType = FileSystemUtil.get_system_type()
    reporting_props.totalNumFrames = 0

classes: List[Union[Type[bpy.types.Panel], Type[bpy.types.UIList], Type[bpy.types.Operator]]] = [
    # Property groups
    property_groups.AnimationSelectionPropertyGroup,
    property_groups.RenderTargetMaterialPropertyGroup,
    property_groups.MaterialSetPropertyGroup,
    property_groups.RenderTargetPropertyGroup,
    property_groups.ReportingPropertyGroup,
    property_groups.SpritesheetPropertyGroup,

    preferences.SpritesheetAddonPreferences,

    # Operators
    SPRITESHEET_OT_ShowAddonPrefsOperator,
    ConfigureRenderCamera.SPRITESHEET_OT_ConfigureRenderCameraOperator,
    ListOperators.SPRITESHEET_OT_AddMaterialSetOperator,
    ListOperators.SPRITESHEET_OT_RemoveMaterialSetOperator,
    ListOperators.SPRITESHEET_OT_AddRenderTargetOperator,
    ListOperators.SPRITESHEET_OT_RemoveRenderTargetOperator,
    ListOperators.SPRITESHEET_OT_MoveRenderTargetUpOperator,
    ListOperators.SPRITESHEET_OT_MoveRenderTargetDownOperator,
    LocateImageMagick.SPRITESHEET_OT_LocateImageMagickOperator,
    OpenDirectory.SPRITESHEET_OT_OpenDirectoryOperator,
    RenderSpritesheet.SPRITESHEET_OT_RenderSpritesheetOperator,

    # UI property lists
    ui_lists.SPRITESHEET_UL_AnimationSelectionPropertyList,
    ui_lists.SPRITESHEET_UL_RenderTargetMaterialPropertyList,
    ui_lists.SPRITESHEET_UL_RenderTargetPropertyList,
    ui_lists.SPRITESHEET_UL_RotationRootPropertyList,

    # UI panels
    ui_panels.SPRITESHEET_PT_AddonPanel,
    ui_panels.SPRITESHEET_PT_RenderTargetsPanel,
    ui_panels.SPRITESHEET_PT_AnimationsPanel,
    ui_panels.SPRITESHEET_PT_CameraPanel,
    ui_panels.SPRITESHEET_PT_MaterialsPanel,
    ui_panels.SPRITESHEET_PT_RotationOptionsPanel,
    ui_panels.SPRITESHEET_PT_OutputPropertiesPanel,
    ui_panels.SPRITESHEET_PT_JobManagementPanel
]

def register():
    for cls in classes:
        Register.register_class(cls)

    bpy.types.Scene.SpritesheetPropertyGroup = bpy.props.PointerProperty(type = property_groups.SpritesheetPropertyGroup)
    bpy.types.Scene.ReportingPropertyGroup = bpy.props.PointerProperty(type = property_groups.ReportingPropertyGroup)

    # Most handlers need to happen when the addon is enabled and also when a new .blend file is opened
    start_timer(find_image_magick_exe, first_interval = .1)
    start_timer(initialize_collections, make_partial = True, is_persistent = True)
    start_timer(populate_animation_selections, make_partial = True, is_persistent = True)
    start_timer(reset_reporting_props, make_partial = True, is_persistent = True)

    bpy.app.handlers.load_post.append(initialize_collections)
    bpy.app.handlers.load_post.append(populate_animation_selections)
    bpy.app.handlers.load_post.append(reset_reporting_props)

def unregister():
    for timer in timers:
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)

    bpy.app.handlers.load_post.remove(initialize_collections)
    bpy.app.handlers.load_post.remove(populate_animation_selections)
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
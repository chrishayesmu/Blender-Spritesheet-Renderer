import bpy
from bpy.app.handlers import persistent
import functools
import importlib
import math
import os
import sys

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

from preferences import SpritesheetAddonPreferences as Prefs
importlib.reload(Prefs)

from property_groups import SpritesheetPropertyGroup
importlib.reload(SpritesheetPropertyGroup)

# UI panels
from ui import BaseAddonPanel
importlib.reload(BaseAddonPanel)
from ui import AnimationsPanel
importlib.reload(AnimationsPanel)
from ui import CameraPanel
importlib.reload(CameraPanel)
from ui import OutputPropertiesPanel
importlib.reload(OutputPropertiesPanel)
from ui import JobManagementPanel
importlib.reload(JobManagementPanel)
from ui import MaterialsPanel
importlib.reload(MaterialsPanel)
from ui import MaterialSetPanel
importlib.reload(MaterialSetPanel)
from ui import RotationOptionsPanel
importlib.reload(RotationOptionsPanel)
from ui import TargetObjectsPanel
importlib.reload(TargetObjectsPanel)

# Other UI
from ui import PropertyList
importlib.reload(PropertyList)

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
    if not Prefs.PrefsAccess.image_magick_path:
        bpy.ops.spritesheet.prefs_locate_imagemagick()

@persistent
def initialize_collections(_unused):
    """Initializes certain CollectionProperty objects that otherwise would be empty."""
    props = bpy.context.scene.SpritesheetPropertyGroup

    if len(props.materialSets) == 0:
        # spritesheet.add_material_set's poll method requires useMaterials to be true, so temporarily set it
        use_materials = props.useMaterials
        props.useMaterials = True
        bpy.ops.spritesheet.add_material_set()
        props.useMaterials = use_materials

    for i in range(0, len(props.materialSets)):
        MaterialSetPanel.SPRITESHEET_PT_MaterialSetPanel.create_sub_panel(i)

    if len(props.targetObjects) == 0:
        bpy.ops.spritesheet.add_render_target()

@persistent
def populate_animation_selections(_unused):
    scene = bpy.context.scene
    props = scene.SpritesheetPropertyGroup
    props.animationSelections.clear()

    for _, action in enumerate(bpy.data.actions):
        selection = props.animationSelections.add()
        selection.name = action.name
        selection.numFrames = math.ceil(action.frame_range[1]) - math.floor(action.frame_range[0])

    return 10.0

@persistent
def reset_reporting_props(_unused):
    reporting_props = bpy.context.scene.ReportingPropertyGroup

    reporting_props.currentFrameNum = 0
    reporting_props.elapsedTime = 0
    reporting_props.hasAnyJobStarted = False
    reporting_props.jobInProgress = False
    reporting_props.lastErrorMessage = ""
    reporting_props.outputDirectory = ""
    reporting_props.systemType = FileSystemUtil.get_system_type()
    reporting_props.totalNumFrames = 0

classes = [
    # Property groups
    SpritesheetPropertyGroup.AnimationSelectionPropertyGroup,
    SpritesheetPropertyGroup.MaterialSelectionPropertyGroup,
    SpritesheetPropertyGroup.ObjectMaterialPairPropertyGroup,
    SpritesheetPropertyGroup.MaterialSetPropertyGroup,
    SpritesheetPropertyGroup.RenderTargetPropertyGroup,
    SpritesheetPropertyGroup.ReportingPropertyGroup,
    SpritesheetPropertyGroup.SpritesheetPropertyGroup,

    Prefs.SpritesheetAddonPreferences,

    # Operators
    SPRITESHEET_OT_ShowAddonPrefsOperator,
    ConfigureRenderCamera.SPRITESHEET_OT_ConfigureRenderCameraOperator,
    ListOperators.SPRITESHEET_OT_AddMaterialSetOperator,
    ListOperators.SPRITESHEET_OT_RemoveMaterialSetOperator,
    ListOperators.SPRITESHEET_OT_AddRenderTargetOperator,
    ListOperators.SPRITESHEET_OT_RemoveRenderTargetOperator,
    LocateImageMagick.SPRITESHEET_OT_LocateImageMagickOperator,
    OpenDirectory.SPRITESHEET_OT_OpenDirectoryOperator,
    RenderSpritesheet.SPRITESHEET_OT_RenderSpritesheetOperator,

    # UI property lists
    PropertyList.SPRITESHEET_UL_AnimationSelectionPropertyList,
    PropertyList.SPRITESHEET_UL_ObjectMaterialPairPropertyList,
    PropertyList.SPRITESHEET_UL_RenderTargetPropertyList,
    PropertyList.SPRITESHEET_UL_RotationRootPropertyList,

    # UI panels
    BaseAddonPanel.SPRITESHEET_PT_AddonPanel,
    TargetObjectsPanel.SPRITESHEET_PT_TargetObjectsPanel,
    AnimationsPanel.SPRITESHEET_PT_AnimationsPanel,
    CameraPanel.SPRITESHEET_PT_CameraPanel,
    MaterialsPanel.SPRITESHEET_PT_MaterialsPanel,
    RotationOptionsPanel.SPRITESHEET_PT_RotationOptionsPanel,
    OutputPropertiesPanel.SPRITESHEET_PT_OutputPropertiesPanel,
    JobManagementPanel.SPRITESHEET_PT_JobManagementPanel
]

timers = []

def register():
    for cls in classes:
        Register.register_class(cls)

    bpy.types.Scene.SpritesheetPropertyGroup = bpy.props.PointerProperty(type = SpritesheetPropertyGroup.SpritesheetPropertyGroup)
    bpy.types.Scene.ReportingPropertyGroup = bpy.props.PointerProperty(type = SpritesheetPropertyGroup.ReportingPropertyGroup)

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

def start_timer(func, make_partial = False, first_interval = 0, is_persistent = False):
    if make_partial:
        func = functools.partial(func, None)

    bpy.app.timers.register(func, first_interval = first_interval, persistent = is_persistent)
    timers.append(func)

# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
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

    def execute(self, context):
        bpy.ops.preferences.addon_show(module = __package__)
        return {'FINISHED'}

def findImageMagickExe():
    # Only look for the exe if the path isn't already set
    if not bpy.context.preferences.addons[Prefs.SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath:
        bpy.ops.spritesheet.prefs_locate_imagemagick()

@persistent
def initializeCollections(_unused):
    """Initializes certain CollectionProperty objects that otherwise would be empty."""
    props = bpy.context.scene.SpritesheetPropertyGroup

    if len(props.materialSets) == 0:
        bpy.ops.spritesheet.add_material_set()

    # TODO something is causing material set panels to be lost when first loading Blender
    print(f"There are {len(props.materialSets)} material sets")
    for i in range(0, len(props.materialSets)):
        MaterialSetPanel.SPRITESHEET_PT_MaterialSetPanel.createSubPanel(i)

    if len(props.targetObjects) == 0:
        bpy.ops.spritesheet.add_render_target()

@persistent
def populateAnimationSelections(_unused):
    scene = bpy.context.scene
    props = scene.SpritesheetPropertyGroup
    props.animationSelections.clear()
    
    for index, action in enumerate(bpy.data.actions):
        selection = props.animationSelections.add()
        selection.name = action.name
        selection.numFrames = math.ceil(action.frame_range[1]) - math.floor(action.frame_range[0])

    return 10.0

@persistent
def resetReportingProps(_unused):
    reportingProps = bpy.context.scene.ReportingPropertyGroup

    reportingProps.currentFrameNum = 0
    reportingProps.elapsedTime = 0
    reportingProps.hasAnyJobStarted = False
    reportingProps.jobInProgress = False
    reportingProps.lastErrorMessage = ""
    reportingProps.outputDirectory = ""
    reportingProps.systemType = FileSystemUtil.getSystemType()
    reportingProps.totalNumFrames = 0

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
    startTimer(findImageMagickExe, first_interval = .1)
    startTimer(initializeCollections, make_partial = True, persistent = True)
    startTimer(populateAnimationSelections, make_partial = True, persistent = True)
    startTimer(resetReportingProps, make_partial = True, persistent = True)

    bpy.app.handlers.load_post.append(initializeCollections)
    bpy.app.handlers.load_post.append(populateAnimationSelections)
    bpy.app.handlers.load_post.append(resetReportingProps)

def unregister():
    for timer in timers:
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)

    bpy.app.handlers.load_post.remove(initializeCollections)
    bpy.app.handlers.load_post.remove(populateAnimationSelections)
    bpy.app.handlers.load_post.remove(resetReportingProps)

    del bpy.types.Scene.ReportingPropertyGroup
    del bpy.types.Scene.SpritesheetPropertyGroup
    
    UIUtil.unregisterSubPanels(MaterialSetPanel.SPRITESHEET_PT_MaterialSetPanel)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

def startTimer(func, make_partial = False, first_interval = 0, persistent = False):
    if make_partial:
        func = functools.partial(func, None)

    bpy.app.timers.register(func, first_interval = first_interval, persistent = persistent)
    timers.append(func)

# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
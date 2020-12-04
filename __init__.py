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
from operators import LocateImageMagick
importlib.reload(LocateImageMagick)
from operators import ModifyRenderTargets
importlib.reload(ModifyRenderTargets)
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
from ui import FilePathsPanel
importlib.reload(FilePathsPanel)
from ui import MaterialsPanel
importlib.reload(MaterialsPanel)
from ui import MaterialSetPanel
importlib.reload(MaterialSetPanel)
from ui import RenderPropertiesPanel
importlib.reload(RenderPropertiesPanel)
from ui import ReportingPanel
importlib.reload(ReportingPanel)
from ui import ScenePropertiesPanel
importlib.reload(ScenePropertiesPanel)

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
class ShowAddonPrefsOperator(bpy.types.Operator):
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
        MaterialSetPanel.MaterialSetPanel.createSubPanel(i)

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
def populateMaterialSelections(_unused):
    props = bpy.context.scene.SpritesheetPropertyGroup
    props.materialSelections.clear()

    # TODO material selections aren't persisting; some selections are lost
    for index in range (0, len(bpy.data.materials)):
        selection = props.materialSelections.add()
        selection.name = bpy.data.materials[index].name
        selection.index = index
        nameLower = selection.name.lower()

        if "albedo" in nameLower or "base" in nameLower or "color" in nameLower:
            selection.role = "albedo"
        elif "mask" in nameLower:
            selection.role = "mask_unity"
        elif "normal" in nameLower:
            selection.role = "normal_unity"
        else:
            selection.role = "other"

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
    ShowAddonPrefsOperator,
    ConfigureRenderCamera.ConfigureRenderCameraOperator,
    LocateImageMagick.LocateImageMagickOperator,
    OpenDirectory.OpenDirectoryOperator,
    ModifyRenderTargets.AddMaterialSetOperator,
    ModifyRenderTargets.RemoveMaterialSetOperator,
    ModifyRenderTargets.AddRenderTargetOperator,
    ModifyRenderTargets.RemoveRenderTargetOperator,
    RenderSpritesheet.RenderSpritesheetOperator,

    # UI property lists
    PropertyList.UI_UL_AnimationSelectionPropertyList,
    PropertyList.UI_UL_MaterialSelectionPropertyList,
    PropertyList.SPRITESHEET_UL_ObjectMaterialPairPropertyList,
    PropertyList.SPRITESHEET_UL_RenderTargetPropertyList,

    # UI panels
    BaseAddonPanel.DATA_PT_AddonPanel,
    ScenePropertiesPanel.ScenePropertiesPanel,
    RenderPropertiesPanel.RenderPropertiesPanel,
    AnimationsPanel.AnimationsPanel,
    MaterialsPanel.MaterialsPanel,
    FilePathsPanel.FilePathsPanel,
    ReportingPanel.ReportingPanel
]

timers = []

def register():
    for cls in classes:
        Register.register_class(cls)
    
    bpy.types.Scene.SpritesheetPropertyGroup = bpy.props.PointerProperty(type = SpritesheetPropertyGroup.SpritesheetPropertyGroup)
    bpy.types.Scene.ReportingPropertyGroup = bpy.props.PointerProperty(type = SpritesheetPropertyGroup.ReportingPropertyGroup)
    
    # Most handlers need to happen when the addon is enabled and also when a new .blend file is opened
    bpy.app.handlers.load_post.append(initializeCollections)
    bpy.app.handlers.load_post.append(populateAnimationSelections)
    bpy.app.handlers.load_post.append(populateMaterialSelections)
    bpy.app.handlers.load_post.append(resetReportingProps)
    
    # Since we're using curried functions here, we need to store references to them to unregister later
    startTimer(findImageMagickExe, first_interval = .1)
    startTimer(initializeCollections, make_partial = True, persistent = True)
    startTimer(populateAnimationSelections, make_partial = True, persistent = True)
    startTimer(populateMaterialSelections, make_partial = True, persistent = True)
    startTimer(resetReportingProps, make_partial = True, persistent = True)

def unregister():
    for timer in timers:
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)

    bpy.app.handlers.load_post.remove(initializeCollections)
    bpy.app.handlers.load_post.remove(populateAnimationSelections)
    bpy.app.handlers.load_post.remove(populateMaterialSelections)
    bpy.app.handlers.load_post.remove(resetReportingProps)

    del bpy.types.Scene.ReportingPropertyGroup
    del bpy.types.Scene.SpritesheetPropertyGroup
    
    UIUtil.unregisterSubPanels(MaterialSetPanel.MaterialSetPanel)

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
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
    scene = bpy.context.scene
    props = scene.SpritesheetPropertyGroup
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
    SpritesheetPropertyGroup.ReportingPropertyGroup,
    PropertyList.UI_UL_AnimationSelectionPropertyList,
    PropertyList.UI_UL_MaterialSelectionPropertyList,
    SpritesheetPropertyGroup.SpritesheetPropertyGroup,

    Prefs.SpritesheetAddonPreferences,

    # Operators
    ShowAddonPrefsOperator,
    ConfigureRenderCamera.ConfigureRenderCameraOperator,
    LocateImageMagick.LocateImageMagickOperator,
    OpenDirectory.OpenDirectoryOperator,
    RenderSpritesheet.RenderSpritesheetOperator,

    # UI
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
        # bpy.utils.register_class will call a "register" method before registration if it exists,
        # but it does some validations first that prevent use cases we need in ui.BaseAddonPanel
        preregister = getattr(cls, "preregister", None)
        if callable(preregister):
            preregister()

        bpy.utils.register_class(cls)
    
    bpy.types.Scene.SpritesheetPropertyGroup = bpy.props.PointerProperty(type = SpritesheetPropertyGroup.SpritesheetPropertyGroup)
    bpy.types.Scene.ReportingPropertyGroup = bpy.props.PointerProperty(type = SpritesheetPropertyGroup.ReportingPropertyGroup)
    
    # Most handlers need to happen when the addon is enabled and also when a new .blend file is opened
    bpy.app.handlers.load_post.append(populateAnimationSelections)
    bpy.app.handlers.load_post.append(populateMaterialSelections)
    bpy.app.handlers.load_post.append(resetReportingProps)
    
    # Since we're using curried functions here, we need to store references to them to unregister later
    bpy.app.timers.register(findImageMagickExe, first_interval = .1)
    timers.append(findImageMagickExe)

    populateAnimationSelectionsPartial = functools.partial(populateAnimationSelections, None)
    bpy.app.timers.register(populateAnimationSelectionsPartial, persistent = True)
    timers.append(populateAnimationSelectionsPartial)

    populateMaterialSelectionsPartial = functools.partial(populateMaterialSelections, None)
    bpy.app.timers.register(populateMaterialSelectionsPartial, persistent = True)
    timers.append(populateMaterialSelectionsPartial)

    resetReportingPropsPartial = functools.partial(resetReportingProps, None)
    bpy.app.timers.register(resetReportingPropsPartial, persistent = True)
    timers.append(resetReportingPropsPartial)

def unregister():
    for timer in timers:
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)

    del bpy.types.Scene.ReportingPropertyGroup
    del bpy.types.Scene.SpritesheetPropertyGroup
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
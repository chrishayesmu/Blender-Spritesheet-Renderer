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

from preferences import SpritesheetAddonPreferences as Prefs
importlib.reload(Prefs)

from property_groups import SpritesheetPropertyGroup
importlib.reload(SpritesheetPropertyGroup)

from ui import Panels
importlib.reload(Panels)
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

from custom_operators import Misc
importlib.reload(Misc)
from custom_operators import spritesheetRenderModal
importlib.reload(spritesheetRenderModal)

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
        bpy.ops.spritesheet._misc("INVOKE_DEFAULT", action = "locateImageMagick")

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
    Prefs.SpritesheetAddonPreferences,
    SpritesheetPropertyGroup.SpritesheetPropertyGroup,

    # Operators
    ShowAddonPrefsOperator,
    Misc.MiscOperator,
    spritesheetRenderModal.SpritesheetRenderModalOperator,

    # UI
    Panels.ScenePropertiesPanel,
    Panels.RenderPropertiesPanel,
    Panels.AnimationsPanel,
    Panels.MaterialsPanel,
    Panels.FilePathsPanel,
    Panels.ReportingPanel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.SpritesheetPropertyGroup = bpy.props.PointerProperty(type = SpritesheetPropertyGroup.SpritesheetPropertyGroup)
    bpy.types.Scene.ReportingPropertyGroup = bpy.props.PointerProperty(type = SpritesheetPropertyGroup.ReportingPropertyGroup)
    
    # Most handlers need to happen when the addon is enabled and also when a new .blend file is opened
    bpy.app.handlers.load_post.append(populateAnimationSelections)
    bpy.app.handlers.load_post.append(populateMaterialSelections)
    bpy.app.handlers.load_post.append(resetReportingProps)
    
    bpy.app.timers.register(findImageMagickExe, first_interval = .1)
    bpy.app.timers.register(functools.partial(populateAnimationSelections, None), persistent = True)
    bpy.app.timers.register(functools.partial(populateMaterialSelections, None), persistent = True)
    bpy.app.timers.register(functools.partial(resetReportingProps, None), first_interval = .1)



def unregister():
    if bpy.app.timers.is_registered(findImageMagickExe): bpy.app.timers.unregister(findImageMagickExe)
    if bpy.app.timers.is_registered(populateMaterialSelections): bpy.app.timers.unregister(populateMaterialSelections)
    if bpy.app.timers.is_registered(populateAnimationSelections): bpy.app.timers.unregister(populateAnimationSelections)
    if bpy.app.timers.is_registered(resetReportingProps): bpy.app.timers.unregister(resetReportingProps)
    del bpy.types.Scene.ReportingPropertyGroup
    del bpy.types.Scene.SpritesheetPropertyGroup
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
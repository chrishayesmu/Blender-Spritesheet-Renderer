import bpy
import importlib
import math
import os 
import sys

bl_info = {
    "name": "Spritesheet Renderer",
    "blender": (2, 90, 0),
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
from util import ImageMagick
importlib.reload(ImageMagick)
from util import SceneSnapshot
importlib.reload(SceneSnapshot)
from util import StringUtil
importlib.reload(StringUtil)
from util import TerminalOutput
importlib.reload(TerminalOutput)

from custom_operators import OpenDirectory
importlib.reload(OpenDirectory)
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

def populateAnimationSelections():
    scene = bpy.context.scene
    props = scene.SpritesheetPropertyGroup
    props.animationSelections.clear()
    
    for index, action in enumerate(bpy.data.actions):
        selection = props.animationSelections.add()
        selection.name = action.name
        selection.numFrames = math.ceil(action.frame_range[1]) - math.floor(action.frame_range[0])

    return 10.0

def populateMaterialSelections():
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

def resetReportingProps():
    reportingProps = bpy.context.scene.ReportingPropertyGroup

    reportingProps.currentFrameNum = 0
    reportingProps.fileExplorerType = OpenDirectory.CheckFileExplorerType()
    reportingProps.hasAnyJobStarted = False
    reportingProps.jobInProgress = False
    reportingProps.lastErrorMessage = ""
    reportingProps.totalNumFrames = 0

classes = [
    SpritesheetPropertyGroup.AnimationSelectionPropertyGroup,
    SpritesheetPropertyGroup.MaterialSelectionPropertyGroup,
    SpritesheetPropertyGroup.ReportingPropertyGroup,
    PropertyList.UI_UL_AnimationSelectionPropertyList,
    PropertyList.UI_UL_MaterialSelectionPropertyList,
    Prefs.SpritesheetAddonPreferences,
    SpritesheetPropertyGroup.SpritesheetPropertyGroup,
    ShowAddonPrefsOperator,
    OpenDirectory.OpenDirectoryOperator,
    spritesheetRenderModal.SpritesheetRenderModalOperator,
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
    bpy.app.timers.register(populateAnimationSelections, persistent = True)
    bpy.app.timers.register(populateMaterialSelections, persistent = True)
    bpy.app.timers.register(resetReportingProps, first_interval = .1)

def unregister():
    if bpy.app.timers.is_registered(populateMaterialSelections): bpy.app.timers.unregister(populateMaterialSelections)
    if bpy.app.timers.is_registered(populateAnimationSelections): bpy.app.timers.unregister(populateAnimationSelections)
    del bpy.types.Scene.ReportingPropertyGroup
    del bpy.types.Scene.SpritesheetPropertyGroup
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
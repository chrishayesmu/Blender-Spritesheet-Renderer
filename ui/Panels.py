import bpy
import math
import textwrap

from custom_operators import spritesheetRenderModal as Render
from preferences import SpritesheetAddonPreferences as Prefs
from util import FileSystemUtil
from util import StringUtil

def _wrapTextInRegion(context, text):
    width = context.region.width - 10
    wrapper = textwrap.TextWrapper(width = int(width / 7))
    return wrapper.wrap(text = text)

class AnimationsPanel(bpy.types.Panel):
    """UI Panel for animations"""
    bl_idname = "SPRITESHEET_PT_animations"
    bl_label = "Animation Data"
    bl_category = "Spritesheet"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        row = self.layout.row()
        row.prop(props, "useAnimations")

        if (props.useAnimations):
            if len(props.animationSelections) > 0:
                row = self.layout.row()
                row.prop(props, "outputFrameRate")

                self.layout.separator()
                row = self.layout.row()
                split = row.split(factor = 0.075)
                split.scale_y = 0.4
                col1, col2 = (split.column(), split.column())
                
                split = col2.split(factor = 0.75)
                col2, col3 = (split.column(), split.column())

                col1.label(text = "Use")
                col2.label(text = "Action")
                col3.label(text = "Length")
                
                row = self.layout.row()
                row.template_list("UI_UL_AnimationSelectionPropertyList", # Class name
                                "", # List ID (blank to generate)
                                props, # List items property source
                                "animationSelections", # List items property name
                                props, # List index property source
                                "activeAnimationSelectionIndex", # List index property name
                                rows = min(5, len(props.animationSelections)),
                                maxrows = 5
                )

            else:
                row = self.layout.row()
                box = row.box()
                box.label(text = "There are no animations in the file to render.", icon = "ERROR")

class FilePathsPanel(bpy.types.Panel):
    """UI Panel for file paths"""
    bl_idname = "SPRITESHEET_PT_filepaths"
    bl_label = "File Paths"
    bl_category = "Spritesheet"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        row = self.layout.row()
        row.prop(props, "separateFilesPerAnimation")

        row = self.layout.row()
        row.prop(props, "separateFilesPerRotation")

        row = self.layout.row()
        row.enabled = False
        row.prop(props, "separateFilesPerMaterial")

class MaterialsPanel(bpy.types.Panel):
    """UI Panel for materials"""
    bl_idname = "SPRITESHEET_PT_materials"
    bl_label = "Material Data"
    bl_category = "Spritesheet"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        row = self.layout.row()
        row.prop(props, "useMaterials")

        if props.useMaterials:
            if len(props.materialSelections) > 0:
                self.layout.separator()

                row = self.layout.row()
                split = row.split(factor = 0.075)
                split.scale_y = 0.4
                col1, col2 = (split.column(), split.column())
                
                split = col2.split(factor = 0.6)
                col2, col3 = (split.column(), split.column())

                col1.label(text = "Use")
                col2.label(text = "Material")
                col3.label(text = "Purpose")

                row = self.layout.row()
                row.template_list("UI_UL_MaterialSelectionPropertyList", # Class name
                                "", # List ID (blank to generate)
                                props, # List items property source
                                "materialSelections", # List items property name
                                props, # List index property source
                                "activeMaterialSelectionIndex", # List index property name
                                rows = min(5, len(props.materialSelections)),
                                maxrows = 5
                )
            else:
                row = self.layout.row()
                box = row.box()
                box.label(text = "No materials are in this scene.", icon = "ERROR")

class RenderPropertiesPanel(bpy.types.Panel):
    """UI Panel for render properties"""
    bl_idname = "SPRITESHEET_PT_renderproperties"
    bl_label = "Render Properties"
    bl_category = "Spritesheet"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        
        row = self.layout.row()
        row.prop(props, "spriteSize")

        row = self.layout.row()
        row.prop(props, "padToPowerOfTwo")

        row = self.layout.row()
        row.prop(props, "controlCamera")

        if props.controlCamera:
            row.prop(props, "cameraControlMode")

        row = self.layout.row()
        split = row.split(factor = 0.3)
        col1, col2 = (split.column(), split.column())
        col1.prop(props, "rotateObject")
        
        if props.rotateObject:
            col2.prop(props, "rotationNumber")

            split = col2.split(factor = 0.3)
            split.label(text = "Rotation Root")
            split.prop_search(props, "rotationRoot", bpy.data, "objects")

class ReportingPanel(bpy.types.Panel):
    """UI Panel for render properties"""
    bl_idname = "SPRITESHEET_PT_reporting"
    bl_label = "Job Output"
    bl_category = "Spritesheet"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw(self, context):
        reportingProps = context.scene.ReportingPropertyGroup

        row = self.layout.row()
        row.prop(reportingProps, "suppressTerminalOutput")

        if reportingProps.hasAnyJobStarted:
            if reportingProps.jobInProgress:
                row = self.layout.row()
                box = row.box()
                box.label(text = "Press ESC at any time to cancel job.", icon = "INFO")

                row = self.layout.row()
                progressPercent = math.floor(100 * reportingProps.currentFrameNum / reportingProps.totalNumFrames)
                row.label(text = "Rendering frame {} of {} ({}% complete).".format(reportingProps.currentFrameNum, reportingProps.totalNumFrames, progressPercent))

                row = self.layout.row()
                row.label(text = "Elapsed time: {}".format(StringUtil.timeAsString(reportingProps.elapsedTime)))

                row = self.layout.row()
                timeRemaining = reportingProps.estimatedTimeRemaining()
                timeRemainingStr = StringUtil.timeAsString(timeRemaining) if timeRemaining != None else "Calculating.."
                row.label(text = "Estimated time remaining: {}".format(timeRemainingStr))            
            else:
                row = self.layout.row()
                box = row.box()
                box.label(text = "No job is currently running. Showing results from the latest job.", icon = "INFO")

                row = self.layout.row()
                row.label(text = "Last job completed after {}.".format(StringUtil.timeAsString(reportingProps.elapsedTime)))

                row = self.layout.row()
                row.label(text = "A total of {} frame(s) were rendered (of an expected {}).".format(reportingProps.currentFrameNum, reportingProps.totalNumFrames))

                if not reportingProps.lastErrorMessage:
                    if FileSystemUtil.getSystemType() in ("unchecked", "unknown"):
                        # We don't know how to open the directory automatically so just show it
                        row = self.layout.row()
                        row.label(text = "Output is at {}".format(reportingProps.outputDirectory))
                    else:
                        row = self.layout.row()
                        op = row.operator("spritesheet._misc", text = "Open Last Job Output")
                        op.action = "openDir"
                        op.directory = reportingProps.outputDirectory

                # Don't show error message if a job is still running, it would be misleading
                if reportingProps.lastErrorMessage:
                    row = self.layout.row()
                    box = row.box()

                    # First column just has an error icon
                    row = box.row()
                    row.scale_y = 0.7 # shrink so lines of text appear closer together

                    col = row.column()
                    col.label(icon = "ERROR")
                    col.scale_x = .75 # adjust spacing from icon to text

                    col = row.column() # text column

                    msg = "Last job ended in error: " + reportingProps.lastErrorMessage
                    
                    wrappedMessageLines = _wrapTextInRegion(context, msg)
                    for line in wrappedMessageLines:
                        row = col.row()
                        row.label(text = line)

class ScenePropertiesPanel(bpy.types.Panel):
    """UI Panel for 2D Spritesheet Renderer"""
    bl_idname = "SPRITESHEET_PT_sceneproperties"
    bl_label = "Scene Properties"
    bl_category = "Spritesheet"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        
        row = self.layout.row()
        row.prop_search(props, "targetObject", bpy.data, "objects")

        row = self.layout.row()
        row.prop_search(props, "renderCamera", bpy.data, "objects")

        row = self.layout.row()
        row.operator("spritesheet.render", text = "Start Render")

        if Render.SpritesheetRenderModalOperator.renderDisabledReason:
            row = self.layout.row()
            box = row.box()

            # First column just has an error icon
            row = box.row()
            row.scale_y = 0.7 # shrink so lines of text appear closer together

            col = row.column()
            col.label(icon = "ERROR")
            col.scale_x = .75 # adjust spacing from icon to text

            col = row.column() # text column

            wrappedMessageLines = _wrapTextInRegion(context, Render.SpritesheetRenderModalOperator.renderDisabledReason)
            for line in wrappedMessageLines:
                row = col.row()
                row.label(text = line)

            # Hacky: check for keywords in the error string to expose some functionality
            reasonLower = Render.SpritesheetRenderModalOperator.renderDisabledReason.lower()
            if "addon preferences" in reasonLower:
                row = box.row()
                row.operator("spritesheet.showprefs", text = "Show Addon Preferences")

                # Right now the only addon preference is ImageMagick location, but let's future proof a little
                if "imagemagick" in reasonLower:
                    row = box.row()
                    row.operator("spritesheet._misc", text = "Locate Automatically").action = "locateImageMagick"
            elif "orthographic" in reasonLower:
                row = box.row()
                row.operator("spritesheet._misc", text = "Make Camera Ortho").action = "makeRenderCameraOrtho"
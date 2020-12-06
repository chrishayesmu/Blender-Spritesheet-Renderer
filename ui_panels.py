import bpy
import math
from typing import Any, Optional

import preferences

from operators.RenderSpritesheet import SPRITESHEET_OT_RenderSpritesheetOperator
from util import FileSystemUtil
from util import StringUtil
from util import UIUtil
import utils

class BaseAddonPanel:
    """Base class for all of our UI panels with some common functionality."""
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def preregister(cls):
        # pylint is having trouble telling that display_area is a getter and think it's a callable
        # pylint: disable=comparison-with-callable
        display_area: str = preferences.PrefsAccess.display_area

        # Despite reloading all the modules, somehow some of this class data is being retained between
        # disabling/re-enabling the addon, so we set everything each time to be safe
        if display_area == "render_properties":
            cls.bl_parent_id = "SPRITESHEET_PT_AddonPanel"
            cls.bl_space_type = "PROPERTIES"
            cls.bl_region_type = "WINDOW"
            cls.bl_context = "render"
            cls.bl_category = ""
        elif display_area == "view3d":
            cls.bl_space_type = "VIEW_3D"
            cls.bl_region_type = "UI"
            cls.bl_context = ""
            cls.bl_category = "Spritesheet"
            cls.bl_parent_id = ""
        else:
            raise ValueError("Unrecognized displayArea value: {}".format(display_area))

    def error_box(self, context: bpy.types.Context, layout: bpy.types.UILayout, text: str) -> bpy.types.UILayout:
        box = layout.box()
        row = box.row(align = True)
        row.label(text = "", icon = "ERROR")

        self.wrapped_label(context, row, text)

        return box

    def template_list(self, layout: bpy.types.UILayout, listtype_name: str, list_id: str, dataptr: Any, propname: str, active_dataptr: Any, active_propname: str, add_op: Optional[str] = None, remove_op: Optional[str] = None):
        list_obj = getattr(dataptr, propname)

        # Mostly passthrough but with a couple of standardized params
        layout.template_list(listtype_name, list_id, dataptr, propname, active_dataptr, active_propname, rows = min(5, max(1, len(list_obj))), maxrows = 5)

        if add_op or remove_op:
            col = layout.column(align = True)

            if add_op:
                col.operator(add_op, text = "", icon = "ADD")

            if remove_op:
                col.operator(remove_op, text = "", icon = "REMOVE")

    def wrapped_label(self, context: bpy.types.Context, layout: bpy.types.UILayout, text: str):
        lines = UIUtil.wrap_text_in_region(context, text)

        col = layout.column(align = True)
        col.scale_y = .7 # bring text lines a little closer together
        for line in lines:
            col.label(text = line)

class SPRITESHEET_PT_AddonPanel(bpy.types.Panel):
    """Parent panel that holds all other addon panels when the UI is in the Render Properties area"""
    bl_idname = "SPRITESHEET_PT_AddonPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_label = "Spritesheet Renderer"

    @classmethod
    def poll(cls, _context):
        # pylint: disable=comparison-with-callable
        return preferences.PrefsAccess.display_area == "render_properties"

    def draw(self, context):
        pass

class SPRITESHEET_PT_AnimationsPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_animations"
    bl_label = "Control Animations"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "useAnimations", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.useAnimations

        row = self.layout.row()
        row.prop(props, "outputFrameRate")

        row = self.layout.row()
        self.template_list(row,
                           "SPRITESHEET_UL_AnimationSelectionPropertyList", # Class name
                           "", # List ID (blank to generate)
                           props, # List items property source
                           "animationSelections", # List items property name
                           props, # List index property source
                           "activeAnimationSelectionIndex" # List index property name
        )

class SPRITESHEET_PT_CameraPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_camera"
    bl_label = "Control Camera"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "controlCamera", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.controlCamera

        row = self.layout.row()
        row.prop_search(props, "renderCamera", bpy.data, "cameras")

        row = self.layout.row()
        row.prop(props, "cameraControlMode")

class SPRITESHEET_PT_JobManagementPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_jobmanagement"
    bl_label = "Job Management"
    bl_options = set() # override parent's DEFAULT_CLOSED

    def draw(self, context):
        reporting_props = context.scene.ReportingPropertyGroup

        col = self.layout.column(heading = "Output Progress to", align = True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(reporting_props, "outputToTerminal")
        col.prop(reporting_props, "outputToUI")

        row = self.layout.row()
        row.operator("spritesheet.render", text = "Start Render")

        if SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason:
            self.draw_render_disabled_reason(context)

        if not reporting_props.hasAnyJobStarted:
            if reporting_props.outputToUI:
                row = self.layout.row()
                row.label(text = "Job output will be available here once a render job has started.")
        else:
            if reporting_props.jobInProgress:
                if reporting_props.outputToUI:
                    self.draw_active_job_status(reporting_props)
            else:
                row = self.layout.row()
                box = row.box()
                box.label(text = "No job is currently running. Showing results from the latest job.", icon = "INFO")

                row = self.layout.row()
                row.label(text = f"Last job completed after {StringUtil.timeAsString(reporting_props.elapsedTime)}.")

                row = self.layout.row()
                row.label(text = f"A total of {reporting_props.currentFrameNum} frame(s) were rendered (of an expected {reporting_props.totalNumFrames}).")

                if not reporting_props.lastErrorMessage:
                    if FileSystemUtil.get_system_type() in ("unchecked", "unknown"):
                        # We don't know how to open the directory automatically so just show it
                        row = self.layout.row()
                        row.label(text = f"Output is at {reporting_props.outputDirectory}")
                    else:
                        row = self.layout.row()
                        row.operator("spritesheet.open_directory", text = "Open Last Job Output").directory = reporting_props.outputDirectory

                # Don't show error message if a job is still running, it would be misleading
                if reporting_props.lastErrorMessage:
                    self.error_box(context, self.layout, f"Last job ended in error: {reporting_props.lastErrorMessage}")

    def draw_active_job_status(self, reporting_props):
        row = self.layout.row()
        box = row.box()
        box.label(text = "Press ESC at any time to cancel job.", icon = "INFO")

        row = self.layout.row()
        progress_percent = math.floor(100 * reporting_props.currentFrameNum / reporting_props.totalNumFrames)
        row.label(text = f"Rendering frame {reporting_props.currentFrameNum} of {reporting_props.totalNumFrames} ({progress_percent}% complete).")

        row = self.layout.row()
        row.label(text = f"Elapsed time: {StringUtil.timeAsString(reporting_props.elapsedTime)}")

        row = self.layout.row()
        time_remaining = reporting_props.estimatedTimeRemaining()
        time_remaining_str = StringUtil.time_as_string(time_remaining) if time_remaining is not None else "Calculating.."
        row.label(text = f"Estimated time remaining: {time_remaining_str}")

    def draw_render_disabled_reason(self, context: bpy.types.Context):
        box = self.error_box(context, self.layout, SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason)

        # Hacky: check for keywords in the error string to expose some functionality
        reason_lower = SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason.lower()
        if "addon preferences" in reason_lower:
            row = box.row()
            row.operator("spritesheet.showprefs", text = "Show Addon Preferences")

            if "imagemagick" in reason_lower:
                row = box.row()
                row.operator("spritesheet.prefs_locate_imagemagick", text = "Locate Automatically")
        elif "orthographic" in reason_lower:
            row = box.row()
            row.operator("spritesheet.configure_render_camera", text = "Make Camera Ortho")

class SPRITESHEET_PT_MaterialsPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_materials"
    bl_label = "Control Materials"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "useMaterials", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.useMaterials

        row = self.layout.row(align = True)
        row.operator("spritesheet.add_material_set", text = "Add Material Set", icon = "ADD")

class SPRITESHEET_PT_MaterialSetPanel():
    """UI Panel for material sets.

    Since this panel is shown multiple times, it is instantiated as multiple sub-types, and this specific class
    is never actually instantiated. Hence, it does not need to extend any classes like the other panels do, since
    those will be mixed in at runtime."""

    bl_label = "" # hidden; see draw_header
    bl_parent_id = "SPRITESHEET_PT_materials"

    index = 0

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup

        return cls.index < len(props.materialSets)

    @classmethod
    def create_sub_panel(cls, index):
        UIUtil.create_panel_type(cls, index)

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup
        material_set = props.materialSets[self.index]

        set_display_name: str = material_set.name if material_set.name else utils.enum_display_name_from_identifier(material_set, "role", material_set.role)

        split = self.layout.split()

        col = split.column()
        col.alignment = "LEFT"
        col.label(text = f"Material Set {self.index + 1}", icon = "MATERIAL")

        col = split.column()
        col.alignment = "RIGHT"
        col.label(text = set_display_name)

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        material_set = props.materialSets[self.index]

        self.layout.active = props.useMaterials

        row = self.layout.row()
        row.operator("spritesheet.remove_material_set", text = "Remove Set", icon = "REMOVE").index = self.index

        row = self.layout.row()
        row.prop(material_set, "name")

        row = self.layout.row()
        row.prop(material_set, "role")

        row = self.layout.row()
        self.template_list(row,
                           "SPRITESHEET_UL_ObjectMaterialPairPropertyList", # Class name
                           "", # List ID (blank to generate)
                           material_set, # List items property source
                           "objectMaterialPairs", # List items property name
                           material_set, # List index property source
                           "selectedObjectMaterialPair", # List index property name
        )

class SPRITESHEET_PT_OutputPropertiesPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_outputproperties"
    bl_label = "Output Properties"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        self.layout.prop(props, "spriteSize")

        row = self.layout.row(heading = "Output Size")
        row.prop(props, "padToPowerOfTwo")

        self.layout.separator()

        col = self.layout.column(heading = "Separate Files by", align = True)

        subcol = col.column()
        subcol.enabled = props.useAnimations
        subcol.prop(props, "separateFilesPerAnimation", text = "Animation")

        subcol = col.column()
        subcol.enabled = props.rotateObject
        subcol.prop(props, "separateFilesPerRotation", text = "Rotation")

        # Files are always separated by material set; this can't be changed
        subcol = col.column()
        subcol.enabled = False
        subcol.prop(props, "separateFilesPerMaterial", text = "Material Set")

class SPRITESHEET_PT_RotationOptionsPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_rotationoptions"
    bl_label = "Control Rotation"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "rotateObject", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.rotateObject

        row = self.layout.row()
        row.prop(props, "rotationNumber")

        if 360 % props.rotationNumber != 0:
            self.error_box(context, self.layout, "Chosen number of angles does not smoothly divide into 360 degrees (integer math only). Rotations may be slightly different from your expectations.")

        row = self.layout.row()
        self.template_list(row,
                    "SPRITESHEET_UL_RotationRootPropertyList", # Class name
                    "spritesheet_RotationOptionsPanel_rotation_root_list", # List ID (blank to generate)
                    props, # List items property source
                    "targetObjects", # List items property name
                    props, # List index property source
                    "selectedRotationRootIndex", # List index property name
        )

class SPRITESHEET_PT_TargetObjectsPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_targetobjects"
    bl_label = "Target Objects"
    bl_options = set() # override parent's DEFAULT_CLOSED

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        row = self.layout.row()
        self.template_list(row,
                           "SPRITESHEET_UL_RenderTargetPropertyList", # Class name
                           "spritesheet_TargetObjectsPanel_target_objects_list", # List ID (blank to generate)
                           props, # List items property source
                           "targetObjects", # List items property name
                           props, # List index property source
                           "selectedTargetObjectIndex", # List index property name,
                           add_op = "spritesheet.add_render_target",
                           remove_op = "spritesheet.remove_render_target"
        )
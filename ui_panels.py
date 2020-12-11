import bpy
import math
from typing import Any, Optional

import preferences

from render_operator import SPRITESHEET_OT_RenderSpritesheetOperator
from util import FileSystemUtil
from util import StringUtil
from util import UIUtil

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

    def message_box(self, context: bpy.types.Context, layout: bpy.types.UILayout, text: str, icon: str = "NONE") -> bpy.types.UILayout:
        box = layout.box()
        sub = box

        if icon:
            row = box.row(align = True)
            row.label(text = "", icon = icon)
            sub = row

        self.wrapped_label(context, sub, text)

        return box

    def template_list(self, layout: bpy.types.UILayout, listtype_name: str, list_id: str, dataptr: Any, propname: str, active_dataptr: Any, active_propname: str, min_rows: int = 1,
                      add_op: Optional[str] = None, remove_op: Optional[str] = None, reorder_up_op: Optional[str] = None, reorder_down_op: Optional[str] = None):
        list_obj = getattr(dataptr, propname)

        row = layout.row()

        # Mostly passthrough but with a couple of standardized params
        row.template_list(listtype_name, list_id, dataptr, propname, active_dataptr, active_propname, rows = min(5, max(min_rows, len(list_obj))), maxrows = 5)

        if add_op or remove_op or reorder_up_op or reorder_down_op:
            col = row.column(align = True)

            if add_op:
                col.operator(add_op, text = "", icon = "ADD")

            if remove_op:
                col.operator(remove_op, text = "", icon = "REMOVE")

            col.separator()

            if reorder_up_op:
                col.operator(reorder_up_op, text = "", icon = "TRIA_UP")

            if reorder_down_op:
                col.operator(reorder_down_op, text = "", icon = "TRIA_DOWN")

    def wrapped_label(self, context: bpy.types.Context, layout: bpy.types.UILayout, text: str, icon: str = ""):
        lines = UIUtil.wrap_text_in_region(context, text)

        if icon and len(lines) > 1:
            pass

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

        self.layout.prop(props, "control_animations", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.control_animations
        self.layout.operator("spritesheet.add_animation_set", text = "Add Animation Set", icon = "ADD")

class SPRITESHEET_PT_AnimationSetPanel():
    # See SPRITESHEET_PT_MaterialSetPanel for why this has no parent types
    bl_label = "" # hidden; see draw_header
    bl_parent_id = "SPRITESHEET_PT_animations"

    index = 0

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup

        return cls.index < len(props.animation_sets)

    @classmethod
    def create_sub_panel(cls, index):
        UIUtil.create_panel_type(cls, index)

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup
        animation_set = props.animation_sets[self.index]

        num_frames = 0
        selected_actions = animation_set.get_selected_actions()
        if len(selected_actions) > 0:
            num_frames = max([a.num_frames for a in selected_actions])

        self.layout.enabled = props.control_animations
        self.layout.use_property_split = True
        self.layout.prop(animation_set, "name", text = f"Animation Set {self.index + 1}")

        if num_frames > 0:
            self.layout.label(text = f"{num_frames} frames")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        animation_set = props.animation_sets[self.index]

        self.layout.enabled = props.control_animations
        self.layout.operator("spritesheet.remove_animation_set", text = "Remove Set", icon = "REMOVE").index = self.index

        self.template_list(self.layout,
                            "SPRITESHEET_UL_AnimationActionPropertyList", # Class name
                            "", # List ID (blank to generate)
                            animation_set, # List items property source
                            "actions", # List items property name
                            animation_set, # List index property source
                            "selected_action_index", # List index property name
        )

        # Show a warning if there are actions with different frame ranges
        set_frame_data = animation_set.get_frame_data()

        if set_frame_data is not None and any(action.get_frame_data() != set_frame_data for action in animation_set.get_selected_actions()):
            self.message_box(context,
                                self.layout,
                                f"Not all selected actions have the same range of frames. This animation set will play over the superset of frames for all actions ({set_frame_data.frame_min} to {set_frame_data.frame_max}).",
                                "INFO"
            )

        # TODO add a preview button

class SPRITESHEET_PT_CameraPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_camera"
    bl_label = "Control Camera"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "control_camera", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.control_camera
        self.layout.prop_search(props, "render_camera", bpy.data, "cameras")
        self.layout.prop(props, "camera_control_mode")

class SPRITESHEET_PT_JobManagementPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_jobmanagement"
    bl_label = "Job Management"
    bl_options = set() # override parent's DEFAULT_CLOSED

    def draw(self, context):
        reporting_props = context.scene.ReportingPropertyGroup

        row = self.layout.row(heading = "Output Progress to", align = True)
        row.alignment = "LEFT"
        row.prop(reporting_props, "output_to_panel")
        row.prop(reporting_props, "output_to_terminal")

        self.layout.operator("spritesheet.render", text = "Start Render")

        if SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason:
            self.draw_render_disabled_reason(context)

        if not reporting_props.has_any_job_started:
            if reporting_props.output_to_panel:
                self.layout.label(text = "Job output will be available here once a render job has started.")
        else:
            if reporting_props.job_in_progress:
                if reporting_props.output_to_panel:
                    self.draw_active_job_status(reporting_props)
            else:
                self.message_box(context, self.layout, "No job is currently running. Showing results from the latest job.", icon = "INFO")
                self.wrapped_label(context, self.layout, f"Last job completed after {StringUtil.time_as_string(reporting_props.elapsed_time)}. A total of {reporting_props.current_frame_num} frame(s) were rendered.")

                if not reporting_props.last_error_message:
                    if FileSystemUtil.get_system_type() in ("unchecked", "unknown"):
                        # We don't know how to open the directory automatically so just show it
                        self.layout.label(text = f"Output is at {reporting_props.output_directory}")
                    else:
                        self.layout.operator("spritesheet.open_directory", text = "Open Last Job Output").directory = reporting_props.output_directory

                # Don't show error message if a job is still running, it would be misleading
                if reporting_props.last_error_message:
                    self.message_box(context, self.layout, f"Last job ended in error: {reporting_props.last_error_message}", icon = "ERROR")

    def draw_active_job_status(self, reporting_props):
        progress_percent = math.floor(100 * reporting_props.current_frame_num / reporting_props.total_num_frames)
        time_remaining = reporting_props.estimated_time_remaining
        time_remaining_str = StringUtil.time_as_string(time_remaining) if time_remaining is not None else "Calculating.."

        box = self.layout.box()
        box.label(text = "Press ESC at any time to cancel job.", icon = "INFO")

        self.layout.label(text = f"Rendering frame {reporting_props.current_frame_num} of {reporting_props.total_num_frames} ({progress_percent}% complete).")
        self.layout.label(text = f"Elapsed time: {StringUtil.time_as_string(reporting_props.elapsed_time)}")
        self.layout.label(text = f"Estimated time remaining: {time_remaining_str}")

    def draw_render_disabled_reason(self, context: bpy.types.Context):
        props = context.scene.SpritesheetPropertyGroup

        box = self.message_box(context, self.layout, SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason, icon = "ERROR")

        # Hacky: check for keywords in the error string to expose some functionality
        reason_lower = SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason.lower()
        if "addon preferences" in reason_lower:
            box.operator("spritesheet.showprefs", text = "Show Addon Preferences")

            if "imagemagick" in reason_lower:
                box.operator("spritesheet.prefs_locate_imagemagick", text = "Locate Automatically")
        elif "orthographic" in reason_lower:
            box.operator("spritesheet.configure_render_camera", text = f"Make Camera \"{props.render_camera.name}\" Ortho")

class SPRITESHEET_PT_MaterialsPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_materials"
    bl_label = "Control Materials"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "control_materials", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.control_materials
        self.layout.operator("spritesheet.add_material_set", text = "Add Material Set", icon = "ADD")

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

        return cls.index < len(props.material_sets)

    @classmethod
    def create_sub_panel(cls, index):
        UIUtil.create_panel_type(cls, index)

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup
        material_set = props.material_sets[self.index]

        self.layout.enabled = props.control_materials
        self.layout.use_property_split = True
        self.layout.prop(material_set, "name", text = f"Material Set {self.index + 1}")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        material_set = props.material_sets[self.index]

        self.layout.enabled = props.control_materials
        # TODO add a preview button

        self.layout.operator("spritesheet.remove_material_set", text = "Remove Set", icon = "REMOVE").index = self.index
        self.layout.prop(material_set, "role")
        self.layout.prop(material_set, "mode")

        if material_set.mode == "shared":
            self.layout.prop(material_set, "shared_material")
        elif material_set.mode == "individual":
            self.template_list(self.layout,
                               "SPRITESHEET_UL_RenderTargetMaterialPropertyList", # Class name
                               "", # List ID (blank to generate)
                               material_set, # List items property source
                               "materials", # List items property name
                               material_set, # List index property source
                               "selected_material_index", # List index property name
            )

class SPRITESHEET_PT_OutputPropertiesPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_outputproperties"
    bl_label = "Output Properties"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        self.layout.prop(props, "sprite_size")

        row = self.layout.row(heading = "Output Size")
        row.prop(props, "pad_output_to_power_of_two")

        self.layout.separator()

        col = self.layout.column(heading = "Separate Files by", align = True)

        sub = col.row()
        sub.enabled = props.control_animations
        sub.prop(props, "separate_files_per_animation", text = "Animation Set")

        sub = col.row()
        sub.enabled = props.control_rotation
        sub.prop(props, "separate_files_per_rotation", text = "Rotation")

        # Files are always separated by material set; this can't be changed
        sub = col.row()
        sub.enabled = False
        sub.prop(props, "separate_files_per_material", text = "Material Set")

class SPRITESHEET_PT_RotationOptionsPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_rotationoptions"
    bl_label = "Control Rotation"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "control_rotation", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.control_rotation
        self.layout.prop(props, "num_rotations")

        if 360 % props.num_rotations != 0:
            self.message_box(context, self.layout, "Chosen number of angles does not smoothly divide into 360 degrees (integer math only). Rotations may be slightly different from your expectations.", icon = "ERROR")

        self.template_list(self.layout,
                    "SPRITESHEET_UL_RotationRootPropertyList", # Class name
                    "spritesheet_RotationOptionsPanel_rotation_root_list", # List ID (blank to generate)
                    props, # List items property source
                    "render_targets", # List items property name
                    props, # List index property source
                    "selected_rotation_root_index", # List index property name
        )

class SPRITESHEET_PT_RenderTargetsPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_rendertargets"
    bl_label = "Render Targets"
    bl_options = set() # override parent's DEFAULT_CLOSED

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.template_list(self.layout,
                           "SPRITESHEET_UL_RenderTargetPropertyList", # Class name
                           "spritesheet_RenderTargetsPanel_target_objects_list", # List ID (blank to generate)
                           props, # List items property source
                           "render_targets", # List items property name
                           props, # List index property source
                           "selected_render_target_index", # List index property name,
                           min_rows = 4,
                           add_op = "spritesheet.add_render_target",
                           remove_op = "spritesheet.remove_render_target",
                           reorder_up_op = "spritesheet.move_render_target_up",
                           reorder_down_op = "spritesheet.move_render_target_down"
        )
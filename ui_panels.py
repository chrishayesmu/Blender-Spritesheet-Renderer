import bpy
from copy import deepcopy
import math
from typing import Any, Dict, List, Optional, Tuple, Union

import preferences

from render_operator import SPRITESHEET_OT_RenderSpritesheetOperator
from util import FileSystemUtil, StringUtil, UIUtil

# TODO: it would be nice to update one of these panels to show a preview of how many
# sprites will be rendered into how many files, based on the current configuration

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

    def template_list(self, context: bpy.types.Context, layout: bpy.types.UILayout, listtype_name: str, list_id: str, dataptr: Any, propname: str, active_dataptr: Any, active_propname: str, item_dyntip_propname: str = "",
                      min_rows: int = 1, header_labels: List[str] = None,
                      add_op: Optional[Union[str, Tuple[str, Dict[str, Any]]]] = None,
                      remove_op: Optional[Union[str, Tuple[str, Dict[str, Any]]]] = None,
                      reorder_up_op: Optional[Union[str, Tuple[str, Dict[str, Any]]]] = None,
                      reorder_down_op: Optional[Union[str, Tuple[str, Dict[str, Any]]]] = None):
        """Helper method for standardizing the appearance of lists within the addon, as well as being able to add some controls along the right side.

        Most arguments match their equivalent in bpy.types.UILayout.template_list. Operator arguments can be either the argument name by itself, or the name
        plus a dictionary of key-value pairs to pass to the operator.
        """

        list_obj = getattr(dataptr, propname)
        show_header_row = header_labels and len(header_labels) > 0
        header_row_scale = 0.5

        row = layout.row()
        list_col = row.column()

        # Header row above the list: these settings make them roughly aligned with the columns in the list
        if show_header_row:
            sub = list_col.row()

            for label in header_labels:
                text: str

                if isinstance(label, str):
                    text = label
                elif isinstance(label, tuple):
                    if len(label) == 2:
                        text, split_factor = label
                        sub = sub.split(factor = split_factor)
                    else:
                        raise ValueError(f"Don't know how to process header label {label}")
                else:
                    raise ValueError(f"Don't know how to process header label {label}")

                col = sub.column()
                UIUtil.wrapped_label(context, col, text)

        # Mostly passthrough but with a couple of standardized params
        list_col.template_list(listtype_name, list_id, dataptr, propname, active_dataptr, active_propname, item_dyntip_propname = item_dyntip_propname, rows = min(5, max(min_rows, len(list_obj))), maxrows = 5)

        if add_op or remove_op or reorder_up_op or reorder_down_op:
            button_col = row.column(align = True)

            if show_header_row:
                row = button_col.row()
                row.scale_y = header_row_scale + 0.1
                row.alignment = "CENTER"
                row.label(text = "")

            if add_op:
                self._emit_operator(button_col, add_op, "ADD")

            if remove_op:
                self._emit_operator(button_col, remove_op, "REMOVE")

            button_col.separator()

            if reorder_up_op:
                self._emit_operator(button_col, reorder_up_op, "TRIA_UP")

            if reorder_down_op:
                self._emit_operator(button_col, reorder_down_op, "TRIA_DOWN")

        return list_col

    def _emit_operator(self, layout: bpy.types.UILayout, op: Optional[Union[str, Tuple[str, Dict[str,  Any]]]], icon: str):
        if isinstance(op, str):
            layout.operator(op, text = "", icon = icon)
        else:
            op_name = op[0]
            op_args = op[1]

            op_instance = layout.operator(op_name, text = "", icon = icon)

            for key, value in op_args.items():
                setattr(op_instance, key, value)

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

        self.layout.prop(props.animation_options, "control_animations", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.animation_options.control_animations
        self.layout.operator("spritesheet.add_animation_set", text = "Add Animation Set", icon = "ADD")

class SPRITESHEET_PT_AnimationSetPanel():
    # See SPRITESHEET_PT_MaterialSetPanel for why this has no parent types
    bl_label = "" # hidden; see draw_header
    bl_parent_id = "SPRITESHEET_PT_animations"

    index = 0

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup

        return cls.index < len(props.animation_options.animation_sets)

    @classmethod
    def create_sub_panel(cls, index):
        UIUtil.create_panel_type(cls, index)

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup
        animation_set = props.animation_options.animation_sets[self.index]
        frame_data = animation_set.get_frame_data()

        self.layout.enabled = props.animation_options.control_animations
        self.layout.use_property_split = True
        self.layout.prop(animation_set, "name", text = f"Animation Set {self.index + 1}")

        if frame_data:
            sub = self.layout.column()
            sub.alignment = "RIGHT"
            sub.label(text = f"{frame_data.num_frames} frames at {animation_set.output_frame_rate} fps")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        animation_set = props.animation_options.animation_sets[self.index]

        add_op = ("spritesheet.modify_animation_set", {
            "animation_set_index": self.index,
            "operation": "add_action"
        })

        remove_op = ("spritesheet.modify_animation_set", {
            "action_index": animation_set.selected_action_index,
            "animation_set_index": self.index,
            "operation": "remove_action"
        })

        move_up_op = deepcopy(remove_op)
        move_up_op[1]["operation"] = "move_action_up"

        move_down_op = deepcopy(remove_op)
        move_down_op[1]["operation"] = "move_action_down"

        self.layout.enabled = props.animation_options.control_animations

        row = self.layout.row(align = True)
        row.operator("spritesheet.remove_animation_set", text = "Remove Set", icon = "REMOVE").index = self.index

        if context.screen.is_animation_playing and animation_set.is_previewing:
            row.operator("screen.animation_cancel", text = "Pause Playback", icon = "PAUSE").restore_frame = False
        else:
            row.operator("spritesheet.play_animation_set", text = "Play in Viewport", icon = "PLAY").index = self.index

        self.layout.separator()
        self.layout.prop(animation_set, "output_frame_rate")

        self.layout.separator()

        list_col = self.template_list(context,
                                      self.layout,
                                      "SPRITESHEET_UL_AnimationActionPropertyList", # Class name
                                      "", # List ID (blank to generate)
                                      animation_set, # List items property source
                                      "actions", # List items property name
                                      animation_set, # List index property source
                                      "selected_action_index", # List index property name
                                      min_rows = 4,
                                      header_labels = [ " Target", ("Action", 0.685), "Frame Range"],
                                      add_op = add_op,
                                      remove_op = remove_op,
                                      reorder_up_op = move_up_op,
                                      reorder_down_op = move_down_op
        )

        prop = animation_set.actions[animation_set.selected_action_index]

        list_col.separator()
        list_col.prop_search(prop, "target", bpy.data, "objects", text = "Target Object", icon = "OBJECT_DATA")
        list_col.prop_search(prop, "action", bpy.data, "actions", text = "Action", icon = "ACTION")

        # Show a warning if there are actions with different frame ranges
        set_frame_data = animation_set.get_frame_data()

        if set_frame_data is not None and any(action.get_frame_data() != set_frame_data for action in animation_set.get_selected_actions()):
            UIUtil.message_box(context,
                               self.layout,
                               f"Not all selected actions have the same range of frames. This animation set will play over the superset of frames for all actions ({set_frame_data.frame_min} to {set_frame_data.frame_max}).",
                               "INFO"
            )

class SPRITESHEET_PT_CameraPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_camera"
    bl_label = "Control Camera"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props.camera_options, "control_camera", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.operator("spritesheet.optimize_camera", text = "Set Camera in Viewport", icon = 'HIDE_OFF')

        self.layout.active = props.camera_options.control_camera
        self.layout.prop_search(props.camera_options, "render_camera", bpy.data, "cameras")
        self.layout.prop(props.camera_options, "camera_control_mode")

        self.layout.separator()

        add_op = "spritesheet.add_camera_target"

        remove_op = ("spritesheet.remove_camera_target", {
            "index": props.camera_options.selected_target_index
        })

        move_up_op = ("spritesheet.move_camera_target_up", {
            "index": props.camera_options.selected_target_index
        })

        move_down_op = ("spritesheet.move_camera_target_down", {
            "index": props.camera_options.selected_target_index
        })

        self.template_list(context,
                           self.layout,
                           "SPRITESHEET_UL_CameraTargetPropertyList", # Class name
                           "spritesheet_CameraOptionsPanel_camera_target_list", # List ID (blank to generate)
                           props.camera_options, # List items property source
                           "targets", # List items property name
                           props.camera_options, # List index property source
                           "selected_target_index", # List index property name,
                           min_rows = 4,
                           header_labels = ["Each object selected here (and their children) will be framed by the camera."],
                           add_op = add_op,
                           remove_op = remove_op,
                           reorder_up_op = move_up_op,
                           reorder_down_op = move_down_op
        )

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
                UIUtil.message_box(context, self.layout, "No job is currently running. Showing results from the latest job.", icon = "INFO")
                UIUtil.wrapped_label(context, self.layout, f"Last job completed after {StringUtil.time_as_string(reporting_props.elapsed_time)}. A total of {reporting_props.current_frame_num} frame(s) were rendered.")

                if not reporting_props.last_error_message:
                    if FileSystemUtil.get_system_type() in ("unchecked", "unknown"):
                        # We don't know how to open the directory automatically so just show it
                        self.layout.label(text = f"Output is at {reporting_props.output_directory}")
                    else:
                        self.layout.operator("spritesheet.open_directory", text = "Open Last Job Output").directory = reporting_props.output_directory

                # Don't show error message if a job is still running, it would be misleading
                if reporting_props.last_error_message:
                    UIUtil.message_box(context, self.layout, f"Last job ended in error: {reporting_props.last_error_message}", icon = "ERROR")

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

        box = UIUtil.message_box(context, self.layout, SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason, icon = "ERROR")

        # Hacky: check for keywords in the error string to expose some functionality
        reason_lower = SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason.lower()
        if "addon preferences" in reason_lower:
            box.operator("spritesheet.showprefs", text = "Show Addon Preferences")

            if "imagemagick" in reason_lower:
                box.operator("spritesheet.prefs_locate_imagemagick", text = "Locate Automatically")
        elif "orthographic" in reason_lower:
            box.operator("spritesheet.configure_render_camera", text = f"Make Camera \"{props.camera_options.render_camera.name}\" Ortho")

class SPRITESHEET_PT_MaterialsPanel(BaseAddonPanel, bpy.types.Panel):
    bl_idname = "SPRITESHEET_PT_materials"
    bl_label = "Control Materials"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props.material_options, "control_materials", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.material_options.control_materials
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

        return cls.index < len(props.material_options.material_sets)

    @classmethod
    def create_sub_panel(cls, index):
        UIUtil.create_panel_type(cls, index)

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup
        material_set = props.material_options.material_sets[self.index]

        self.layout.enabled = props.material_options.control_materials
        self.layout.use_property_split = True
        self.layout.prop(material_set, "name", text = f"Material Set {self.index + 1}")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        material_set = props.material_options.material_sets[self.index]

        self.layout.enabled = props.material_options.control_materials

        row = self.layout.row(align = True)
        row.operator("spritesheet.remove_material_set", text = "Remove Set", icon = "REMOVE").index = self.index
        row.operator("spritesheet.assign_material_set", text = "Assign in Scene", icon = "HIDE_OFF").index = self.index

        self.layout.prop(material_set, "role")
        self.layout.prop(material_set, "mode")

        if material_set.mode == "shared":
            self.layout.prop(material_set, "shared_material")

        add_op = ("spritesheet.modify_material_set", {
            "material_set_index": self.index,
            "operation": "add_target"
        })

        remove_op = ("spritesheet.modify_material_set", {
            "target_index": material_set.selected_material_index,
            "material_set_index": self.index,
            "operation": "remove_target"
        })

        move_up_op = deepcopy(remove_op)
        move_up_op[1]["operation"] = "move_target_up"

        move_down_op = deepcopy(remove_op)
        move_down_op[1]["operation"] = "move_target_down"

        self.layout.separator()

        # TODO add dynamic tooltip to this and other lists
        list_col = self.template_list(context,
                                      self.layout,
                                      "SPRITESHEET_UL_MaterialSetTargetPropertyList", # Class name
                                      "", # List ID (blank to generate)
                                      material_set, # List items property source
                                      "materials", # List items property name
                                      material_set, # List index property source
                                      "selected_material_index", # List index property name
                                      min_rows = 4,
                                      header_labels = ["Target", "Material"],
                                      add_op = add_op,
                                      remove_op = remove_op,
                                      reorder_up_op = move_up_op,
                                      reorder_down_op = move_down_op
        )

        prop = material_set.materials[material_set.selected_material_index]

        list_col.separator()
        list_col.prop_search(prop, "target", bpy.data, "objects", text = "Target Object", icon = "OBJECT_DATA")

        if material_set.mode == "individual":
            list_col.prop_search(prop, "material", bpy.data, "materials", text = "Material", icon = "MATERIAL")

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
        sub.enabled = props.animation_options.control_animations
        sub.prop(props, "separate_files_per_animation", text = "Animation Set")

        sub = col.row()
        sub.enabled = props.rotation_options.control_rotation
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

        self.layout.prop(props.rotation_options, "control_rotation", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        add_op = "spritesheet.add_rotation_target"

        remove_op = ("spritesheet.remove_rotation_target", {
            "index": props.rotation_options.selected_target_index
        })

        move_up_op = ("spritesheet.move_rotation_target_up", {
            "index": props.rotation_options.selected_target_index
        })

        move_down_op = ("spritesheet.move_rotation_target_down", {
            "index": props.rotation_options.selected_target_index
        })

        self.layout.active = props.rotation_options.control_rotation
        self.layout.prop(props.rotation_options, "num_rotations")

        if 360 % props.rotation_options.num_rotations != 0:
            UIUtil.message_box(context, self.layout, "Chosen number of angles does not smoothly divide into 360 degrees (integer math only). Rotations may be slightly different from your expectations.", icon = "ERROR")

        self.layout.separator()

        self.template_list(context,
                           self.layout,
                           "SPRITESHEET_UL_RotationTargetPropertyList", # Class name
                           "spritesheet_RotationOptionsPanel_rotation_root_list", # List ID (blank to generate)
                           props.rotation_options, # List items property source
                           "targets", # List items property name
                           props.rotation_options, # List index property source
                           "selected_target_index", # List index property name,
                           min_rows = 4,
                           header_labels = ["Each object selected here will be rotated during rendering."],
                           add_op = add_op,
                           remove_op = remove_op,
                           reorder_up_op = move_up_op,
                           reorder_down_op = move_down_op
        )
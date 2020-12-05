import bpy
import math

from operators.RenderSpritesheet import SPRITESHEET_OT_RenderSpritesheetOperator
from util import FileSystemUtil
from util import StringUtil
from util import UIUtil
from ui.BaseAddonPanel import BaseAddonPanel

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
                    self.draw_last_job_error_message(context)

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

    def draw_last_job_error_message(self, context):
        reporting_props = context.scene.ReportingPropertyGroup

        row = self.layout.row()
        box = row.box()

        # First column just has an error icon
        row = box.row()
        row.scale_y = 0.7 # shrink so lines of text appear closer together

        col = row.column()
        col.label(icon = "ERROR")
        col.scale_x = .75 # adjust spacing from icon to text

        col = row.column() # text column

        msg = "Last job ended in error: " + reporting_props.lastErrorMessage

        wrapped_message_lines = UIUtil.wrap_text_in_region(context, msg)
        for line in wrapped_message_lines:
            row = col.row()
            row.label(text = line)

    def draw_render_disabled_reason(self, context):
        row = self.layout.row()
        box = row.box()

        # First column just has an error icon
        row = box.row()
        row.scale_y = 0.7 # shrink so lines of text appear closer together

        col = row.column()
        col.label(icon = "ERROR")
        col.scale_x = .75 # adjust spacing from icon to text

        col = row.column() # text column

        wrapped_message_lines = UIUtil.wrap_text_in_region(context, SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason)
        for line in wrapped_message_lines:
            row = col.row()
            row.label(text = line)

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
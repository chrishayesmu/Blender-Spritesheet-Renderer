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
        reportingProps = context.scene.ReportingPropertyGroup

        col = self.layout.column(heading = "Output Progress to", align = True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(reportingProps, "outputToTerminal")
        col.prop(reportingProps, "outputToUI")

        row = self.layout.row()
        row.operator("spritesheet.render", text = "Start Render")

        if SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason:
            self.draw_render_disabled_reason(context)

        if not reportingProps.hasAnyJobStarted:
            if reportingProps.outputToUI:
                row = self.layout.row()
                row.label(text = "Job output will be available here once a render job has started.")
        else:
            if reportingProps.jobInProgress:
                if reportingProps.outputToUI:
                    self.draw_active_job_status(reportingProps)
            else:
                row = self.layout.row()
                box = row.box()
                box.label(text = "No job is currently running. Showing results from the latest job.", icon = "INFO")

                row = self.layout.row()
                row.label(text = f"Last job completed after {StringUtil.timeAsString(reportingProps.elapsedTime)}.")

                row = self.layout.row()
                row.label(text = f"A total of {reportingProps.currentFrameNum} frame(s) were rendered (of an expected {reportingProps.totalNumFrames}).")

                if not reportingProps.lastErrorMessage:
                    if FileSystemUtil.getSystemType() in ("unchecked", "unknown"):
                        # We don't know how to open the directory automatically so just show it
                        row = self.layout.row()
                        row.label(text = f"Output is at {reportingProps.outputDirectory}")
                    else:
                        row = self.layout.row()
                        row.operator("spritesheet.open_directory", text = "Open Last Job Output").directory = reportingProps.outputDirectory

                # Don't show error message if a job is still running, it would be misleading
                if reportingProps.lastErrorMessage:
                    self.draw_last_job_error_message(context)

    def draw_active_job_status(self, reportingProps):
        row = self.layout.row()
        box = row.box()
        box.label(text = "Press ESC at any time to cancel job.", icon = "INFO")

        row = self.layout.row()
        progressPercent = math.floor(100 * reportingProps.currentFrameNum / reportingProps.totalNumFrames)
        row.label(text = f"Rendering frame {reportingProps.currentFrameNum} of {reportingProps.totalNumFrames} ({progressPercent}% complete).")

        row = self.layout.row()
        row.label(text = f"Elapsed time: {StringUtil.timeAsString(reportingProps.elapsedTime)}")

        row = self.layout.row()
        timeRemaining = reportingProps.estimatedTimeRemaining()
        timeRemainingStr = StringUtil.timeAsString(timeRemaining) if timeRemaining != None else "Calculating.."
        row.label(text = f"Estimated time remaining: {timeRemainingStr}")

    def draw_last_job_error_message(self, context):
        reportingProps = context.scene.ReportingPropertyGroup

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
        
        wrappedMessageLines = UIUtil.wrapTextInRegion(context, msg)
        for line in wrappedMessageLines:
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

        wrappedMessageLines = UIUtil.wrapTextInRegion(context, SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason)
        for line in wrappedMessageLines:
            row = col.row()
            row.label(text = line)

        # Hacky: check for keywords in the error string to expose some functionality
        reasonLower = SPRITESHEET_OT_RenderSpritesheetOperator.renderDisabledReason.lower()
        if "addon preferences" in reasonLower:
            row = box.row()
            row.operator("spritesheet.showprefs", text = "Show Addon Preferences")

            if "imagemagick" in reasonLower:
                row = box.row()
                row.operator("spritesheet.prefs_locate_imagemagick", text = "Locate Automatically")
        elif "orthographic" in reasonLower:
            row = box.row()
            row.operator("spritesheet.configure_render_camera", text = "Make Camera Ortho")
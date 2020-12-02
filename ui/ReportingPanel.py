import bpy
import math

from util import FileSystemUtil
from util import StringUtil
from util import UIUtil
from ui.BaseAddonPanel import BaseAddonPanel

class ReportingPanel(BaseAddonPanel, bpy.types.Panel):
    """UI Panel for render properties"""
    bl_idname = "SPRITESHEET_PT_reporting"
    bl_label = "Job Output"

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
                    
                    wrappedMessageLines = UIUtil.wrapTextInRegion(context, msg)
                    for line in wrappedMessageLines:
                        row = col.row()
                        row.label(text = line)

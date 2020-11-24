import bpy
import json
import math
import os
import pathlib
import sys
import tempfile
import time

from preferences import SpritesheetAddonPreferences as Prefs
from util import Camera as CameraUtil
from util import ImageMagick
from util.TerminalOutput import TerminalWriter
from util.SceneSnapshot import SceneSnapshot
from util import StringUtil

class SpritesheetRenderModalOperator(bpy.types.Operator):
    """Operator for executing spritesheet rendering"""
    bl_idname = "spritesheet.render"
    bl_label = "Render Spritesheet"
    bl_description = "Render target object according to the input settings"

    renderDisabledReason = ""

    @classmethod
    def poll(cls, context):
        # For some reason, if an error occurs in this method, Blender won't report it.
        # So the whole thing is wrapped in a try/except block so we can know what happened.
        try:
            scene = context.scene
            props = scene.SpritesheetPropertyGroup
            enabledActionSelections = [a for a in props.animationSelections if a.isSelectedForExport]
            enabledMaterialSelections = [ms for ms in props.materialSelections if ms.isSelectedForExport]

            reason = ""

            if not props.targetObject:
                reason = "Target Object is not set."
            elif props.useAnimations and not props.targetObject.animation_data:
                reason = "'Animate During Render' is enabled, but Target Object has no animation data."
            elif props.useAnimations and len(enabledActionSelections) == 0:
                reason = "'Animate During Render' is enabled, but no materials have been selected for use."
            elif props.separateFilesPerAnimation and not props.useAnimations:
                reason = "'Separate Files Per Animation' is enabled, but 'Animate During Render' is not."
            elif props.useMaterials and len(props.targetObject.data.materials) != 1:
                reason = "If 'Render Multiple Materials' is enabled, Target Object must have exactly 1 material slot."
            elif props.useMaterials and len(enabledMaterialSelections) == 0:
                reason = "'Render Multiple Materials' is enabled, but no materials have been selected for use."
            elif props.controlCamera and props.cameraControlMode == "unselected":
                reason = "'Control Render Camera' is enabled, but the control mode has not been set."
            elif not bpy.context.preferences.addons[Prefs.SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath:
                reason = "ImageMagick path is not set in Addon Preferences."

            SpritesheetRenderModalOperator.renderDisabledReason = reason
            
            return not reason
        except Exception as e:
            print("Error occurred in SpritesheetRenderModalOperator")
            print(e)
            return False

    def invoke(self, context, event):
        self.jsonData = {}
        self.outputDir = None
        self._error = None
        self._lastJobId = -1
        self._lastJobStartTime = None
        self._nextJobId = 0
        self._startTime = time.clock()
        self._terminalWriter = TerminalWriter(sys.stdout)
        self._sceneSnapshot = SceneSnapshot(context, self._terminalWriter)

        self._generator = self._frameRenderGenerator(context)

        self.execute(context)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        reportingProps = context.scene.ReportingPropertyGroup
        reportingProps.elapsedTime = time.clock() - self._startTime

        if event.type in {"ESC"}:
            self._error = "Job cancelled by request of user"
            self.cancel(context)
            return {"CANCELLED"}

        if event.type != "TIMER":
            return {"PASS_THROUGH"} # ignore non-timer events

        # Check if the generator is done (i.e. we're finished rendering)
        sentinel = object()
        if next(self._generator, sentinel) == sentinel and not self._error:
            self.cancel(context)
            return {"FINISHED"}

        # Check if error flag has been set
        if self._error:
            self.cancel(context)
            return {"CANCELLED"}

        # If it's not done and there's no error, then we're continuing; leave this event for others to handle if needed
        return {"PASS_THROUGH"}

    def execute(self, context):
        reportingProps = context.scene.ReportingPropertyGroup
        wm = context.window_manager

        self._timer = wm.event_timer_add(0.25, window = context.window)
        wm.modal_handler_add(self)

        reportingProps.hasAnyJobStarted = True
        reportingProps.jobInProgress = True
        reportingProps.outputDirectory = self._baseOutputDir()

    def cancel(self, context):
        reportingProps = context.scene.ReportingPropertyGroup
        reportingProps.lastErrorMessage = self._error if self._error else ""
        reportingProps.jobInProgress = False

        context.window_manager.event_timer_remove(self._timer)

        if self._error:
            self._terminalWriter.indent = 0
            self._terminalWriter.write("\n\nError occurred, cancelling operator: {}\n\n".format(self._error))
            self.report({'ERROR'}, self._error)

    def _frameRenderGenerator(self, context):
        scene = context.scene
        props = scene.SpritesheetPropertyGroup
        reportingProps = scene.ReportingPropertyGroup

        reportingProps.currentFrameNum = 0
        reportingProps.totalNumFrames = 0

        self._terminalWriter.write("\n\n---------- Starting spritesheet render job ----------\n\n")

        try:
            result = ImageMagick.validateImageMagickPath()
            if not result["succeeded"]:
                self._error = "ImageMagick check failed\n" + result["stderr"]
                return
        except Exception as e:
            print("Error occurred while validating ImageMagick executable path")
            print(e)
            self._error = "Failed to validate ImageMagick executable. Check that the path is correct in Addon Preferences."
            return

        self._setUpRenderSettings()

        self._terminalWriter.clearTerminal()

        scene.camera = props.renderCamera

        if props.useAnimations:
            enabledActions = [bpy.data.actions.get(a.name) for a in props.animationSelections if a.isSelectedForExport]
            separateFilesPerAnimation = props.separateFilesPerAnimation
        else:
            enabledActions = [None]
            separateFilesPerAnimation = False

        if props.useMaterials:
            enabledMaterialSelections = [ms for ms in props.materialSelections if ms.isSelectedForExport]
            enabledMaterials = [bpy.data.materials.get(ms.name) for ms in enabledMaterialSelections]
        else:
            enabledMaterialSelections = []
            enabledMaterials = [None]

        if props.rotateObject:
            rotations = [int(n * (360 / props.rotationNumber)) for n in range(props.rotationNumber)]
            rotationRoot = props.rotationRoot if props.rotationRoot else props.targetObject
            separateFilesPerRotation = props.separateFilesPerRotation
        else:
            rotations = [0]
            rotationRoot = props.targetObject
            separateFilesPerRotation = False
        
        # Variables for progress tracking
        materialNumber = 0
        expectedJsonFiles = (len(rotations) if props.separateFilesPerRotation else 1) * (len(enabledActions) if props.separateFilesPerAnimation else 1) # materials never result in separate JSON files

        reportingProps.totalNumFrames = self._countTotalFrames(enabledMaterials, rotations, enabledActions)
        self._terminalWriter.write("Expecting to render a total of {} frames\n".format(reportingProps.totalNumFrames))

        if separateFilesPerAnimation:
            outputMode = "per animation"
        elif separateFilesPerRotation:
            outputMode = "per rotation"
        else:
            outputMode = "per material"

        self._terminalWriter.write("File output will be generated {}\n\n".format(outputMode))

        if props.controlCamera and props.cameraControlMode == "move_once":
            self._optimizeCamera(context, rotationRoot = rotationRoot, rotations = rotations, enabledActions = enabledActions)

        self._terminalWriter.write("\n")

        for material in enabledMaterials:
            materialNumber += 1
            materialName = material.name if material else "N/A"
            renderData = []
            stillFrameNumber = 0
            totalFramesForMaterial = 0
            tempDir = tempfile.TemporaryDirectory()

            self._terminalWriter.write("Rendering material {} of {}: \"{}\"\n".format(materialNumber, len(enabledMaterials), materialName))
            self._terminalWriter.indent += 1

            if material is not None:
                props.targetObject.data.materials[0] = material
 
            rotationNumber = 0
            for rotationAngle in rotations:
                rotationNumber += 1
                actionNumber = 0

                self._terminalWriter.write("Rendering angle {} of {}: {} degrees\n".format(rotationNumber, len(rotations), rotationAngle))
                self._terminalWriter.indent += 1

                if props.rotateObject:
                    rotationRoot.rotation_euler[2] = math.radians(rotationAngle)

                tempDirPath = tempDir.name

                if props.controlCamera and props.cameraControlMode == "move_each_rotation":
                    self._optimizeCamera(context, rotationRoot = rotationRoot, rotations = rotations, enabledActions = enabledActions, currentRotation = rotationAngle)
                
                for action in enabledActions:
                    actionNumber += 1
                    totalFramesForAction = 0

                    if action is not None:
                        self._terminalWriter.write("Processing action {} of {}: \"{}\"\n".format(actionNumber, len(enabledActions), action.name))
                        self._terminalWriter.indent += 1

                        # Yield after each frame of the animation to update the UI
                        for val in self._renderAction(context, action, rotationAngle, tempDirPath):
                            actionData = val
                            yield

                        actionData["material"] = material
                        actionData["rotation"] = rotationAngle
                        renderData.append(actionData)

                        totalFramesForAction += actionData["numFrames"]
                        totalFramesForMaterial += actionData["numFrames"]

                        # Render now if files are being split by animation, so we can wipe out all the per-frame
                        # files before processing the next animation
                        if separateFilesPerAnimation:
                            self._terminalWriter.write("\nCombining image files for action {} of {}\n".format(actionNumber, len(enabledActions)))
                            imageMagickResult = self._runImageMagick(props, reportingProps, action, totalFramesForAction, tempDirPath, rotationAngle)

                            if not imageMagickResult["succeeded"]: # error running ImageMagick
                                return

                            self._createJsonFile(props, reportingProps, enabledMaterialSelections, renderData, imageMagickResult)
                            self._terminalWriter.write("\n")
                            
                            renderData = []
                            tempDir = tempfile.TemporaryDirectory() # change directories for per-frame files

                        self._terminalWriter.indent -= 1
                    else:
                        stillData = self._renderStill(rotationAngle, stillFrameNumber, tempDirPath)
                        renderData.append(stillData)
                        stillFrameNumber += 1
                        totalFramesForMaterial += 1

                        yield

                    # End of for(actions)

                if separateFilesPerRotation and not separateFilesPerAnimation:
                    self._terminalWriter.write("\nCombining image files for angle {} of {}\n".format(rotationNumber, len(rotations)))
                    self._terminalWriter.indent += 1

                    # Output one file for the whole rotation, with all animations in it
                    imageMagickResult = self._runImageMagick(props, reportingProps, action, totalFramesForAction, tempDirPath, rotationAngle)
                
                    if not imageMagickResult["succeeded"]: # error running ImageMagick
                        return

                    self._createJsonFile(props, reportingProps, enabledMaterialSelections, renderData, imageMagickResult)
                    self._terminalWriter.write("\n")
                    self._terminalWriter.indent -= 1

                    renderData = []
                    stillFrameNumber = 0
                    tempDir = tempfile.TemporaryDirectory() # change directories for per-frame files
                    
                self._terminalWriter.indent -= 1

                # End of for(rotations)

            if not separateFilesPerRotation and not separateFilesPerAnimation:
                self._terminalWriter.write("\nCombining image files for material {} of {}\n".format(materialNumber, len(enabledMaterials)))
                self._terminalWriter.indent += 1
                # Output one file for the entire material
                imageMagickResult = self._runImageMagick(props, reportingProps, action, totalFramesForMaterial, tempDirPath, rotationAngle)
            
                if not imageMagickResult["succeeded"]: # error running ImageMagick
                    return

                self._createJsonFile(props, reportingProps, enabledMaterialSelections, renderData, imageMagickResult)
                self._terminalWriter.write("\n")
                self._terminalWriter.indent -= 1

                renderData = []
                stillFrameNumber = 0
                tempDir = tempfile.TemporaryDirectory() # change directories for per-frame files

            self._terminalWriter.indent -= 1

            # End of for(materials)

        # Reset scene variables to their original state
        self._sceneSnapshot.restoreFromSnapshot(context)

        # Do some sanity checks and modify the final output based on the result
        sanityChecksPassed = self._performEndingSanityChecks(expectedJsonFiles, reportingProps)
        totalElapsedTime = time.clock() - self._startTime
        timeString = StringUtil.timeAsString(totalElapsedTime)

        completionMessage = "Rendering complete in " + timeString if sanityChecksPassed else "Rendering FAILED after " + timeString

        # Final output: show operator total time and a large completion message to be easily noticed
        termSize = os.get_terminal_size()
        self._terminalWriter.write("\n")
        self._terminalWriter.write(termSize.columns * "=" + "\n")
        self._terminalWriter.write( (termSize.columns // 2) * " " + completionMessage + "\n")
        self._terminalWriter.write(termSize.columns * "=" + "\n\n")

        return

    def _baseOutputDir(self):
        if bpy.data.filepath:
            dir = os.path.dirname(bpy.data.filepath)
            return os.path.join(dir, "Rendered spritesheets")
        else:
            return os.path.join(os.getcwd(), "Rendered spritesheets")

    def _createFilePath(self, props, action, rotationAngle, materialOverride = None, includeMaterial = True):
        if bpy.data.filepath:
            filename, _ = os.path.splitext(os.path.basename(bpy.data.filepath))
        else:
            filename = "rendered_spritesheet"

        outputFilePath = os.path.join(self._baseOutputDir(), filename)

        # Make sure output directory exists
        pathlib.Path(os.path.dirname(outputFilePath)).mkdir(exist_ok = True)

        if materialOverride:
            materialName = materialOverride.name
        else:
            materialName = props.targetObject.data.materials[0].name if props.useMaterials and len(props.targetObject.data.materials) > 0 else ""

        if materialName and includeMaterial:
            outputFilePath += "_" + self._formatStringForFilename(materialName)
        
        if props.useAnimations and props.separateFilesPerAnimation:
            outputFilePath += "_" + self._formatStringForFilename(action.name)

        if props.rotateObject and props.separateFilesPerRotation:
            outputFilePath += "_rot" + str(rotationAngle).zfill(3)

        return outputFilePath

    def _createJsonFile(self, props, reportingProps, enabledMaterialSelections, renderData, imageMagickData):
        jobId = self._getNextJobId()
        self._reportJob("JSON dump", "writing JSON attributes", jobId, reportingProps)

        if props.useAnimations and props.separateFilesPerAnimation:
            action = renderData[0]["action"]
        else:
            action = None

        if props.rotateObject and props.separateFilesPerRotation:
            rotation = renderData[0]["rotation"]
        else:
            rotation = None

        jsonFilePath = self._createFilePath(props, action, rotation, includeMaterial = False) + ".ssdata"

        # Since the material isn't part of the file path, we could end up writing each JSON file multiple times.
        # They all have the same data, so just skip writing if that's the case.
        if jsonFilePath in self.jsonData:
            self._reportJob("JSON dump", "JSON file already written at " + jsonFilePath, jobId, reportingProps, isSkipped = True)
            return

        jsonData = {
            "baseObjectName": os.path.splitext(os.path.basename(bpy.data.filepath))[0] if bpy.data.filepath else "target_object",
            "spriteWidth": props.spriteSize[0],
            "spriteHeight": props.spriteSize[1],
            "numColumns": imageMagickData["args"]["numColumns"],
            "numRows": imageMagickData["args"]["numRows"]
        }

        if props.useMaterials:
            # If using materials, need to reference where the spritesheet for each material is located
            jsonData["materialData"] = []

            for materialSelection in enabledMaterialSelections:
                imagePathForMaterial = self._createFilePath(props, action, rotation, materialOverride = materialSelection) + ".png"
                self.outputDir = os.path.dirname(imagePathForMaterial)
                relativePath = os.path.basename(imagePathForMaterial)

                jsonData["materialData"].append({
                    "name": materialSelection.name,
                    "file": relativePath,
                    "role": materialSelection.role
                })
        else:
            # When not using materials, there's only one image file per JSON file
            imagePath = self._createFilePath(props, action, rotation) + ".png"
            self.outputDir = os.path.dirname(imagePath)

            jsonData["imageFile"] = os.path.basename(imagePath)

        if props.useAnimations:
            jsonData["animations"] = []
        else:
            jsonData["stills"] = []

        for inData in renderData:
            outData = { }

            # Animation data (if present)
            if props.useAnimations:
                if not "action" in inData:
                    raise RuntimeError("props.useAnimations is enabled, but data object didn't have 'action' key")

                outData["frameRate"] = props.outputFrameRate # the same for all animations, but may not always be
                outData["name"] = inData["action"].name
                outData["numFrames"] = inData["numFrames"]
                outData["rotation"] = inData["rotation"]

                # The starting frame may not match the expected value, depending on what order ImageMagick combined
                # the files in. We need to find the matching file in the ImageMagick arguments to figure out the frame number.
                outData["startFrame"] = imageMagickData["args"]["inputFiles"].index(inData["firstFrameFilepath"])
                
                jsonData["animations"].append(outData)
            else:
                outData["frame"] = imageMagickData["args"]["inputFiles"].index(inData["filepath"])
                outData["rotation"] = inData["rotation"]

                jsonData["stills"].append(outData)

        with open(jsonFilePath, "w") as f:
            json.dump(jsonData, f, indent = "\t")

        self.jsonData[jsonFilePath] = jsonData
        self._reportJob("JSON dump", "output is at " + jsonFilePath, jobId, reportingProps, isComplete = True)

    def _countTotalFrames(self, materials, rotations, actions):
        totalFramesAcrossActions = 0

        for action in actions:
            if action is None:
                totalFramesAcrossActions += 1
            else:
                frameMin = math.floor(action.frame_range[0])
                frameMax = math.ceil(action.frame_range[1])
                numFrames = frameMax - frameMin + 1
                totalFramesAcrossActions += numFrames

        return totalFramesAcrossActions * len(materials) * len(rotations)

    def _formatStringForFilename(self, string):
        return string.replace(' ', '_').lower()

    def _getNextJobId(self):
        self._nextJobId += 1
        return self._nextJobId

    def _nextPowerOfTwo(self, val):
        """Returns the smallest power of two which is equal to or greater than val"""
        return 1 if val == 0 else 2 ** math.ceil(math.log2(val))

    def _optimizeCamera(self, context, rotationRoot = None, rotations = None, enabledActions = None, currentAction = None, currentRotation = None, reportJob = True):
        props = context.scene.SpritesheetPropertyGroup
        reportingProps = context.scene.ReportingPropertyGroup

        if not props.controlCamera:
            raise RuntimeError("_optimizeCamera called without controlCamera option enabled")

        jobId = self._getNextJobId()
        jobTitle = "Optimizing camera"

        if props.cameraControlMode == "move_once":
            if reportJob:
                self._reportJob(jobTitle, "finding parameters to cover the entire render", jobId, reportingProps)

            CameraUtil.optimizeForAllFrames(context, rotationRoot, rotations, enabledActions)
        elif props.cameraControlMode == "move_each_frame":
            if reportJob:
                self._reportJob(jobTitle, "finding parameters to cover the current frame", jobId, reportingProps)

            CameraUtil.fitCameraToTargetObject(context)
        elif props.cameraControlMode == "move_each_animation":
            if reportJob:
                self._reportJob(jobTitle, "finding parameters to cover the current animation", jobId, reportingProps)

            CameraUtil.optimizeForAction(context, currentAction)
        elif props.cameraControlMode == "move_each_rotation":
            if reportJob:
                self._reportJob(jobTitle, "finding parameters to cover the current rotation angle", jobId, reportingProps)

            CameraUtil.optimizeForRotation(context, rotationRoot, currentRotation, enabledActions)            

        completeMsg = "Camera will render from {}, with an ortho_scale of {}".format(StringUtil.formatNumber(props.renderCamera.location), StringUtil.formatNumber(props.renderCamera.data.ortho_scale))

        if reportJob:
            self._reportJob(jobTitle, completeMsg, jobId, reportingProps, isComplete = True)

    def _performEndingSanityChecks(self, expectedJsonFiles, reportingProps):
        jobId = self._getNextJobId()

        if reportingProps.currentFrameNum != reportingProps.totalNumFrames:
            self._error = "Expected to render {} frames, but actually rendered {}".format(reportingProps.totalNumFrames, reportingProps.currentFrameNum)
            return False

        # Make sure all the file paths we wrote in the JSON actually exist
        self._terminalWriter.write("Rendering complete. Performing sanity checks before ending operation.\n")
        self._terminalWriter.indent += 1
        if expectedJsonFiles == len(self.jsonData):
            self._reportJob("Sanity check", "wrote the expected number of JSON files ({})".format(expectedJsonFiles), jobId, reportingProps, isComplete = True)
        else:
            self._reportJob("Sanity check", "expected to write {} JSON files but found {}".format(expectedJsonFiles, len(self.jsonData)), jobId, reportingProps, isError = True)
            self._error = "An internal error occurred while writing JSON files."
            return False

        jobId = self._getNextJobId()
        jsonNum = 1
        for filePath, data in self.jsonData.items():
            self._reportJob("Sanity check", "validating JSON data {} of {}".format(jsonNum, len(self.jsonData)), jobId, reportingProps)
            jsonNum += 1

            # Check that file paths for image files are correct
            expectedFiles = []

            if "imageFile" in data:
                expectedFiles.append(data["imageFile"])
            
            if "materialData" in data:
                if len(expectedFiles) != 0:
                    self._reportJob("Sanity check", "JSON should not have both 'imageFile' and 'materialData' keys", jobId, reportingProps, isError = True)
                    self.report({'ERROR'}, "An internal error occurred while writing JSON files.")
                    return False
                    
                for materialData in data["materialData"]:
                    expectedFiles.append(materialData["file"])
            
            for filePath in expectedFiles:
                absPath = os.path.join(self.outputDir, filePath)

                if not os.path.isfile(absPath):
                    self._reportJob("Sanity check", "expected file not found at " + absPath, jobId, reportingProps, isError = True)
                    self._error = "An internal error occurred while writing JSON files."
                    return False

        self._reportJob("Sanity check", "successfully validated JSON data for {} file(s)".format(len(self.jsonData)), jobId, reportingProps, isComplete = True)
        self._terminalWriter.indent -= 1
        return True

    def _progressBar(self, title, numerator, denominator, width = None, showPercentage = True, showNumbers = True, numbersLabel = ""):
        numbersLabel = " " + numbersLabel if numbersLabel else ""
        numbersDisplay = "({}/{}{}) ".format(numerator, denominator, numbersLabel) if showNumbers else ""
        textPrefix = "{title} {numbersDisplay}".format(title = title, numbersDisplay = numbersDisplay)

        if width is None:
            termSize = os.get_terminal_size()
            width = termSize.columns - len(textPrefix) - 10

        progressPercent = numerator / denominator
        completedPlaces = math.floor(progressPercent * width)
        pendingPlaces = width - completedPlaces

        bar = "[{completed}{pending}]".format(completed = "#" * completedPlaces, pending = "-" * pendingPlaces)

        if showPercentage:
            bar = bar + " {}%".format(math.floor(100 * progressPercent))

        return textPrefix + bar

    def _renderAction(self, context, action, rotation, tempDirPath):
        scene = context.scene
        props = scene.SpritesheetPropertyGroup
        reportingProps = scene.ReportingPropertyGroup

        props.targetObject.animation_data.action = action

        frameMin = math.floor(action.frame_range[0])
        frameMax = math.ceil(action.frame_range[1])
        numFrames = frameMax - frameMin + 1

        actionData = {
            "action": action,
            "frameData": [],
            "rotation": rotation
        }
        
        numDigits = int(math.log10(frameMax)) + 1

        if props.controlCamera and props.cameraControlMode == "move_each_animation":
            self._optimizeCamera(context, currentAction = action)

        # Go frame-by-frame and render the object
        jobId = self._getNextJobId()
        renderedFrames = 0
        for index in range(frameMin, frameMax + 1):
            text = "({}/{})".format(index - frameMin + 1, numFrames)
            self._reportJob("Rendering frames", text, jobId, reportingProps)

            # Order of properties in filename is important; they need to sort lexicographically
            # in such a way that sequential frames naturally end up sequential in the sorted file list,
            # no matter what configuration options we're using
            filename = action.name + "_"

            if props.rotateObject:
                filename += "rot" + str(rotation).zfill(3) + "_"

            filename += str(index).zfill(numDigits)

            filepath = os.path.join(tempDirPath, filename)

            if index == frameMin:
                actionData["firstFrameFilepath"] = filepath + ".png"
            
            scene.frame_set(index)
            scene.render.filepath = filepath

            self._runRenderWithoutStdout(props, reportingProps)
            renderedFrames += 1

            # Yield after each frame to let the UI render
            yield

        actionData["numFrames"] = renderedFrames
        self._reportJob("Rendering frames", "completed rendering {} frames".format(renderedFrames), jobId, reportingProps, isComplete = True)

        yield actionData

    def _renderStill(self, rotationAngle, stillFrameNumber, tempDirPath):
        # Renders a single frame
        scene = bpy.context.scene
        props = scene.SpritesheetPropertyGroup
        reportingProps = scene.ReportingPropertyGroup

        filename = "out_still_" + str(stillFrameNumber).zfill(4)

        if props.rotateObject:
            filename += "_rot" + str(rotationAngle).zfill(3)

        filename += ".png"
        filepath = os.path.join(tempDirPath, filename)

        data = {
            "filepath": filepath,
            "rotation": rotationAngle
        }

        self._terminalWriter.write("Rendering single frame without animation\n")
        scene.render.filepath = filepath
        self._runRenderWithoutStdout(props, reportingProps)

        return data

    def _reportJob(self, title, text, jobId, reportingProps, isComplete = False, isError = False, isSkipped = False):
        if (jobId != self._lastJobId):
            if jobId < self._lastJobId:
                self._terminalWriter.write("\nWARNING: incoming job ID {} is smaller than the last job ID {}. This indicates a coding error in the addon.\n\n".format(jobId, self._lastJobId))

            self._lastJobId = jobId
            self._lastJobStartTime = time.clock()

        jobTimeSpent = time.clock() - self._lastJobStartTime
        if jobTimeSpent > 0.001:
            jobTimeSpentString = "[{}]".format(StringUtil.timeAsString(jobTimeSpent, precision = 2, includeHours = False))
        else:
            jobTimeSpentString = ""

        msg = title + ": " + text

        if isError:
            msgPrefix = "[ERROR] "
            persistMessage = True
        elif isComplete:
            msgPrefix = "[DONE] "
            persistMessage = True
        elif isSkipped:
            msgPrefix = "[SKIPPED] "
            persistMessage = True
        else:
            msgPrefix = "[ACTIVE] "
            persistMessage = False

        msgPrefix = (msgPrefix + jobTimeSpentString).ljust(22)
        msg = msgPrefix + msg + "\n"

        # Show a progress bar estimating completion of the entire operator
        progressBar = "\n" + self._progressBar("Overall progress", reportingProps.currentFrameNum, reportingProps.totalNumFrames, numbersLabel = "frames rendered") + "\n\n"

        # Show elapsed and remaining time
        if reportingProps.currentFrameNum > 0:
            timeElapsedString =   "Time elapsed:   {}".format(StringUtil.timeAsString(reportingProps.elapsedTime, precision = 2))
            timeRemainingString = "Time remaining: {}".format(StringUtil.timeAsString(reportingProps.estimatedTimeRemaining(), precision = 2))

            # Make the strings repeat on the right side of the terminal, with a small indent
            columnsRemaining = os.get_terminal_size().columns - len(timeElapsedString) - 10 
            fmtString = "{0} {1:>" + str(columnsRemaining) + "}\n"
            timeElapsedString = fmtString.format(timeElapsedString, timeElapsedString)

            columnsRemaining = os.get_terminal_size().columns - len(timeRemainingString) - 10 
            fmtString = "{0} {1:>" + str(columnsRemaining) + "}\n\n"
            timeRemainingString = fmtString.format(timeRemainingString, timeRemainingString)

            timeString = timeElapsedString + timeRemainingString
        else:
            timeString = ""

        # Don't persist the progress bar and time or else they'd fill the terminal every time we write
        self._terminalWriter.write(msg, unpersistedPortion = progressBar + timeString, persistMsg = persistMessage)

    def _runRenderWithoutStdout(self, props, reportingProps):
        if props.controlCamera and props.cameraControlMode == "move_each_frame":
            # Don't report job because this method is always being called inside of another job
            self._optimizeCamera(bpy.context, reportJob = False)

        # Get the original stdout file, close its fd, and open devnull in its place
        originalStdout = os.dup(1)
        sys.stdout.flush()
        os.close(1)
        os.open(os.devnull, os.O_WRONLY)
        
        try:
            bpy.ops.render.render(write_still = True)
            reportingProps.currentFrameNum += 1
        finally:
            # Reopen stdout in its original position as fd 1
            os.close(1)
            os.dup(originalStdout)
            os.close(originalStdout)
        
    def _runImageMagick(self, props, reportingProps, action, totalNumFrames, tempDirPath, rotationAngle):
        jobId = self._getNextJobId()
        self._reportJob("ImageMagick", "Combining {} frames into spritesheet with ImageMagick".format(totalNumFrames), jobId, reportingProps)

        outputFilePath = self._createFilePath(props, action, rotationAngle) + ".png"
        imageMagickOutput = ImageMagick.assembleFramesIntoSpritesheet(props.spriteSize, totalNumFrames, tempDirPath, outputFilePath)

        if not imageMagickOutput["succeeded"]:
            self._error = str(imageMagickOutput["stderr"]).replace("\\n", "\n").replace("\\r", "\r")
            self._reportJob("ImageMagick", self._error, jobId, reportingProps, isError = True)
        else:
            msg = "output file is at {}".format(outputFilePath)
            self._reportJob("ImageMagick", msg, jobId, reportingProps, isComplete = True)

        if props.padToPowerOfTwo:
            jobId = self._getNextJobId()
            imageSize = imageMagickOutput["args"]["outputImageSize"]
            targetSize = (self._nextPowerOfTwo(imageSize[0]), self._nextPowerOfTwo(imageSize[1]))
            targetSizeStr = "{}x{}".format(targetSize[0], targetSize[1])

            if targetSize == imageSize:
                self._reportJob("ImageMagick", "Padding not necessary; image output size {} is already power-of-two".format(targetSizeStr), jobId, reportingProps, isSkipped = True)
            else:
                self._reportJob("ImageMagick", "Padding output image to power-of-two size {}".format(targetSizeStr), jobId, reportingProps)
                ImageMagick.padImageToSize(imageMagickOutput["args"]["outputFilePath"], targetSize)
                self._reportJob("ImageMagick", "Output image successfully padded to power-of-two size {}".format(targetSizeStr), jobId, reportingProps, isComplete = True)

        return imageMagickOutput

    def _setUpRenderSettings(self):
        scene = bpy.context.scene
        props = scene.SpritesheetPropertyGroup
        
        scene.render.engine = 'CYCLES'
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.film_transparent = True  # Transparent PNG
        scene.render.bake_margin = 0
        scene.render.resolution_percentage = 100
        scene.render.resolution_x = props.spriteSize[0]
        scene.render.resolution_y = props.spriteSize[1]
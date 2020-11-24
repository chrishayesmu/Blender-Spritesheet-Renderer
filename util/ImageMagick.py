import bpy
import glob
import math
import os
import subprocess

from preferences import SpritesheetAddonPreferences as Prefs

def assembleFramesIntoSpritesheet(spriteSize, totalNumFrames, tempDirPath, outputFilePath):
    imageMagickArgs = _imageMagickArgs(spriteSize, totalNumFrames, tempDirPath, outputFilePath)
    processOutput = subprocess.run(imageMagickArgs["argsList"], stdout = subprocess.PIPE, stderr = subprocess.PIPE, cwd = tempDirPath, text = True)

    return {
        "args": imageMagickArgs,
        "stderr": str(processOutput.stderr),
        "succeeded": processOutput.returncode == 0
    }

def padImageToSize(imagePath, size):
    extentArg = str(size[0]) + "x" + str(size[1])

    args = [
        bpy.context.preferences.addons[Prefs.SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath,
        "convert",
        "-background",
        "none", # added pixels will be transparent
        "-gravity",
        "NorthWest", # keep existing image stationary relative to upper left corner
        imagePath, # input image
        "-extent",
        extentArg,
        imagePath # output image
    ]

    processOutput = subprocess.run(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

    return processOutput.returncode == 0

def validateImageMagickPath():
    if not bpy.context.preferences.addons[Prefs.SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath:
        return {
            "stderr": "ImageMagick path is not configured in Addon Preferences",
            "succeeded": False
        }

    # Just run a basic command to make sure ImageMagick is installed and the path is configured correctly
    processOutput = subprocess.run([bpy.context.preferences.addons[Prefs.SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath, "-version"], stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True)

    return {
        "stderr": str(processOutput.stderr),
        "succeeded": processOutput.returncode == 0
    }

def _imageMagickArgs(spriteSize, numImages, tempDirPath, outputFilePath):
        # We need the input files to be in this known order, but the command line
        # won't let us pass too many files at once. ImageMagick supports reading in
        # file names from a text file, so we write everything to a temp file and pass that.
        files = sorted(glob.glob(os.path.join(tempDirPath, "*.png")))
        inFilePath = os.path.join(tempDirPath, "filelist.txt")

        with open(inFilePath, "w") as f:
            quotedFilesString = "\n".join('"{0}"'.format(os.path.basename(f)) for f in files)
            f.write(quotedFilesString)

        resolution = str(spriteSize[0]) + "x" + str(spriteSize[1])
        spacing = "+0+0" # no spacing between images in grid, or between grid and image edge 
        geometryArg = resolution + spacing

        # ImageMagick only needs the number of rows, and it can then figure out the
        # number of columns, but we need both for our own data processing anyway
        numRows = math.floor(math.sqrt(numImages))
        numColumns = math.ceil(numImages / numRows)
        tileArg = str(numColumns) + "x" + str(numRows)

        # Not needed for ImageMagick, but useful info to return
        numPixelsWide = numColumns * spriteSize[0]
        numPixelsTall = numRows * spriteSize[1]

        argsList = [
            bpy.context.preferences.addons[Prefs.SpritesheetAddonPreferences.bl_idname].preferences.imageMagickPath,
            "montage",
            "@" + os.path.basename(inFilePath), # '@' prefix indicates to read input files from a text file; path needs to be relative to cwd
            "-geometry",
            geometryArg,
            "-tile",
            tileArg,
            "-background",
            "none",
            outputFilePath
        ]

        args = {
            "argsList": argsList,
            "inputFiles": files,
            "numColumns": numColumns,
            "numRows": numRows,
            "outputFilePath": outputFilePath,
            "outputImageSize": (numPixelsWide, numPixelsTall)
        }

        return args
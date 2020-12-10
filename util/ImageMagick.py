import glob
import math
import os
import subprocess
from typing import Any, Dict, Optional, Tuple

import preferences

from util import FileSystemUtil

def assemble_frames_into_spritesheet(sprite_size: Tuple[int, int], total_num_frames: int, temp_dir_path: str, output_file_path: str) -> Dict[str, Any]:
    image_magick_args = _image_magick_args(sprite_size, total_num_frames, temp_dir_path, output_file_path)
    process_output = subprocess.run(image_magick_args["argsList"], stdout = subprocess.PIPE, stderr = subprocess.PIPE, cwd = temp_dir_path, text = True, check = False)

    return {
        "args": image_magick_args,
        "stderr": str(process_output.stderr),
        "succeeded": process_output.returncode == 0
    }

def locate_image_magick_exe() -> Optional[str]:
    system = FileSystemUtil.get_system_type()
    if system != "windows":
        # Only supported for Windows right now
        return None

    # The most common installation paths will be in Program Files, so we'll just check those and call it good
    file_systems = FileSystemUtil.get_file_systems()
    subdirs = ["Program Files", "Program Files (x86)"]

    for filesys in file_systems:
        for subdir in subdirs:
            subdir_path = os.path.join(filesys, subdir)
            subdir_glob_path = os.path.join(subdir_path, "*")

            for path in glob.iglob(subdir_glob_path, recursive = False):
                if "imagemagick" in path.lower():
                    exe_path = os.path.join(path, "magick.exe")

                    if os.path.isfile(exe_path) and validate_image_magick_at_path(exe_path)[0]:
                        return exe_path

    return None

def pad_image_to_size(image_path: str, size: Tuple[int, int]) -> bool:
    extent_arg = str(size[0]) + "x" + str(size[1])

    args = [
        preferences.PrefsAccess.image_magick_path,
        "convert",
        "-background",
        "none", # added pixels will be transparent
        "-gravity",
        "NorthWest", # keep existing image stationary relative to upper left corner
        image_path, # input image
        "-extent",
        extent_arg,
        image_path # output image
    ]

    process_output = subprocess.run(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE, check = False)

    return process_output.returncode == 0

def validate_image_magick_at_path(path: str = None) -> Tuple[bool, Optional[str]]:
    """Checks that ImageMagick is installed at the given path, or the path stored in the addon preferences if no path is provided."""

    if not path:
        if not preferences.PrefsAccess.image_magick_path:
            return (False, "ImageMagick path is not configured in Addon Preferences")

        path = preferences.PrefsAccess.image_magick_path

    # Just run a basic command to make sure ImageMagick is installed and the path is correct
    process_output = subprocess.run([path, "-version"], stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True, check = False)

    return (process_output.returncode == 0, str(process_output.stderr))

def _image_magick_args(sprite_size: Tuple[int, int], num_images: int, temp_dir_path: str, output_file_path: str) -> Dict[str, Any]:
    # We need the input files to be in this known order, but the command line
    # won't let us pass too many files at once. ImageMagick supports reading in
    # file names from a text file, so we write everything to a temp file and pass that.
    files = sorted(glob.glob(os.path.join(temp_dir_path, "*.png")))
    in_file_path = os.path.join(temp_dir_path, "filelist.txt")

    with open(in_file_path, "w") as f:
        quoted_files_string = "\n".join('"{0}"'.format(os.path.basename(f)) for f in files)
        f.write(quoted_files_string)

    resolution = str(sprite_size[0]) + "x" + str(sprite_size[1])
    spacing = "+0+0" # no spacing between images in grid, or between grid and image edge
    geometry_arg = resolution + spacing

    # ImageMagick only needs the number of rows, and it can then figure out the
    # number of columns, but we need both for our own data processing anyway
    num_rows = math.floor(math.sqrt(num_images))
    num_columns = math.ceil(num_images / num_rows)
    tile_arg = str(num_columns) + "x" + str(num_rows)

    # Not needed for ImageMagick, but useful info to return
    num_pixels_wide = num_columns * sprite_size[0]
    num_pixels_tall = num_rows * sprite_size[1]

    args_list = [
        preferences.PrefsAccess.image_magick_path,
        "montage",
        "@" + os.path.basename(in_file_path), # '@' prefix indicates to read input files from a text file; path needs to be relative to cwd
        "-geometry",
        geometry_arg,
        "-tile",
        tile_arg,
        "-background",
        "none",
        output_file_path
    ]

    args = {
        "argsList": args_list,
        "inputFiles": files,
        "numColumns": num_columns,
        "numRows": num_rows,
        "outputFilePath": output_file_path,
        "outputImageSize": (num_pixels_wide, num_pixels_tall)
    }

    return args
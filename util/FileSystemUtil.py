import platform
import string
import subprocess
from typing import List

#pylint: disable=import-outside-toplevel

def get_file_systems() -> List[str]:
    system = get_system_type()
    file_systems = []

    if system == "windows":
        from ctypes import windll

        # Windows: we're given a bit mask where each bit position corresponds to a drive letter
        # Credit: https://stackoverflow.com/a/827398/
        bitmask = windll.kernel32.GetLogicalDrives()

        for letter in string.ascii_uppercase:
            if bitmask & 1:
                file_systems.append(letter + ":\\")

            bitmask >>= 1

    return file_systems

def get_system_type() -> str:
    """Attempts to determine what type of system we're on, limited to systems this addon can usefully do things with"""

    system = platform.uname()[0].lower()

    if system in ["windows"]:
        return system

    return "unknown"

def open_file_explorer(dir_path: str) -> bool:
    if not dir_path:
        raise ValueError("openFileExplorer called with empty dirPath argument ({})".format(dir_path))

    system = get_system_type()

    if system == "windows":
        subprocess.Popen('explorer "{}"'.format(dir_path))
        return True

    return False
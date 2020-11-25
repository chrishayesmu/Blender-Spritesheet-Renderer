import platform
import string
import subprocess

def getFileSystems():
    system = getSystemType()
    fileSystems = []

    if system == "windows":
        from ctypes import windll

        # Windows: we're given a bit mask where each bit position corresponds to a drive letter
        # Credit: https://stackoverflow.com/a/827398/
        bitmask = windll.kernel32.GetLogicalDrives()

        for letter in string.ascii_uppercase:
            if bitmask & 1:
                fileSystems.append(letter + ":\\")

            bitmask >>= 1

    return fileSystems

def getSystemType():
    """Attempts to determine what type of system we're on"""

    system = platform.uname()[0]

    if system.lower() in ["windows"]: # TODO extend this
        return system.lower()

    return "unknown"

def openFileExplorer(dirPath):
    if not dirPath:
        raise ValueError("openFileExplorer called with empty dirPath argument ({})".format(dirPath))

    system = getSystemType()

    if system == "windows":
        subprocess.Popen('explorer "{}"'.format(dirPath))
        return True
    else:
        return False
import math
from mathutils import Vector

def formatNumber(val, precision = 3):
    if type(val) in [tuple, Vector]:
        return tuple(round(x, precision) for x in val)
    else:
        return round(val, precision)

def timeAsString(timeInSeconds, precision = 0, includeHours = True):
    if includeHours:
        hours = math.floor(timeInSeconds / 3600)
        hoursStr = str(hours).zfill(2)
        timeInSeconds -= hours * 3600

    minutes = math.floor(timeInSeconds / 60)
    minutesStr = str(minutes).zfill(2)
    timeInSeconds -= minutes * 60

    seconds = round(timeInSeconds, precision)
    secondsParts = str(seconds).split(".")
    wholeSecondsStr = secondsParts[0].zfill(2)
    fracSecondsStr = secondsParts[1] + "0" * (precision - len(secondsParts[1])) if len(secondsParts) > 1 else "0" * precision # right pad zeroes for the fractional part    
    secondsStr = wholeSecondsStr + "." + fracSecondsStr if precision > 0 else wholeSecondsStr

    return hoursStr + ":" + minutesStr + ":" + secondsStr if includeHours else minutesStr + ":" + secondsStr
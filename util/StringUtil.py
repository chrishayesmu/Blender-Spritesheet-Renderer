import math
from mathutils import Vector

def format_number(val, precision = 3):
    if type(val) in [tuple, Vector]:
        return tuple(round(x, precision) for x in val)
    else:
        return round(val, precision)

def time_as_string(time_in_seconds, precision = 0, include_hours = True):
    if include_hours:
        hours = math.floor(time_in_seconds / 3600)
        hours_str = str(hours).zfill(2)
        time_in_seconds -= hours * 3600

    minutes = math.floor(time_in_seconds / 60)
    minutes_str = str(minutes).zfill(2)
    time_in_seconds -= minutes * 60

    seconds = round(time_in_seconds, precision)
    seconds_parts = str(seconds).split(".")
    whole_seconds_str = seconds_parts[0].zfill(2)
    frac_seconds_str = seconds_parts[1] + "0" * (precision - len(seconds_parts[1])) if len(seconds_parts) > 1 else "0" * precision # right pad zeroes for the fractional part
    seconds_str = whole_seconds_str + "." + frac_seconds_str if precision > 0 else whole_seconds_str

    return hours_str + ":" + minutes_str + ":" + seconds_str if include_hours else minutes_str + ":" + seconds_str

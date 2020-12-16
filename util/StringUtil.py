import math
from mathutils import Vector
from typing import List, Tuple, Union

def format_number(val: Union[float, Tuple, Vector], precision: int = 3) -> Union[float, Tuple, Vector]:
    if type(val) in [tuple, Vector]:
        return tuple(round(x, precision) for x in val)

    return round(val, precision)

def join_with_commas(elements: List[str], separator: str = ", ", quote_elements: bool = False) -> str:
    if len(elements) == 0:
        raise ValueError("argument contains no elements")

    if quote_elements:
        elements = ['"' + e + '"' for e in elements]

    if len(elements) == 1:
        return elements[0]

    if len(elements) == 2:
        return elements[0] + " and " + elements[1]

    # Join all but the last element, then add the last separately
    return separator.join(elements[:-1]) + separator + "and " + elements[-1]

def time_as_string(time_in_seconds: float, precision: int = 0, include_hours: bool = True) -> str:
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

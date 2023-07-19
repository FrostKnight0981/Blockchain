import asyncio
import datetime
from time import time


def format_datetime(value):
    time_diff = int(time() - value)
    if time_diff < 60:
        return f"{time_diff} секунд{numeric_word_end(time_diff)} назад"
    elif time_diff < 60 * 60:
        return f"{time_diff // 60} минут{numeric_word_end(time_diff // 60)} назад"
    elif time_diff < 24 * 60 * 60:
        return f"{time_diff // (60 * 60)} час{numeric_word_end(time_diff // (60 * 60), ['ов','','а'])} назад"
    else:
        return str(datetime.datetime.fromtimestamp(value))


def format_filesize(value):
    if value < 1024:
        return f"{value} байт"
    elif value < 1024**2:
        return f"{value/1024:.2f} КБайт"
    else:
        return f"{value/(1024**2):.2f} МБайт"


def format_coin(value, prefix=None):
    prefix_sizes = {
        "G": 9,
        "M": 6,
        "K": 3
    }
    size = prefix_sizes.get(prefix)
    if size is None:
        return f"{value} Coin"
    else:
        return f"{int_to_floatstr(value, size)} {prefix}Coin"


def numeric_word_end(value: int, d: list = None) -> str:
    if d is None:
        d = ["", "у", "ы"]
    rem = value % 10
    if 10 < value < 20 or rem == 0 or rem >= 5:
        return d[0]
    elif rem == 1:
        return d[1]
    else:
        return d[2]


def int_to_floatstr(value: int, zeroes: int) -> str:
    result = ""
    was = False
    while zeroes >= 0 or value > 0:
        if zeroes == 0:
            if was:
                result += "."
            else:
                was = True
        rem = value % 10
        result += str(rem) if was or rem > 0 else ""
        if not was and value % 10 > 0:
            was = True
        value //= 10
        zeroes -= 1
    return result[::-1]

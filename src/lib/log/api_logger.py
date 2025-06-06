import datetime
import time
from enum import IntEnum
from typing import Optional


class EnumColor(IntEnum):
    RED = 196
    GREEN = 46
    YELLOW = 220
    LIGHT_PURPLE = 0
    PURPLE = 0
    CYAN = 0
    LIGHT_GRAY = 0
    BLACK = 0


def test_color():
    for i in range(0, 16):
        for j in range(0, 16):
            code = str(i * 16 + j)
            print(u"\u001b[38;5;" + code + "m " + code.ljust(4), end=", ")
        print(u"\u001b[0m")


def test_color2(message):
    code = str(196)
    print(u"\u001b[38;5;" + code + "m " + message + "\u001b[0m" + " et voilà qui est fait")


def logger_print(message, color: EnumColor = EnumColor.RED):
    if color is None:
        color = EnumColor.YELLOW
    code = str(color.value)
    print(u"\u001b[38;5;" + code + "m " + message + "\u001b[0m")


class ApiLogger(object):
    def __init__(self, message, color: EnumColor = EnumColor.YELLOW):
        self.message = message
        self.time_logger_created = time.time_ns()
        logger_print(
            message=str(datetime.datetime.now()) + " " + self.message,
            color=color
        )

    def print_log(self, extend_message: Optional[str] = None, color: EnumColor = EnumColor.GREEN):
        diff = time.time_ns() - self.time_logger_created
        logger_print(
            message=str(datetime.datetime.now()) + " " + self.message + (f" --- {extend_message}" if extend_message else "") + ": " + f'{ApiLogger.convert_ns_to_hours_format(diff)}',
            color=color
        )

    def print_error(self, message_error: str, color: EnumColor = EnumColor.RED):
        diff = time.time_ns() - self.time_logger_created
        logger_print(
            message=str(datetime.datetime.now()) + " " + self.message + " --- go to error, here's why: " + message_error + ": " + f'{ApiLogger.convert_ns_to_hours_format(diff)}',
            color=color
        )

    @staticmethod
    def convert_ns_to_hours_format(time_in_ns: int) -> str:
        # Convert nanoseconds to milliseconds
        time_in_ms = time_in_ns / 1_000_000

        # Calculate hours, minutes, seconds, and milliseconds
        hours = int(time_in_ms / (1000 * 60 * 60))
        minutes = int((time_in_ms % (1000 * 60 * 60)) / (1000 * 60))
        seconds = int((time_in_ms % (1000 * 60)) / 1000)
        milliseconds = int(time_in_ms % 1000)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


if __name__ == '__main__':
    test_color()
    # test_color2("Adrian")
    api_logger = ApiLogger("Message de log")
    api_logger.print_log()
    time.sleep(1)
    api_logger.print_log(EnumColor.RED)

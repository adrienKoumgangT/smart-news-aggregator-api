import datetime
import random
import time
import uuid
from typing import Optional

from dateutil import parser
from json import JSONEncoder

from bson import ObjectId


# subclass JSONEncoder
class MyJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return str(o)
        if isinstance(o, ObjectId):
            return str(o)
        return o.__dict__


def my_json_decoder(dct):
    for key, value in dct.items():
        # Try to parse datetime strings
        if isinstance(value, str):
            try:
                dct[key] = datetime.datetime.fromisoformat(value)
            except ValueError as e:
                pass  # Leave as string if not ISO datetime
    return dct


class TimeUtils(object):

    @staticmethod
    def get_current_time_ms():
        """
        Get the current time in milliseconds.
        """
        return int(time.time() * 1000)

    @staticmethod
    def convert_ms_to_utc(ms):
        """
        Convert time in milliseconds to UTC time.
        """
        utc_datetime = datetime.datetime.utcfromtimestamp(ms / 1000.0)
        return utc_datetime


class IdentifiedUtils(object):
    @staticmethod
    def get_unique_id():
        t = time.time()
        id4 = uuid.uuid4()
        my_id = str(int(t)) + '-' + str(t).split('.')[1] + '-' + str(id4)
        return my_id


def test_time_utils():
    # Example usage
    current_time_ms = TimeUtils.get_current_time_ms()
    print("Current time in milliseconds:", current_time_ms)

    utc_time = TimeUtils.convert_ms_to_utc(current_time_ms)
    print("UTC time:", utc_time)


def convert_str_to_datetime(s: str | datetime.datetime) -> Optional[datetime.datetime]:
    if s:
        if isinstance(s, datetime.datetime):
            return s
        if isinstance(s, str):
            try:
                return datetime.datetime.fromisoformat(s)
            except Exception | ValueError as e:
                try:
                    return parser.parse(s)
                except ValueError as e:
                    pass
    return None


# Generate a random datetime between start_date and end_date
def random_datetime(start, end):
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + datetime.timedelta(seconds=random_seconds)



if __name__ == '__main__':
    test_time_utils()


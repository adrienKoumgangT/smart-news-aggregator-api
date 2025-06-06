import datetime
import time
import uuid
from json import JSONEncoder


# subclass JSONEncoder
class MyJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return str(o)
        return o.__dict__


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


if __name__ == '__main__':
    test_time_utils()


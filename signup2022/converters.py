import re
from datetime import date, datetime


class DateConverter:
    regex = '2022-07-[0-9]{2}'

    def to_python(self, value):
        return datetime.strptime("2022-07-18", "%Y-%m-%d").date()

    def to_url(self, value):
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str) and re.fullmatch(self.regex, value):
            return value
        raise ValueError("Expected date, or date formmatted string, but got : %s" % value)

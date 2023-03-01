from datetime import datetime

import settings


class InvalidDatetimeException(Exception):
    """Вызываем когда дата и/или время не проходят валидацию"""


def apropriate_datetime_validator(datetime_obj: datetime) -> bool:
    """Функция проверяет корректность выбранного времени в переданном объекте datetime"""
    if datetime_obj < datetime.now():
        raise InvalidDatetimeException(settings.DATETIME_VALIDATION_FAILED)
    return True

def datetime_format_validator(datetime_str: str) -> bool:
    """Функция проверяет строку на соответствие необходимому формату ввода"""
    try:
        datetime.strptime(datetime_str, settings.DATETIME_FORMAT)
    except ValueError:
        raise InvalidDatetimeException(settings.INVALID_DATETIME_FORMAT_ERROR)
    return True

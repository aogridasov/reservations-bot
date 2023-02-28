from datetime import datetime
GREETINGS = """ Привет!

Здесь будет привественное сообщение с командами бота!
"""

HELP = """HELP:

Здесь будут команды и FAQ
"""

# Формат ввода даты и времени
DATETIME_FORMAT = '%d-%m-%Y %H:%M'
DATETIME_DB_FORMAT = '%Y-%m-%d %H:%M'
INVALID_DATETIME_FORMAT_ERROR = """Неверно введены дата или время!
Пожалуйста используйте следующий формат: {}
""".format(datetime.now().strftime(DATETIME_FORMAT))
DATETIME_VALIDATION_FAILED = 'Ой, какая-то странная дата... Введите актуальную!'

RESERVER_ADDITION_START = 'Добавляем новый резерв. '
RESERVER_ADDITION_GUEST_NAME = 'Укажите имя гостя.'
RESERVER_ADDITION_TIME = f'Укажите дату и время визита в формате: {datetime.now().strftime(DATETIME_FORMAT)}'
RESERVER_ADDITION_MORE_INFO = 'Предоставьте дополнительную информацию. Количество гостей, номер стола, etc'

RESERVER_ADDITION_SAVE_EDIT_DELETE = 'Вы собираетесь сохранить бронирование:'
RESERVER_ADDITION_END_SAVE = 'Запись успешно сохранена!'

CARD_BUTTONS_ERROR_MSG = 'Что-то пошло не так! Вызовите сообщение об этом резерве заново и повторите попытку!'

RESERVE_EDITING_CHOICE = 'Что меняем?'

NOTIFY_ALL_CONFIRMATION = 'Другие пользователи получили оповещение!'
NOTIFY_ALL_NEW_RESERVE = 'Появилась новая бронь:'
NOTIFY_ALL_EDIT_RESERVE = 'Изменение в бронировании:'
NOTIFY_ALL_DELETE_RESERVE = 'Бронирование отменена и удалено из базы данных:'


#buttons
NEW_RESERVE_BUTTON = 'Новое бронирование'
TODAY_RESERVES_BUTTON = 'Бронирования на сегодня'
ALL_RESERVES_BUTTON = 'Все бронирования'
ARCHIVE_BUTTON = 'Старые бронирования'
HELP_BUTTON = 'Справка'


NO_INFO_FOUND = 'Ничего не нашлось :('

import sqlite3
import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import List

import settings
from validators import (apropriate_datetime_validator, date_format_validator,
                        datetime_format_validator)

DB_CONNECTION = sqlite3.connect('reservations.db')
DB_CONNECTION.row_factory = sqlite3.Row
DB_CURSOR = DB_CONNECTION.cursor()


@dataclass
class Reservation:
    """Класс для бронирований"""
    id: int = None
    guest_name: str = None
    date_time: datetime = None
    info: str = None
    user_added: str = None
    visited: int = 0

    @staticmethod
    def str_to_datetime(datetime_str: str) -> datetime:
        """Метод парсит строку в нужном формате в datetime объект"""
        datetime_format_validator(datetime_str)
        datetime_obj = datetime.strptime(
            datetime_str, settings.DATETIME_FORMAT
        )
        apropriate_datetime_validator(datetime_obj)
        return datetime_obj

    @staticmethod
    def str_to_date(date: str) -> datetime:
        """Метод парсит строку в нужном формате в date объект"""
        date_format_validator(date)
        date_obj = datetime.strptime(date, '%d.%m.%Y')
        return date_obj

    @staticmethod
    def parse_escape(line: str) -> str:
        """Метод закрывает специальные символы
        от обработки parse_mode телеграма"""
        escaped_line = line
        for i in line:
            if i in settings.HTML_ESCAPE_SYMBOLS.keys():
                escaped_line.replace(
                    i, settings.HTML_ESCAPE_SYMBOLS[i]
                )
        return escaped_line

    def datetime_to_db_format(self) -> str:
        """Метод преобразует datetime объект
        в данные для передачи в соответсвующую колонку БД"""
        return self.date_time.strftime(settings.DATETIME_DB_FORMAT)

    def visited_to_emoji(self):
        """Превращает булево значение self.visited в эмоджи"""
        if self.visited == 1:
            return '✅'
        return '❌'

    def visited_on_off(self):
        """Меняет значение visited на противоположное"""
        if self.visited == 1:
            self.visited = 0
        elif self.visited == 0:
            self.visited = 1

    def reserve_preview(self):
        """Возвращает сокращенную информацию о резерве для превью"""
        preview = """<b>Имя гостя:</b> {}
<b>Время визита:</b> {}

<b>Дополнительная информация:</b>
{}
        """.format(
            self.parse_escape(self.guest_name),
            self.date_time.strftime(settings.DATETIME_FORMAT),
            self.parse_escape(self.info),
        )
        return textwrap.dedent(preview)

    def reserve_card(self):
        """Возвращает полную информацию о резерве для карточки резерва"""
        card = """<b>Имя гостя:</b> {}
<b>Время визита:</b> {}

<b>Дополнительная информация:</b>
{}

<b>Бронь принял(а):</b> {}
<b>Гости пришли:</b> {}
        """.format(
            self.parse_escape(self.guest_name),
            self.date_time.strftime(settings.DATETIME_FORMAT),
            self.parse_escape((textwrap.dedent(self.info))),
            self.user_added,
            self.visited_to_emoji(),
        )
        return textwrap.dedent(card)

    def reserve_line(self, logs=True):
        """Возвращает краткую информацию о резерве в виде строки"""
        if logs is True:
            visited = self.visited
        else:
            visited = self.visited_to_emoji()

        line = (
            f'{self.date_time.strftime(settings.DATETIME_FORMAT)} | {self.parse_escape(self.guest_name)} | {visited}'
        )
        return line

    def reserve_copy_card(self):
        return f"""`TR
{self.date_time.strftime(settings.DATETIME_FORMAT)}
{self.guest_name}
{self.info}`
    """


def parse_db_to_reservation_class(reservations_list: List) -> List:
    """Принимает список с данными из бд
    и парсит в список классов Reservation"""
    reservations = []
    for line in reservations_list:
        parsed_line = dict(line)
        reservations.append(
            Reservation(
                id=parsed_line['rowid'],
                guest_name=parsed_line['guest_name'],
                date_time=datetime.strptime(
                    parsed_line['date_time'], settings.DATETIME_DB_FORMAT
                ),
                info=parsed_line['info'],
                user_added=parsed_line['user_added'],
                visited=parsed_line['visited'],
            )
        )
    return reservations


def add_reservation(reservation: Reservation):
    """Функция записывает данные резерва
    из объекта класса Reservation в базу данных"""
    with DB_CONNECTION:
        DB_CURSOR.execute(
            """
            INSERT INTO reservations
            VALUES (:guest_name, :date_time, :info, :user_added, :visited)
            """,
            {
                'guest_name': reservation.guest_name,
                'date_time': reservation.datetime_to_db_format(),
                'info': reservation.info,
                'user_added': reservation.user_added,
                'visited': reservation.visited,
            }
        )


def delete_reservation(reservation: Reservation):
    """Функция находит соответствующую строку и удаляет из бд"""
    with DB_CONNECTION:
        DB_CURSOR.execute(
            """DELETE FROM reservations
               WHERE rowid = :id""",
            {'id': reservation.id}
        )


def edit_reservation(reservation: Reservation):
    """Функция находит соответствующую строку в бд и изменяет её"""
    with DB_CONNECTION:
        DB_CURSOR.execute(
            """UPDATE reservations
               SET
               guest_name=:guest_name,
               date_time=:date_time,
               info=:info,
               visited=:visited
               WHERE rowid = :id""",
            {
                'id': reservation.id,
                'guest_name': reservation.guest_name,
                'date_time': reservation.datetime_to_db_format(),
                'info': reservation.info,
                'visited': reservation.visited,
            }
        )


def show_reservations_all():
    """Функция выводит все БУДУЩИЕ резервы."""
    DB_CURSOR.execute(
        """
        SELECT rowid, *
        FROM reservations
        WHERE date(date_time) >= DATE('now', 'localtime')
        ORDER BY date_time
        """
    )
    return parse_db_to_reservation_class(DB_CURSOR.fetchall())


def show_reservations_archive():
    """Функция выводит все ПРОШЕДШИЕ резервы."""
    DB_CURSOR.execute(
         """
         SELECT rowid, *
         FROM reservations
         WHERE date(date_time) < DATE('now', 'localtime')
         ORDER BY date_time
         """
    )
    return parse_db_to_reservation_class(DB_CURSOR.fetchall())


def show_reservations_today():
    """Функция выводит строки из бд, где дата соответствует текущей"""
    DB_CURSOR.execute(
        """
        SELECT rowid, *
        FROM reservations
        WHERE date(date_time) = DATE('now', 'localtime')
        ORDER BY date_time
        """
    )
    results = DB_CURSOR.fetchall()
    return parse_db_to_reservation_class(results)


def show_reservations_per_date(passed_date: datetime):
    """Функция выводит строки из БД,
    где дата соответствует переданной в функцию"""
    DB_CURSOR.execute(
        """
        SELECT rowid, *
        FROM reservations
        WHERE date(date_time) = DATE(:passed_date)
        ORDER BY date_time
        """,
        {'passed_date': passed_date.strftime(settings.DATE_DB_FORMAT)}
    )
    results = DB_CURSOR.fetchall()
    return parse_db_to_reservation_class(results)


def add_chat_id(chat_id: int):
    """Функция записывает id чата в базу данных"""
    with DB_CONNECTION:
        DB_CURSOR.execute(
            "INSERT INTO chats VALUES (:id)", {'id': chat_id}
        )


def get_chat_id_list() -> List[int]:
    """Функция выводит из бд ID всех чатов, с которыми общается бот"""
    DB_CURSOR.execute(
        "SELECT id, * FROM chats",
    )
    return [dict(chat_id)['id'] for chat_id in DB_CURSOR.fetchall()]

import json
import sqlite3
import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Reservation:
    """Класс для бронирований"""
    id: int = None
    guest_name: str = None
    date_time: datetime = None
    info: str = None
    user_added: str = None
    visited: int = 0

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
        preview = """\
        Имя гостя: {}
        Время визита: {}
        Дополнительная информация:
        {}""".format(
            self.guest_name,
            self.date_time,
            self.info,
        )
        return textwrap.dedent(preview)

    def reserve_card(self):
        """Возвращает полную информацию о резерве для карточки резерва"""
        card = """\
        Имя гостя: {}
        Время визита: {}
        Дополнительная информация:
        {}
        Бронь принял: {}
        Гости пришли: {}
        """.format(
            self.guest_name,
            self.date_time,
            self.info,
            self.user_added,
            self.visited_to_emoji(),
        )
        return textwrap.dedent(card)

    def to_json(self):
        """Возвращает информацию о бронировании в JSON формате"""
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            sort_keys=True, indent=4
        )

    @classmethod
    def from_json(cls, json_obj):
        """Создаёт экземпляр класса на основании полученного JSON объекта"""
        return cls.__init__(**json.loads(json_obj))


def parse_db_to_reservation_class(reservations_list: List) -> List:
    """Принимает список с данными из бд и парсит в список классов Reservation"""
    reservations = []
    for line in reservations_list:
        parsed_line = dict(line)
        reservations.append(
            Reservation(
                id=parsed_line['rowid'],
                guest_name=parsed_line['guest_name'],
                date_time=parsed_line['date_time'],
                info=parsed_line['info'],
                user_added=parsed_line['user_added'],
                visited=parsed_line['visited'],
            )
        )
    return reservations


DB_CONNECTION = sqlite3.connect('reservations.db')
DB_CONNECTION.row_factory = sqlite3.Row
DB_CURSOR = DB_CONNECTION.cursor()


def add_reservation(reservation: Reservation):
    """Функция записывает данные резерва из объекта класса Reservation в базу данных"""
    with DB_CONNECTION:
        DB_CURSOR.execute(
            "INSERT INTO reservations VALUES (:guest_name, strftime('%Y-%m-%d %H:%M', :date_time), :info, :user_added, :visited)",
            {
                'guest_name': reservation.guest_name,
                'date_time': reservation.date_time,
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
               date_time=strftime('%Y-%m-%d %H:%M', :date_time),
               info=:info,
               visited=:visited
               WHERE rowid = :id""",
            {
                'id': reservation.id,
                'guest_name': reservation.guest_name,
                'date_time': reservation.date_time,
                'info': reservation.info,
                'visited': reservation.visited,
            }
        )


def show_reservations_all():
    """Функция выводит ВСЕ резервы. ДЛЯ ДЕБАГУ"""
    DB_CURSOR.execute(
        "SELECT rowid, * FROM reservations"
    )
    return parse_db_to_reservation_class(DB_CURSOR.fetchall())


def show_reservations_today():
    """Функция выводит строки из бд, где дата соответствует текущей"""
    DB_CURSOR.execute(
        "SELECT rowid, * FROM reservations WHERE date(date_time) = date('now')",
    )
    return parse_db_to_reservation_class(DB_CURSOR.fetchall())

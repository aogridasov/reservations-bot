import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Reservation:
    # Класс для объкетов бронирования
    guest_name: str = None
    date_time: datetime = None
    info: str = None
    user_added: str = None
    visited: bool = False


DB_CONNECTION = sqlite3.connect('reservations.db')
DB_CURSOR = DB_CONNECTION.cursor()


def add_reservation(reservation: Reservation):
    """Функция записывает данные резерва из объекта класса Reservation в базу данных"""
    with DB_CONNECTION:
        DB_CURSOR.execute(
            "INSERT INTO reservations VALUES (:guest_name, :date_time, :info, :user_added, :visited)",
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
    pass


def edit_reservation(reservation: Reservation):
    """Функция находит соответствующую строку в бд и изменяет её"""
    pass


def show_reservations_per_time(time_period):
    """Функция выводит строки из бд, соответствующие указаному временному периоду"""
    DB_CURSOR.execute(
        "SELECT * FROM reservations WHERE date_time=':time_period'",
        {'time_period': time_period}
    )
    return DB_CURSOR.fetchall()

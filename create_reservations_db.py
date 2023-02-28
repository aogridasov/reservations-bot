import sqlite3

conn = sqlite3.connect('reservations.db')
c = conn.cursor()

# создаем таблицу с резервами
c.execute("""CREATE TABLE reservations (
                guest_name text,
                date_time datetime,
                info text,
                user_added text,
                visited integer
                )""")

conn.commit()

# создаем таблицу для хранения id чатов бота
c.execute("""CREATE TABLE chats (
                id integer
                )""")

conn.commit()

conn.close()

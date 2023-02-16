import sqlite3

conn = sqlite3.connect('reservations.db')
c = conn.cursor()
c.execute("""CREATE TABLE reservations (
                guest_name text,
                date_time text,
                info text,
                user_added text,
                visited integer
                )""")

conn.commit()

conn.close()

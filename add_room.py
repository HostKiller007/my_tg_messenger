import sqlite3

def add_room_column():
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()

    # Проверяем, есть ли уже столбец 'room' в таблице 'messages'
    cursor.execute("PRAGMA table_info(messages)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'room' not in columns:
        try:
            # Добавление нового столбца 'room' в таблицу 'messages'
            cursor.execute("ALTER TABLE messages ADD COLUMN room TEXT DEFAULT 'chat'")
            conn.commit()
            print("Столбец 'room' успешно добавлен.")
        except sqlite3.OperationalError as e:
            print(f"Ошибка при добавлении столбца: {e}")
    else:
        print("Столбец 'room' уже существует.")

    conn.close()

# Вызов функции для добавления столбца
add_room_column()

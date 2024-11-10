import sqlite3

def clear_message_history():
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('your_database.db')
        cursor = conn.cursor()

        # Удаляем все записи из таблицы messages
        cursor.execute("DELETE FROM messages")

        # Сохраняем изменения
        conn.commit()
        print("История сообщений успешно очищена.")

    except Exception as e:
        print(f"Ошибка при очистке истории сообщений: {e}")
    
    finally:
        # Закрываем соединение с базой данных
        conn.close()

if __name__ == '__main__':
    clear_message_history()

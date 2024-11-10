import sqlite3

def clear_user_data():
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('your_database.db')
        cursor = conn.cursor()

        # Удаляем все записи из таблицы users
        cursor.execute("DELETE FROM users")

        # Сохраняем изменения
        conn.commit()
        print("Информация о пользователях успешно очищена.")

    except Exception as e:
        print(f"Ошибка при очистке информации о пользователях: {e}")
    
    finally:
        # Закрываем соединение с базой данных
        conn.close()

if __name__ == '__main__':
    clear_user_data()

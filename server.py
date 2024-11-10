from flask import Flask, redirect, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room
import sqlite3
import logging
from cryptography.fernet import Fernet
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

messages = []

logging.basicConfig(level=logging.DEBUG)

# Обработчик для корневого маршрута
@app.route('/')
def home():
    return "server is working"

# Генерация или загрузка ключа шифрования
if not os.path.exists('config.key'):
    key = Fernet.generate_key()
    with open('config.key', 'wb') as f:
        f.write(key)
else:
    with open('config.key', 'rb') as f:
        key = f.read()

cipher_suite = Fernet(key)

# Убедитесь, что база данных и таблицы существуют
def init_db():
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()

    # Создание таблицы пользователей, если не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL
                    )''')
    # Создание таблицы сообщений
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        room TEXT NOT NULL,
                        username TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')
    conn.commit()
    conn.close()

# Регистрация нового пользователя
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Проверка на пустые значения
    if not username or not password:
        return jsonify({"message": "Username and password are required."}), 400

    # Хеширование пароля перед сохранением
    hashed_password = generate_password_hash(password)

    # Проверка на существование пользователя с таким же логином
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        return jsonify({"message": "Username already exists."}), 400
    
    # Добавление пользователя в базу данных
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()
    conn.close()

    return jsonify({"message": "Registration successful!"}), 200

# Логин пользователя
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Username and password are required."}), 400

    user = find_user_by_username(username)

    if user:
        if check_password_hash(user[2], password):  # Проверка пароля
            session['user_id'] = user[0]  # Сохраняем id пользователя в сессию
            return jsonify({"message": "Login successful!"}), 200
        else:
            return jsonify({"message": "Invalid password."}), 401
    else:
        return jsonify({"message": "User not found."}), 404

@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Удаление информации о пользователе из сессии
    return jsonify({"message": "Logged out successfully."}), 200

# Отправка сообщения
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    username = data.get('username')
    message = data.get('message')

    if not username or not message:
        return jsonify({"message": "Username and message are required."}), 400

    # Дешифровка сообщения
    decrypted_message = cipher_suite.decrypt(message.encode()).decode()

    # Запись сообщения в базу данных
    try:
        conn = sqlite3.connect('your_database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (room, username, message) VALUES (?, ?, ?)", ("chat", username, decrypted_message))
        conn.commit()
        conn.close()

        # Подтверждение клиенту с сообщением
        return jsonify({"message": decrypted_message}), 200
    except Exception as e:
        return jsonify({"message": f"Error saving message: {str(e)}"}), 500


# Получение всех сообщений из чата
@app.route('/get_messages', methods=['GET'])
def get_messages():
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, message, timestamp FROM messages WHERE room = ?", ("chat",))
    messages = cursor.fetchall()
    conn.close()

    # Возвращаем все сообщения
    return jsonify(messages), 200


# Обработка сообщения от пользователя через WebSocket
@socketio.on('message')
def handle_message(data):
    # Проверка на наличие необходимых ключей
    if 'username' not in data or 'message' not in data:
        print("Ошибка: данные не содержат 'username' или 'message'.")
        return

    username = data['username']
    encrypted_message = data['message']

    # Расшифровка сообщения
    try:
        decrypted_message = cipher_suite.decrypt(encrypted_message.encode()).decode()
    except Exception as e:
        print(f"Ошибка при расшифровке сообщения: {e}")
        return

    # Логируем полученное сообщение
    print(f"Получено сообщение от {username}: {decrypted_message}")

    # Сохранение сообщения в базе данных
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (room, username, message) VALUES (?, ?, ?)", ('chat', username, decrypted_message))
    conn.commit()
    conn.close()

    # Отправляем ответ клиенту
    emit('message', {'username': username, 'message': decrypted_message})



# Присоединение пользователя к комнате
@socketio.on('join')
def on_join(data):
    username = data.get('username')
    if not username:
        print("Ошибка: username не передан")
        return
    room = data['room']
    join_room(room)
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()
    messages = cursor.execute("SELECT username, message, timestamp FROM messages WHERE room = ?", (room,)).fetchall()
    conn.close()
    
    for msg in messages:
        history_message = f"[{msg[0]} at {msg[2]}]: {msg[1]}"
        emit('message', history_message, room=request.sid)

    emit('message', f"{username} has entered the room.", room=room)

# Функция поиска пользователя по имени
def find_user_by_username(username):
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    return user

def add_room_column():
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()
    try:
        # Добавление нового столбца 'room' в таблицу 'messages'
        cursor.execute("ALTER TABLE messages ADD COLUMN room TEXT DEFAULT 'chat'")
        conn.commit()
        print("Столбец 'room' успешно добавлен.")
    except sqlite3.OperationalError as e:
        print(f"Ошибка при добавлении столбца: {e}")
    finally:
        conn.close()

# Вызов функции для добавления столбца
add_room_column()


if __name__ == '__main__':
    init_db()  # Инициализация базы данных
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

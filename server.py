from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room
import sqlite3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, async_mode=None, cors_allowed_origins="*")

# Генерация или загрузка ключа шифрования
if not os.path.exists('config.key'):
    key = Fernet.generate_key()
    with open('config.key', 'wb') as f:
        f.write(key)
else:
    with open('config.key', 'rb') as f:
        key = f.read()

cipher_suite = Fernet(key)

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('chat.db')
    conn.row_factory = sqlite3.Row
    return conn

# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Создание таблицы пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        sid TEXT
    )''')
    
    # Создание таблицы сообщений
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room TEXT,
        username TEXT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

# Маршрут для регистрации пользователя
@app.route('/register', methods=['POST'])
def register():
    username = request.json.get('username')
    sid = request.headers.get('X-Socket-ID')
    
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (username, sid) VALUES (?, ?)", (username, sid))
        conn.commit()
        return jsonify({"message": "User registered successfully."})
    except sqlite3.IntegrityError:
        return jsonify({"message": "Username already exists."}), 400
    finally:
        conn.close()

# Маршрут для получения истории сообщений
@app.route('/messages', methods=['GET'])
def get_messages():
    room = request.args.get('room')
    conn = get_db_connection()
    messages = conn.execute("SELECT username, message, timestamp FROM messages WHERE room = ?", (room,)).fetchall()
    conn.close()
    
    messages_list = [f"[{row['username']} at {row['timestamp']}]: {row['message']}" for row in messages]
    return jsonify(messages_list)

# Обработка сообщения от пользователя
@socketio.on('message')
def handle_message(data):
    room = data['room']
    username = data['username']
    encrypted_message = data['message']
    
    # Дешифровка сообщения
    try:
        decrypted_message = cipher_suite.decrypt(encrypted_message.encode()).decode()
    except Exception as e:
        print(f"Ошибка расшифровки: {e}")
        return
    
    # Сохранение сообщения в БД
    conn = get_db_connection()
    conn.execute("INSERT INTO messages (room, username, message) VALUES (?, ?, ?)", (room, username, decrypted_message))
    conn.commit()
    conn.close()

    # Рассылка сообщения
    formatted_message = f"[{username}]: {decrypted_message}"
    emit('message', formatted_message, room=room)

# Присоединение пользователя к комнате
@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    emit('message', f"{username} has entered the room.", room=room)

if __name__ == '__main__':
    init_db()  # Инициализация базы данных
    socketio.run(app, host='0.0.0.0', port=5000)

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room
import sqlite3
from cryptography.fernet import Fernet
import os
import json
from database import get_db_connection, init_db
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# Обработчик для корневого маршрута
@app.route('/')
def home():
    return "server is working"

data = {"username": "example_user"}
response = requests.post("http://127.0.0.1:5000/register", json=data)
print(response.status_code)
print(response.json())

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
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        sid TEXT
    )''')
    
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
# Маршрут для регистрации пользователя
# Маршрут для регистрации пользователя
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data received"}), 400

    username = data.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400
    
    # Логика регистрации
    conn = get_db_connection()
    existing_user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if existing_user:
        return jsonify({"error": "Username already taken"}), 400
    
    conn = get_db_connection()
    conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": f"User '{username}' successfully registered."}), 200


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
    
    try:
        # Дешифровка сообщения
        decrypted_message = cipher_suite.decrypt(encrypted_message.encode()).decode()
    except Exception as e:
        print(f"Ошибка расшифровки: {e}")
        return
    
    # Сохранение сообщения в БД
    conn = get_db_connection()
    conn.execute("INSERT INTO messages (room, username, message) VALUES (?, ?, ?)", (room, username, decrypted_message))
    conn.commit()
    conn.close()

    # Рассылка сообщения всем клиентам в комнате
    formatted_message = f"[{username}]: {decrypted_message}"
    emit('message', formatted_message, room=room)

# Присоединение пользователя к комнате
@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    
    # Отправка истории сообщений клиенту, который присоединился
    conn = get_db_connection()
    messages = conn.execute("SELECT username, message, timestamp FROM messages WHERE room = ?", (room,)).fetchall()
    conn.close()
    
    for msg in messages:
        history_message = f"[{msg['username']} at {msg['timestamp']}]: {msg['message']}"
        emit('message', history_message, room=request.sid)  # Отправляем только клиенту, который присоединился

    emit('message', f"{username} has entered the room.", room=room)

if __name__ == '__main__':
    init_db()  # Инициализация базы данных
    app.run(debug=True, host='0.0.0.0', port=5000)

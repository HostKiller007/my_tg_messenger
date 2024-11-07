import json
import socketio
from cryptography.fernet import Fernet

sio = socketio.Client()
chat_log_callback = None  # Глобальная переменная для хранения ссылки на callback
username = None 

# Загрузка ключа из файла конфигурации
def load_config():
    with open("config.json") as config_file:
        return json.load(config_file)

config = load_config()
key = config["CHAT_ENCRYPTION_KEY"].encode()
cipher_suite = Fernet(key)

# Подключение
@sio.event
def connect():
    print("Подключено к серверу.")

@sio.event
def disconnect():
    print("Отключено от сервера.")

# Прием сообщения
@sio.on('message')
def on_message(data):
    print("Новое сообщение:", data)
    if chat_log_callback:
        chat_log_callback(data)  # Обновление GUI при получении сообщения

@sio.event
def history(data):
    # Вывод истории сообщений только для нового участника
    print(f"История сообщений: {data['history']}")

def register(username):
    sio.emit('register', {'username': username})

def join_room(username, room):
    sio.emit('join', {'username': username, 'room': room})

def send_message(room, message):
    global username
    encrypted_message = cipher_suite.encrypt(message.encode())  # Шифрование
    sio.emit('message', {'room': room, 'username': username, 'message': encrypted_message.decode()})

def leave_room(username, room):
    sio.emit('leave', {'username': username, 'room': room})
    sio.disconnect()

def set_chat_log_callback(callback):
    global chat_log_callback
    chat_log_callback = callback

def start_client(username_input, room):
    global username
    username = username_input  # Устанавливаем глобальное имя пользователя

    sio.connect('http://192.168.0.100:5000')

    # После подключения, пользователь автоматически присоединяется к комнате
    join_room(username, room)

import json
import socketio
import requests  # Используем для HTTP-запроса регистрации
from cryptography.fernet import Fernet

sio = socketio.Client()
chat_log_callback = None  # Глобальная переменная для хранения ссылки на callback
username = None 

# Загрузка ключа из файла config.key
with open("config.key", "rb") as key_file:
    key = key_file.read()

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
    try:
        # Дешифровка сообщения
        decrypted_message = cipher_suite.decrypt(data.encode()).decode()
        print("Новое сообщение:", decrypted_message)
        
        if chat_log_callback:
            chat_log_callback(decrypted_message)  # Обновление GUI при получении сообщения
    except Exception as e:
        print(f"Ошибка расшифровки сообщения: {e}")

# Обработка истории сообщений, когда пользователь присоединяется к комнате
@sio.on('history')
def on_history(data):
    for message in data:
        try:
            decrypted_message = cipher_suite.decrypt(message.encode()).decode()
            print("История сообщения:", decrypted_message)
            if chat_log_callback:
                chat_log_callback(decrypted_message)
        except Exception as e:
            print(f"Ошибка расшифровки истории сообщения: {e}")

# Регистрация пользователя на сервере через HTTP запрос
def register(username):
    url = 'http://192.168.0.100:5000/register'
    headers = {'X-Socket-ID': sio.sid}
    response = requests.post(url, json={'username': username}, headers=headers)
    
    if response.status_code == 200:
        print("Пользователь успешно зарегистрирован.")
    else:
        print("Ошибка регистрации пользователя:", response.json().get('message'))

# Присоединение к комнате
def join_room(username, room):
    sio.emit('join', {'username': username, 'room': room})

# Отправка сообщения в комнату
def send_message(room, message):
    global username
    encrypted_message = cipher_suite.encrypt(message.encode())  # Шифрование
    sio.emit('message', {'room': room, 'username': username, 'message': encrypted_message.decode()})

# Отключение пользователя от комнаты
def leave_room(username, room):
    sio.emit('leave', {'username': username, 'room': room})
    sio.disconnect()

# Установка колбэка для обновления чата
def set_chat_log_callback(callback):
    global chat_log_callback
    chat_log_callback = callback

def close_client():
    if sio.connected:
        sio.disconnect()

def start_client(username_input, room):
    global username
    username = username_input
    try:
        sio.connect('http://192.168.0.100:5000')
        register(username)
        join_room(username, room)
    except socketio.exceptions.ConnectionError as e:
        print(f"Ошибка подключения к серверу: {e}")

    # Регистрация пользователя после подключения
    register(username)
    
    # Присоединение к комнате после регистрации
    join_room(username, room)

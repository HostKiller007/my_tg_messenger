import socketio
from cryptography.fernet import Fernet  # Импортируем для шифрования

# Генерация или загрузка ключа шифрования
with open('config.key', 'rb') as f:
    key = f.read()

sio = socketio.Client()
cipher_suite = Fernet(key)

def set_chat_log_callback(callback):
    """ Устанавливаем callback для обработки сообщений чата """
    sio.on('message', callback)

class MessengerClient:
    def __init__(self, nickname, encrypted_message):
        self.nickname = nickname
        self.encrypted_message = encrypted_message
        self.sio = socketio.Client()

        # Подключаем события
        self.sio.on('message', self.handle_message)
        self.sio.on('connect', self.on_connect)

    def send_message(self, message, room=None):
        """ Отправка сообщения на сервер """
        if sio.connected:
            encrypted_message = cipher_suite.encrypt(message.encode()).decode()
            sio.emit('message', {'nickname': self.nickname, 'message': encrypted_message})
        else:
            print("Ошибка: не подключено к серверу.")

    def connect(self):
        """ Подключаемся к серверу """
        print("Подключение к серверу...")
        try:
            sio.connect('http://127.0.0.1:5000')  # Используйте IP-адрес сервера
            sio.emit('join', {'nickname': self.nickname})
        except socketio.exceptions.ConnectionError:
            print("Не удалось подключиться к серверу.")

    def on_connect(self):
        print("Соединение установлено.")
        self.join_room('chat')  # Например, присоединяемся к комнате 'chat'

    def on_disconnect(self):
        """ Вызывается при отключении """
        print("Отключено от сервера.")

    def handle_message(self, data):
        """ Обрабатываем новые сообщения """
        print("Новое сообщение:", data)

    def encrypt_message(self, message):
        """ Шифрование сообщения """
        encrypted_message = cipher_suite.encrypt(message.encode())
        return encrypted_message.decode()  # Возвращаем строку для отправки
    
    def disconnect(self):
        """ Отключение от сервера """
        sio.disconnect()

# Пример использования
if __name__ == "__main__":
    client = MessengerClient(nickname="User", encrypted_message="YourEncryptedMessage")
    client.connect()
    client.send_message(message="Привет, сервер!")


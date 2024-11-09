import socketio
from cryptography.fernet import Fernet  # Импортируем для шифрования

# Генерация ключа шифрования (его можно сохранить и использовать повторно)
key = Fernet.generate_key()
cipher_suite = Fernet(key)  # Создаем объект для шифрования

sio = socketio.Client()

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

    def connect(self):
        """ Подключаемся к серверу """
        print("Подключение к серверу...")
        try:
            self.sio.connect('http://127.0.0.1:5000')  # Используйте IP-адрес сервера
            self.sio.wait()
        except socketio.exceptions.ConnectionError:
            print("Не удалось подключиться к серверу.")
        except KeyboardInterrupt:
            print("Отключение клиента...")
        finally:
            self.sio.disconnect()

    def on_connect(self):
        """ Вызывается при успешном подключении """
        print("Соединение установлено.")
        self.emit_message()

    def on_disconnect(self):
        """ Вызывается при отключении """
        print("Отключено от сервера.")

    def emit_message(self):
        """ Метод для отправки сообщения """
        encrypted_message = self.encrypt_message(self.encrypted_message)
        print(f"Отправка сообщения: {encrypted_message}")
        # Отправляем сообщение в правильной структуре
        self.sio.emit('message', {
            'nickname': self.nickname,  # Отправляем имя пользователя
            'message': encrypted_message # Отправляем зашифрованное сообщение
        })

    def handle_message(self, data):
        """ Обрабатываем новые сообщения """
        print("Новое сообщение:", data)

    def encrypt_message(self, message):
        """ Шифрование сообщения """
        encrypted_message = cipher_suite.encrypt(message.encode())
        return encrypted_message.decode()  # Возвращаем строку для отправки

# Пример использования
if __name__ == "__main__":
    client = MessengerClient(nickname="User", encrypted_message="YourEncryptedMessage")
    client.connect()

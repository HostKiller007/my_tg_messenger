import sqlite3  # Для работы с SQLite
from PyQt5 import QtWidgets
from datetime import datetime
import sys
import json
import os
import requests  # Для HTTP-запросов
from cryptography.fernet import Fernet
from client import sio, set_chat_log_callback  # Убедитесь, что client.py корректно импортирует sio и set_chat_log_callback

# Путь к файлу с данными пользователей
USER_DATA_FILE = "users.json"

# Генерация или загрузка ключа шифрования
if not os.path.exists('config.key'):
    key = Fernet.generate_key()
    with open('config.key', 'wb') as f:
        f.write(key)
else:
    with open('config.key', 'rb') as f:
        key = f.read()

cipher_suite = Fernet(key)

# Главное окно приложения
class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.nickname = ""  # Инициализация никнейма
        self.cipher_suite = cipher_suite  # Инициализация шифровщика

        self.setWindowTitle("Чат")
        self.setGeometry(100, 100, 400, 300)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.stacked_widget = QtWidgets.QStackedWidget()

        # Создание виджетов для разных экранов
        self.login_widget = self.create_login_widget()
        self.registration_widget = self.create_registration_widget()
        self.chat_widget = self.create_chat_widget()

        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.registration_widget)
        self.stacked_widget.addWidget(self.chat_widget)

        self.layout.addWidget(self.stacked_widget)  # Добавляем stacked_widget в layout
        self.setLayout(self.layout)  # Устанавливаем layout для MainWindow

        # Проверка на сохраненный никнейм для автоматического входа
        if os.path.exists("current_user.txt"):
            with open("current_user.txt", 'r') as file:
                saved_nickname = file.read().strip()
                if saved_nickname:  # Если файл содержит никнейм, автоматически заходим в чат
                    self.nickname = saved_nickname
                    self.open_chat(self.nickname)
                else:
                    self.stacked_widget.setCurrentWidget(self.login_widget)  # Показываем экран входа
        else:
            self.stacked_widget.setCurrentWidget(self.login_widget)  # Показываем экран входа

        self.show()

    def create_login_widget(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        self.nickname_label = QtWidgets.QLabel("Никнейм:")
        self.nickname_entry = QtWidgets.QLineEdit()

        self.password_label = QtWidgets.QLabel("Пароль:")
        self.password_entry = QtWidgets.QLineEdit()
        self.password_entry.setEchoMode(QtWidgets.QLineEdit.Password)

        self.remember_checkbox = QtWidgets.QCheckBox("Не выходить из этого ника")

        self.login_button = QtWidgets.QPushButton("Войти")
        self.login_button.clicked.connect(self.login)

        self.register_button = QtWidgets.QPushButton("Зарегистрироваться")
        self.register_button.clicked.connect(self.show_registration)

        layout.addWidget(self.nickname_label)
        layout.addWidget(self.nickname_entry)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_entry)
        layout.addWidget(self.remember_checkbox)
        layout.addWidget(self.login_button)
        layout.addWidget(self.register_button)  # Добавление кнопки регистрации

        widget.setLayout(layout)
        return widget

    def create_registration_widget(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        self.reg_nickname_label = QtWidgets.QLabel("Никнейм:")
        self.reg_nickname_entry = QtWidgets.QLineEdit()

        self.reg_password_label = QtWidgets.QLabel("Пароль:")
        self.reg_password_entry = QtWidgets.QLineEdit()
        self.reg_password_entry.setEchoMode(QtWidgets.QLineEdit.Password)

        self.reg_repeat_password_label = QtWidgets.QLabel("Повторите пароль:")
        self.reg_repeat_password_entry = QtWidgets.QLineEdit()
        self.reg_repeat_password_entry.setEchoMode(QtWidgets.QLineEdit.Password)

        self.register_button = QtWidgets.QPushButton("Зарегистрироваться")
        self.register_button.clicked.connect(self.register)

        self.back_to_login_button = QtWidgets.QPushButton("Назад к входу")
        self.back_to_login_button.clicked.connect(self.show_login)

        layout.addWidget(self.reg_nickname_label)
        layout.addWidget(self.reg_nickname_entry)
        layout.addWidget(self.reg_password_label)
        layout.addWidget(self.reg_password_entry)
        layout.addWidget(self.reg_repeat_password_label)
        layout.addWidget(self.reg_repeat_password_entry)
        layout.addWidget(self.register_button)
        layout.addWidget(self.back_to_login_button)

        widget.setLayout(layout)
        return widget

    def create_chat_widget(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        # Ввод информации о пользователе
        self.user_info_layout = QtWidgets.QHBoxLayout()
        self.user_info_label = QtWidgets.QLabel(f"Пользователь: {self.nickname}")
        self.logout_button = QtWidgets.QPushButton("Выход")
        self.logout_button.clicked.connect(self.confirm_logout)

        self.user_info_layout.addWidget(self.user_info_label)
        self.user_info_layout.addWidget(self.logout_button)

        self.chat_area = QtWidgets.QTextEdit()
        self.chat_area.setReadOnly(True)

        self.message_entry = QtWidgets.QLineEdit()
        self.message_entry.returnPressed.connect(self.send_message)

        self.send_button = QtWidgets.QPushButton("Отправить")
        self.send_button.clicked.connect(self.send_message)

        layout.addLayout(self.user_info_layout)
        layout.addWidget(self.chat_area)
        layout.addWidget(self.message_entry)
        layout.addWidget(self.send_button)

        widget.setLayout(layout)
        return widget

    def show_registration(self):
        self.stacked_widget.setCurrentWidget(self.registration_widget)

    def show_login(self):
        self.stacked_widget.setCurrentWidget(self.login_widget)

    def login(self):
        self.nickname = self.nickname_entry.text().strip()
        password = self.password_entry.text().strip()

        # Отправка запроса на сервер для проверки логина
        response = requests.post('http://localhost:5000/login', json={'username': self.nickname, 'password': password})
        if response.status_code == 200:
            self.open_chat(self.nickname)
        else:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Неправильное имя пользователя или пароль.")

    def register(self):
        username = self.reg_nickname_entry.text().strip()
        password = self.reg_password_entry.text().strip()
        repeat_password = self.reg_repeat_password_entry.text().strip()

        if password != repeat_password:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Пароли не совпадают.")
            return

        # Отправка запроса на сервер для регистрации
        response = requests.post('http://localhost:5000/register', json={'username': username, 'password': password})
        if response.status_code == 200:
            QtWidgets.QMessageBox.information(self, "Успех", "Регистрация прошла успешно!")
            self.show_login()
        else:
            QtWidgets.QMessageBox.warning(self, "Ошибка", response.json()['message'])

    def open_chat(self, nickname):
        self.user_info_label.setText(f"Пользователь: {nickname}")
        self.stacked_widget.setCurrentWidget(self.chat_widget)
        self.load_messages()

        # Подключаемся к чату через client.py
        set_chat_log_callback(self.update_chat_log)

        # Сохранение никнейма, если выбрана опция автологина
        if self.remember_checkbox.isChecked():
            with open("current_user.txt", 'w') as file:
                file.write(nickname)
        else:
            try:
                if os.path.exists("current_user.txt"):
                    os.remove("current_user.txt")
            except PermissionError:
                print("Не удалось удалить файл current_user.txt, так как он используется другой программой.")

    def update_chat_log(self, message):
        print(f"Новое сообщение для {self.nickname}: {message}")

    # Функция для получения сообщений из базы данных
    def get_messages_from_db(self):
        self.create_messages_table()  # Убедитесь, что таблица существует перед запросом
        conn = sqlite3.connect('your_database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT username, message FROM messages ORDER BY timestamp ASC")
        rows = cursor.fetchall()

        messages = []
        for row in rows:
            messages.append({'username': row[0], 'message': row[1]})

        conn.close()
        return messages
    
    def create_messages_table(self):
        conn = sqlite3.connect('your_database.db')  # Путь к вашей базе данных
        cursor = conn.cursor()

        # SQL-запрос для создания таблицы, если её нет
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL,
                            message TEXT NOT NULL,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()

    def load_messages(self):
        messages = self.get_messages_from_db()  # Получаем сообщения из базы данных

        for msg in messages:
            message_text = f"[{msg['username']}] {msg['message']}"
            self.chat_area.append(message_text)

    def send_message(self):
        message = self.message_entry.text()
        if message.strip():
            encrypted_message = self.cipher_suite.encrypt(message.encode())

            if sio.connected:  # Проверяем подключение перед отправкой
                # Отправляем сообщение, если соединение установлено
                sio.emit('message', {'nickname': self.nickname, 'message': encrypted_message})
                self.chat_area.append(f"[{self.nickname}] {message}")
            else:
                # Сообщаем об ошибке подключения
                QtWidgets.QMessageBox.warning(self, "Ошибка подключения", "Не удалось отправить сообщение. Подключитесь к серверу.")
            
            self.message_entry.clear()


    def handle_new_message(data):
        print(f"Новое сообщение: {data['nickname']}: {data['message']}")


    def confirm_logout(self):
        reply = QtWidgets.QMessageBox.question(self, 'Подтверждение выхода',
                                               'Вы уверены, что хотите выйти из чата?',
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.stacked_widget.setCurrentWidget(self.login_widget)

    set_chat_log_callback(handle_new_message)

# Создаем приложение
app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
sys.exit(app.exec_())

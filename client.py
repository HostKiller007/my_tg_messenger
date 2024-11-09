import json
from flask import app, jsonify, request
import socketio
import requests
from cryptography.fernet import Fernet

from database import get_db_connection

sio = socketio.Client()
chat_log_callback = None  # Global variable to store the callback reference

# Load the encryption key from the config file
with open("config.key", "rb") as key_file:
    key = key_file.read()
cipher_suite = Fernet(key)

# Function to save user data for auto-login
def save_user_data(username, password):
    with open("user_data.json", "w") as file:
        json.dump({"username": username, "password": password}, file)

# Function to load saved user data for auto-login
def load_saved_user():
    try:
        with open("user_data.json", "r") as file:
            data = json.load(file)
            return data.get("username"), data.get("password")
    except FileNotFoundError:
        return None, None

# Function to handle incoming messages
@sio.on('message')
def on_message(data):
    try:
        decrypted_message = cipher_suite.decrypt(data.encode()).decode()
        print("Received message:", decrypted_message)
        if chat_log_callback:
            chat_log_callback(decrypted_message)
    except Exception as e:
        print(f"Error decrypting message: {e}")

# Function to handle history messages
@sio.on('history')
def on_history(data):
    print("Received history messages:")
    for message in data:
        try:
            decrypted_message = cipher_suite.decrypt(message.encode()).decode()
            print("History message:", decrypted_message)
            if chat_log_callback:
                chat_log_callback(decrypted_message)
        except Exception as e:
            print(f"Error decrypting history message: {e}")

# Function to register a new user
def register(username, password):
    url = 'http://192.168.0.100:5000/register'
    response = requests.post(url, json={'username': username, 'password': password})
    
    if response.status_code == 200:
        print("User registered successfully.")
        return True
    else:
        print("Error registering user:", response.json().get('message'))
        return False

# Function to login an existing user
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data received"}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    # Check if the user exists
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
    conn.close()
    
    if user:
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 400

# Function to set the chat log callback
def set_chat_log_callback(callback):
    global chat_log_callback
    chat_log_callback = callback

# Function to start the client
def start_client():
    global username, password
    print("Connecting to the server...")
    
    # Load saved user data for auto-login
    username, password = load_saved_user()
    
    if not username or not password:
        print("No saved user data found. Please enter login credentials.")
        # Add code to prompt the user for login credentials via GUI
    
    sio.connect('http://192.168.0.100:5000')  # Connect to the server
    
    # Try to login the user
    if login(username, password):
        # Save the user data for auto-login
        save_user_data(username, password)
    else:
        print("Error logging in user.")

# Run the client
if __name__ == "__main__":
    start_client()
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
from datetime import datetime
import secrets
import hashlib
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*")

# ========== ФАЙЛ ДЛЯ ХРАНЕНИЯ ПОЛЬЗОВАТЕЛЕЙ ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, 'users.txt')

def load_users():
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        username = parts[0]
                        password = parts[1]
                        users[username] = {
                            'password': password,
                            'first_name': username,
                            'last_name': '',
                            'avatar': username[0].upper(),
                            'status': '🟢 Онлайн'
                        }
    return users

def save_user(username, password):
    with open(USERS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{username}|{password}\n")

users = load_users()
user_sessions = {}
messages = {}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShadowChat — Мессенджер</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            height: 100vh;
            overflow: hidden;
            color: #ffffff;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .login-wrapper {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .login-card {
            background: #1a1a1a;
            border-radius: 28px;
            padding: 40px;
            width: 380px;
            max-width: 90%;
            text-align: center;
            border: 1px solid #2a2a2a;
            animation: fadeIn 0.5s ease;
        }
        .login-card h1 {
            font-size: 32px;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #2b9aff 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .login-card input {
            width: 100%;
            padding: 14px 18px;
            margin: 10px 0;
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 50px;
            font-size: 15px;
            color: #ffffff;
        }
        .login-card input:focus { outline: none; border-color: #2b9aff; }
        .login-card button {
            width: 100%;
            padding: 14px;
            background: #2b9aff;
            color: white;
            border: none;
            border-radius: 50px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 15px;
        }
        .switch-auth {
            margin-top: 15px;
            color: #888;
            cursor: pointer;
        }
        .switch-auth span { color: #2b9aff; }
        .error-message { color: #ff4444; font-size: 12px; margin-top: 10px; display: none; }
        
        .chat-app { display: none; height: 100vh; display: flex; }
        .chats-sidebar {
            width: 380px;
            background: #1a1a1a;
            border-right: 1px solid #2a2a2a;
            display: flex;
            flex-direction: column;
        }
        .profile-header {
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid #2a2a2a;
            cursor: pointer;
        }
        .profile-avatar {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #2b9aff 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: bold;
        }
        .profile-info { flex: 1; }
        .profile-name { font-size: 16px; font-weight: bold; }
        .profile-status { font-size: 11px; color: #4caf50; margin-top: 2px; }
        
        .search-section { padding: 12px 16px; border-bottom: 1px solid #2a2a2a; }
        .search-box {
            display: flex;
            gap: 10px;
            background: #2a2a2a;
            border-radius: 50px;
            padding: 8px 16px;
        }
        .search-box input {
            flex: 1;
            background: none;
            border: none;
            color: #ffffff;
            font-size: 14px;
            outline: none;
        }
        .chats-list {
            flex: 1;
            overflow-y: auto;
        }
        .chat-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .chat-item:hover { background: #2a2a2a; }
        .chat-avatar {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #2b9aff 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        .chat-info { flex: 1; }
        .chat-name { font-size: 15px; font-weight: 500; }
        .chat-last-message { font-size: 13px; color: #888; margin-top: 3px; }
        
        .chat-main {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #0a0a0a;
        }
        .chat-header {
            padding: 12px 20px;
            background: #1a1a1a;
            border-bottom: 1px solid #2a2a2a;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .chat-header-avatar {
            width: 42px;
            height: 42px;
            background: linear-gradient(135deg, #2b9aff 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        .chat-header-info { flex: 1; }
        .chat-header-name { font-size: 17px; font-weight: bold; }
        
        .messages-area {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .message {
            display: flex;
            max-width: 70%;
            animation: fadeIn 0.2s ease;
        }
        .message.own { align-self: flex-end; }
        .message.other { align-self: flex-start; }
        .message-bubble {
            padding: 10px 14px;
            border-radius: 18px;
        }
        .message.own .message-bubble {
            background: #2b9aff;
            color: white;
            border-bottom-right-radius: 4px;
        }
        .message.other .message-bubble {
            background: #1a1a1a;
            color: #ffffff;
            border-bottom-left-radius: 4px;
        }
        .message-text { font-size: 14px; }
        .message-time { font-size: 10px; opacity: 0.7; margin-top: 4px; text-align: right; }
        
        .input-area {
            background: #1a1a1a;
            padding: 12px 20px;
            border-top: 1px solid #2a2a2a;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .message-input {
            flex: 1;
            background: #2a2a2a;
            border: none;
            border-radius: 50px;
            padding: 12px 18px;
            color: #ffffff;
            font-size: 14px;
            outline: none;
        }
        .send-btn {
            background: #2b9aff;
            border: none;
            border-radius: 50%;
            width: 44px;
            height: 44px;
            color: white;
            cursor: pointer;
            font-size: 18px;
        }
        
        .fab {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 56px;
            height: 56px;
            background: #2b9aff;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 100;
        }
        .fab i { font-size: 24px; color: white; }
        
        @media (max-width: 768px) {
            .chats-sidebar {
                position: fixed;
                left: 0;
                top: 0;
                height: 100vh;
                transform: translateX(-100%);
                transition: transform 0.3s;
            }
            .chats-sidebar.open { transform: translateX(0); }
            .message { max-width: 85%; }
        }
    </style>
</head>
<body>
    <div class="login-wrapper" id="loginWrapper">
        <div class="login-card">
            <div style="font-size: 60px; margin-bottom: 20px;">✨</div>
            <h1>ShadowChat</h1>
            <p id="authTitle">Вход в аккаунт</p>
            <input type="text" id="loginUsername" placeholder="Юзернейм (мин. 4 символа)">
            <input type="password" id="loginPassword" placeholder="Пароль (мин. 8 символов)">
            <div class="error-message" id="loginError"></div>
            <button id="loginBtn">Войти</button>
            <div class="switch-auth" id="switchAuthBtn">Нет аккаунта? <span>Зарегистрироваться</span></div>
        </div>
    </div>
    
    <div class="chat-app" id="chatApp">
        <div class="chats-sidebar" id="chatsSidebar">
            <div class="profile-header" id="profileBtn">
                <div class="profile-avatar" id="profileAvatar">✨</div>
                <div class="profile-info">
                    <div class="profile-name" id="profileName"></div>
                    <div class="profile-status" id="profileStatus">🟢 Онлайн</div>
                </div>
            </div>
            <div class="search-section">
                <div class="search-box">
                    <input type="text" id="searchChats" placeholder="Поиск...">
                </div>
            </div>
            <div class="chats-list" id="chatsList"></div>
        </div>
        
        <div class="chat-main">
            <div class="chat-header">
                <button id="mobileMenuBtn" style="display: none; background: none; border: none; color: #888; font-size: 24px;">☰</button>
                <div class="chat-header-avatar" id="chatAvatar">💬</div>
                <div class="chat-header-info">
                    <div class="chat-header-name" id="chatName">ShadowChat</div>
                </div>
            </div>
            
            <div class="messages-area" id="messagesArea">
                <div style="text-align: center; color: #888; margin-top: 40px;">✨ Выберите чат из списка слева</div>
            </div>
            
            <div class="input-area" id="inputArea" style="display: none;">
                <input type="text" class="message-input" id="messageInput" placeholder="Сообщение...">
                <button class="send-btn" id="sendBtn">📤</button>
            </div>
        </div>
    </div>
    
    <div class="fab" id="fabBtn" style="display: none;">
        <i class="fas fa-plus"></i>
    </div>
    
    <script>
        const socket = io();
        let currentUser = '';
        let currentChat = null;
        let allUsers = [];
        
        const loginWrapper = document.getElementById('loginWrapper');
        const chatApp = document.getElementById('chatApp');
        const loginUsername = document.getElementById('loginUsername');
        const loginPassword = document.getElementById('loginPassword');
        const loginBtn = document.getElementById('loginBtn');
        const switchAuthBtn = document.getElementById('switchAuthBtn');
        const authTitle = document.getElementById('authTitle');
        const loginError = document.getElementById('loginError');
        const profileName = document.getElementById('profileName');
        const profileAvatar = document.getElementById('profileAvatar');
        const chatsListEl = document.getElementById('chatsList');
        const messagesArea = document.getElementById('messagesArea');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const chatName = document.getElementById('chatName');
        const chatAvatar = document.getElementById('chatAvatar');
        const inputArea = document.getElementById('inputArea');
        const fabBtn = document.getElementById('fabBtn');
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        
        let isLoginMode = true;
        
        switchAuthBtn.onclick = () => {
            isLoginMode = !isLoginMode;
            if (isLoginMode) {
                authTitle.innerText = 'Вход в аккаунт';
                loginBtn.innerText = 'Войти';
                switchAuthBtn.innerHTML = 'Нет аккаунта? <span>Зарегистрироваться</span>';
            } else {
                authTitle.innerText = 'Регистрация';
                loginBtn.innerText = 'Зарегистрироваться';
                switchAuthBtn.innerHTML = 'Уже есть аккаунт? <span>Войти</span>';
            }
            loginError.style.display = 'none';
        };
        
        loginBtn.onclick = () => {
            const username = loginUsername.value.trim();
            const password = loginPassword.value;
            
            if (!isLoginMode) {
                if (username.length < 4) {
                    loginError.innerText = 'Юзернейм должен быть минимум 4 символа';
                    loginError.style.display = 'block';
                    return;
                }
                if (password.length < 8) {
                    loginError.innerText = 'Пароль должен быть минимум 8 символов';
                    loginError.style.display = 'block';
                    return;
                }
                socket.emit('register', { username: username, password: password });
            } else {
                if (!username || !password) {
                    loginError.innerText = 'Заполните все поля';
                    loginError.style.display = 'block';
                    return;
                }
                socket.emit('login', { username: username, password: password });
            }
        };
        
        socket.on('login_success', (data) => {
            currentUser = data.username;
            profileName.innerText = data.username;
            profileAvatar.innerText = data.username.charAt(0).toUpperCase();
            loginWrapper.style.display = 'none';
            chatApp.style.display = 'flex';
            fabBtn.style.display = 'flex';
            loadUsers();
        });
        
        socket.on('register_success', (data) => {
            alert('Аккаунт создан! Теперь войдите');
            isLoginMode = true;
            authTitle.innerText = 'Вход в аккаунт';
            loginBtn.innerText = 'Войти';
            switchAuthBtn.innerHTML = 'Нет аккаунта? <span>Зарегистрироваться</span>';
            loginError.style.display = 'none';
            loginUsername.value = data.username;
            loginPassword.value = '';
        });
        
        socket.on('auth_error', (data) => {
            loginError.innerText = data.error;
            loginError.style.display = 'block';
        });
        
        socket.on('users_list', (data) => {
            allUsers = data.users;
            renderChatsList();
        });
        
        socket.on('new_message', (data) => {
            if (data.chat_id === currentChat) {
                addMessageToChat(data, data.from === currentUser);
            }
        });
        
        function loadUsers() {
            socket.emit('get_users');
        }
        
        function renderChatsList() {
            chatsListEl.innerHTML = '';
            allUsers.forEach(user => {
                if (user !== currentUser) {
                    const div = document.createElement('div');
                    div.className = 'chat-item';
                    div.innerHTML = `
                        <div class="chat-avatar">${user.charAt(0).toUpperCase()}</div>
                        <div class="chat-info">
                            <div class="chat-name">${escapeHtml(user)}</div>
                            <div class="chat-last-message">Нажмите для чата</div>
                        </div>
                    `;
                    div.onclick = () => openChat(user);
                    chatsListEl.appendChild(div);
                }
            });
        }
        
        function openChat(username) {
            currentChat = username;
            chatName.innerText = username;
            chatAvatar.innerText = username.charAt(0).toUpperCase();
            inputArea.style.display = 'flex';
            messageInput.disabled = false;
            messagesArea.innerHTML = '';
            // Здесь будет загрузка истории
        }
        
        function sendMessage() {
            if (!currentChat || !messageInput.value.trim()) return;
            const msg = messageInput.value.trim();
            socket.emit('send_message', { to: currentChat, message: msg });
            addMessageToChat({ from: currentUser, message: msg, time: new Date().toLocaleTimeString() }, true);
            messageInput.value = '';
        }
        
        function addMessageToChat(msg, isOwn) {
            const div = document.createElement('div');
            div.className = `message ${isOwn ? 'own' : 'other'}`;
            div.innerHTML = `
                <div class="message-bubble">
                    <div class="message-text">${escapeHtml(msg.message)}</div>
                    <div class="message-time">${msg.time || new Date().toLocaleTimeString()}</div>
                </div>
            `;
            messagesArea.appendChild(div);
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
        
        sendBtn.onclick = sendMessage;
        
        mobileMenuBtn.onclick = () => {
            document.getElementById('chatsSidebar').classList.toggle('open');
        };
        
        if (window.innerWidth <= 768) {
            mobileMenuBtn.style.display = 'block';
        }
    </script>
</body>
</html>
'''

# ========== СОКЕТ-СОБЫТИЯ ==========
@socketio.on('login')
def handle_login(data):
    username = data['username']
    password = data['password']
    
    if username not in users:
        emit('auth_error', {'error': 'Пользователь не найден'})
        return
    
    if users[username]['password'] != hashlib.md5(password.encode()).hexdigest():
        emit('auth_error', {'error': 'Неверный пароль'})
        return
    
    user_sessions[request.sid] = username
    emit('login_success', {'username': username})

@socketio.on('register')
def handle_register(data):
    username = data['username']
    password = data['password']
    
    if username in users:
        emit('auth_error', {'error': 'Юзернейм уже занят'})
        return
    if len(username) < 4:
        emit('auth_error', {'error': 'Юзернейм должен быть минимум 4 символа'})
        return
    if len(password) < 8:
        emit('auth_error', {'error': 'Пароль должен быть минимум 8 символов'})
        return
    
    password_hash = hashlib.md5(password.encode()).hexdigest()
    users[username] = {
        'password': password_hash,
        'first_name': username,
        'last_name': '',
        'avatar': username[0].upper(),
        'status': '🟢 Онлайн'
    }
    save_user(username, password_hash)
    emit('register_success', {'username': username})

@socketio.on('get_users')
def handle_get_users():
    username = user_sessions.get(request.sid)
    if username:
        users_list = list(users.keys())
        emit('users_list', {'users': users_list})

@socketio.on('send_message')
def handle_send_message(data):
    username = user_sessions.get(request.sid)
    if not username:
        return
    
    to_user = data['to']
    msg_data = {
        'from': username,
        'to': to_user,
        'message': data['message'],
        'time': datetime.now().strftime('%H:%M'),
        'chat_id': to_user
    }
    
    if to_user in user_sessions:
        emit('new_message', msg_data, room=user_sessions[to_user])
    emit('new_message', msg_data, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    username = user_sessions.pop(request.sid, None)
    @app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)

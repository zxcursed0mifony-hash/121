from flask import Flask, render_template_string, request, redirect, url_for, session
from datetime import datetime
import secrets
import hashlib
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

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
                        users[username] = password
    return users

def save_user(username, password):
    with open(USERS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{username}|{password}\n")

users = load_users()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShadowChat — Мессенджер</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            height: 100vh;
            overflow: hidden;
            color: #ffffff;
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
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
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
        .error-message { color: #ff4444; font-size: 12px; margin-top: 10px; display: none; }
        .chat-header { padding: 20px; text-align: center; border-bottom: 1px solid #2a2a2a; }
        .messages-area {
            height: calc(100vh - 120px);
            overflow-y: auto;
            padding: 20px;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px;
            background: #1a1a1a;
            border-radius: 10px;
        }
        .message strong { color: #2b9aff; }
        .message small { color: #888; font-size: 11px; }
        .back-btn {
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: #2b9aff;
            color: white;
            border: none;
            border-radius: 20px;
            padding: 10px 20px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="login-wrapper" id="loginWrapper">
        <div class="login-card">
            <div style="font-size: 60px; margin-bottom: 20px;">✨</div>
            <h1>ShadowChat</h1>
            <p id="authTitle">Вход в аккаунт</p>
            <input type="text" id="username" placeholder="Юзернейм (мин. 4 символа)">
            <input type="password" id="password" placeholder="Пароль (мин. 8 символов)">
            <div class="error-message" id="errorMsg"></div>
            <button id="actionBtn">Войти</button>
            <div style="margin-top: 15px;">
                <span style="color:#888;" id="switchBtn">Нет аккаунта? <span style="color:#2b9aff;cursor:pointer;">Зарегистрироваться</span></span>
            </div>
        </div>
    </div>
    
    <div class="chat-app" id="chatApp" style="display:none;">
        <div class="chat-header">
            <h2>ShadowChat</h2>
            <div id="userName" style="margin-top:5px;color:#2b9aff;"></div>
        </div>
        <div id="usersList" style="padding:10px;border-bottom:1px solid #2a2a2a;">
            <h4>Пользователи онлайн:</h4>
            <div id="onlineUsers"></div>
        </div>
        <div class="messages-area" id="messagesArea"></div>
        <div class="input-area" style="position:fixed;bottom:0;left:0;right:0;background:#1a1a1a;padding:15px;display:flex;gap:10px;">
            <input type="text" id="messageInput" placeholder="Введите сообщение..." style="flex:1;padding:12px;background:#2a2a2a;border:none;border-radius:25px;color:white;">
            <button id="sendBtn" style="padding:12px 25px;background:#2b9aff;border:none;border-radius:25px;color:white;cursor:pointer;">Отправить</button>
        </div>
        <button class="back-btn" id="logoutBtn">🚪 Выйти</button>
    </div>
    
    <script>
        let currentUser = '';
        let currentChat = null;
        let messages = {};
        
        const loginWrapper = document.getElementById('loginWrapper');
        const chatApp = document.getElementById('chatApp');
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        const actionBtn = document.getElementById('actionBtn');
        const errorMsg = document.getElementById('errorMsg');
        const authTitle = document.getElementById('authTitle');
        const switchBtn = document.getElementById('switchBtn');
        const userNameSpan = document.getElementById('userName');
        const onlineUsersDiv = document.getElementById('onlineUsers');
        const messagesArea = document.getElementById('messagesArea');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const logoutBtn = document.getElementById('logoutBtn');
        
        let isLogin = true;
        
        switchBtn.onclick = () => {
            isLogin = !isLogin;
            if (isLogin) {
                authTitle.innerText = 'Вход в аккаунт';
                actionBtn.innerText = 'Войти';
                switchBtn.innerHTML = 'Нет аккаунта? <span style="color:#2b9aff;cursor:pointer;">Зарегистрироваться</span>';
            } else {
                authTitle.innerText = 'Регистрация';
                actionBtn.innerText = 'Зарегистрироваться';
                switchBtn.innerHTML = 'Уже есть аккаунт? <span style="color:#2b9aff;cursor:pointer;">Войти</span>';
            }
            errorMsg.style.display = 'none';
        };
        
        actionBtn.onclick = async () => {
            const username = usernameInput.value.trim();
            const password = passwordInput.value.trim();
            
            if (!username || !password) {
                errorMsg.innerText = 'Заполните все поля';
                errorMsg.style.display = 'block';
                return;
            }
            
            if (!isLogin && username.length < 4) {
                errorMsg.innerText = 'Юзернейм должен быть минимум 4 символа';
                errorMsg.style.display = 'block';
                return;
            }
            
            if (!isLogin && password.length < 8) {
                errorMsg.innerText = 'Пароль должен быть минимум 8 символов';
                errorMsg.style.display = 'block';
                return;
            }
            
            const response = await fetch(isLogin ? '/login' : '/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                currentUser = username;
                userNameSpan.innerText = currentUser;
                loginWrapper.style.display = 'none';
                chatApp.style.display = 'flex';
                loadUsers();
                loadMessages();
                startPolling();
            } else {
                errorMsg.innerText = data.error;
                errorMsg.style.display = 'block';
            }
        };
        
        async function loadUsers() {
            const response = await fetch('/get_users');
            const data = await response.json();
            onlineUsersDiv.innerHTML = data.users.filter(u => u !== currentUser).map(u => 
                `<div style="padding:8px;cursor:pointer;border-bottom:1px solid #2a2a2a;" onclick="openChat('${u}')">👤 ${u}</div>`
            ).join('');
        }
        
        function openChat(user) {
            currentChat = user;
            const msgs = messages[currentChat] || [];
            messagesArea.innerHTML = msgs.map(msg => 
                `<div class="message">
                    <strong>${msg.from === currentUser ? 'Я' : msg.from}:</strong> ${msg.message}
                    <br><small>${msg.time}</small>
                </div>`
            ).join('');
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }
        
        async function sendMessage() {
            const text = messageInput.value.trim();
            if (!text || !currentChat) return;
            
            const response = await fetch('/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ to: currentChat, message: text })
            });
            
            const data = await response.json();
            if (data.success) {
                if (!messages[currentChat]) messages[currentChat] = [];
                messages[currentChat].push({
                    from: currentUser,
                    message: text,
                    time: new Date().toLocaleTimeString()
                });
                openChat(currentChat);
                messageInput.value = '';
            }
        }
        
        async function loadMessages() {
            const response = await fetch('/get_messages');
            const data = await response.json();
            messages = data.messages;
            if (currentChat) openChat(currentChat);
        }
        
        function startPolling() {
            setInterval(async () => {
                await loadMessages();
                await loadUsers();
            }, 2000);
        }
        
        sendBtn.onclick = sendMessage;
        messageInput.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
        
        logoutBtn.onclick = async () => {
            await fetch('/logout');
            location.reload();
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username in users:
        return {'success': False, 'error': 'Юзернейм уже занят'}
    if len(username) < 4:
        return {'success': False, 'error': 'Юзернейм минимум 4 символа'}
    if len(password) < 8:
        return {'success': False, 'error': 'Пароль минимум 8 символов'}
    
    password_hash = hashlib.md5(password.encode()).hexdigest()
    users[username] = password_hash
    save_user(username, password_hash)
    return {'success': True}

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username not in users:
        return {'success': False, 'error': 'Пользователь не найден'}
    
    if users[username] != hashlib.md5(password.encode()).hexdigest():
        return {'success': False, 'error': 'Неверный пароль'}
    
    session['username'] = username
    return {'success': True}

@app.route('/get_users')
def get_users():
    if 'username' not in session:
        return {'users': []}
    return {'users': list(users.keys())}

# Хранилище сообщений (в памяти, для простоты)
messages_storage = {}

@app.route('/send', methods=['POST'])
def send_message():
    if 'username' not in session:
        return {'success': False}
    
    data = request.get_json()
    to_user = data.get('to')
    message = data.get('message')
    from_user = session['username']
    
    key = tuple(sorted([from_user, to_user]))
    if key not in messages_storage:
        messages_storage[key] = []
    
    messages_storage[key].append({
        'from': from_user,
        'to': to_user,
        'message': message,
        'time': datetime.now().strftime('%H:%M')
    })
    
    return {'success': True}

@app.route('/get_messages')
def get_messages():
    if 'username' not in session:
        return {'messages': {}}
    
    current_user = session['username']
    result = {}
    
    for key, msgs in messages_storage.items():
        if current_user in key:
            result[key[0] if key[1] == current_user else key[1]] = msgs
    
    return {'messages': result}

@app.route('/logout')
def logout():
    session.pop('username', None)
    return {'success': True}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import secrets
import hashlib
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*")

# ========== ФАЙЛ ДЛЯ СОХРАНЕНИЯ ПОЛЬЗОВАТЕЛЕЙ ==========
USERS_FILE = 'users.json'

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users():
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

users = load_users()
user_sessions = {}
messages = {}
groups = {}
channels = {}
user_chats = {}  # username -> список созданных чатов

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>ShadowChat — как Telegram</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            height: 100vh;
            overflow: hidden;
            color: var(--text);
        }
        body.dark {
            --bg: #0a0a0a;
            --bg2: #1a1a1a;
            --bg3: #2a2a2a;
            --text: #ffffff;
            --text2: #8e8e8e;
            --accent: #2b9aff;
            --border: #2a2a2a;
            --danger: #ff4444;
            --success: #4caf50;
            --warning: #ff9800;
        }
        body.light {
            --bg: #ffffff;
            --bg2: #f0f0f0;
            --bg3: #e0e0e0;
            --text: #000000;
            --text2: #5e5e5e;
            --accent: #0088cc;
            --border: #d0d0d0;
        }
        body.blue {
            --bg: #0a1929;
            --bg2: #132f4c;
            --bg3: #1a3d5c;
            --text: #ffffff;
            --accent: #2196f3;
        }
        body.green {
            --bg: #0a2e1a;
            --bg2: #0d3d22;
            --bg3: #12502c;
            --accent: #4caf50;
        }
        body.purple {
            --bg: #1a0a2e;
            --bg2: #2d1b4e;
            --bg3: #3d2568;
            --accent: #9c27b0;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes bounce {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        .login-wrapper {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, var(--bg) 0%, var(--bg2) 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .login-card {
            background: var(--bg2);
            border-radius: 28px;
            padding: 40px;
            width: 380px;
            max-width: 90%;
            text-align: center;
            border: 1px solid var(--border);
            animation: fadeIn 0.5s ease;
        }
        .login-card h1 {
            font-size: 32px;
            margin-bottom: 10px;
            background: linear-gradient(135deg, var(--accent) 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .login-card input {
            width: 100%;
            padding: 14px 18px;
            margin: 10px 0;
            background: var(--bg3);
            border: 1px solid var(--border);
            border-radius: 50px;
            font-size: 15px;
            color: var(--text);
        }
        .login-card input:focus { outline: none; border-color: var(--accent); }
        .login-card button {
            width: 100%;
            padding: 14px;
            background: var(--accent);
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
            color: var(--text2);
            cursor: pointer;
        }
        .switch-auth span { color: var(--accent); }
        .error-message { color: var(--danger); font-size: 12px; margin-top: 10px; display: none; }
        
        .chat-app { display: none; height: 100vh; display: flex; }
        .chats-sidebar {
            width: 380px;
            background: var(--bg2);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }
        .profile-header {
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            border-bottom: 1px solid var(--border);
        }
        .profile-avatar {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--accent) 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: bold;
        }
        .profile-info { flex: 1; }
        .profile-name { font-size: 16px; font-weight: bold; }
        .profile-username { font-size: 12px; color: var(--text2); }
        .profile-status { font-size: 11px; color: var(--success); margin-top: 2px; }
        .edit-profile { background: none; border: none; color: var(--text2); font-size: 20px; cursor: pointer; padding: 8px; }
        .search-section { padding: 12px 16px; border-bottom: 1px solid var(--border); }
        .search-box {
            display: flex;
            gap: 10px;
            background: var(--bg3);
            border-radius: 50px;
            padding: 8px 16px;
        }
        .search-box input {
            flex: 1;
            background: none;
            border: none;
            color: var(--text);
            font-size: 14px;
            outline: none;
        }
        .chats-list {
            flex: 1;
            overflow-y: auto;
            padding-bottom: 80px;
        }
        .chat-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            cursor: pointer;
            transition: background 0.2s;
            border-left: 3px solid transparent;
        }
        .chat-item:hover { background: var(--bg3); }
        .chat-item.active {
            background: var(--bg3);
            border-left-color: var(--accent);
        }
        .chat-avatar {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, var(--accent) 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            position: relative;
        }
        .chat-avatar.group { border-radius: 20px; }
        .chat-avatar.channel { border-radius: 20px; background: var(--warning); }
        .online-dot {
            position: absolute;
            bottom: 2px;
            right: 2px;
            width: 12px;
            height: 12px;
            background: var(--success);
            border-radius: 50%;
            border: 2px solid var(--bg2);
        }
        .chat-info { flex: 1; }
        .chat-name { font-size: 15px; font-weight: 500; }
        .chat-username { font-size: 11px; color: var(--text2); }
        .chat-last-message { font-size: 13px; color: var(--text2); margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .chat-meta { text-align: right; }
        .chat-time { font-size: 11px; color: var(--text2); }
        .chat-unread {
            background: var(--accent);
            color: white;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 50px;
            margin-top: 4px;
        }
        
        .chat-main {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg);
        }
        .chat-header {
            padding: 12px 20px;
            background: var(--bg2);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .chat-header-avatar {
            width: 42px;
            height: 42px;
            background: linear-gradient(135deg, var(--accent) 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        .chat-header-info { flex: 1; }
        .chat-header-name { font-size: 17px; font-weight: bold; }
        .chat-header-username { font-size: 12px; color: var(--text2); }
        .chat-header-status { font-size: 11px; color: var(--success); margin-top: 2px; }
        .chat-header-actions { display: flex; gap: 8px; }
        .chat-header-actions button {
            background: none;
            border: none;
            color: var(--text2);
            font-size: 18px;
            cursor: pointer;
            padding: 8px;
            border-radius: 50%;
        }
        .chat-header-actions button:hover { background: var(--bg3); }
        
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
            background: var(--accent);
            color: white;
            border-bottom-right-radius: 4px;
        }
        .message.other .message-bubble {
            background: var(--bg2);
            color: var(--text);
            border-bottom-left-radius: 4px;
        }
        .message-text { font-size: 14px; line-height: 1.4; }
        .message-time {
            font-size: 10px;
            opacity: 0.7;
            margin-top: 4px;
            text-align: right;
        }
        .typing-indicator {
            padding: 8px 20px;
            font-size: 12px;
            color: var(--text2);
            font-style: italic;
            min-height: 36px;
        }
        .input-area {
            background: var(--bg2);
            padding: 12px 20px;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .message-input {
            flex: 1;
            background: var(--bg3);
            border: none;
            border-radius: 50px;
            padding: 12px 18px;
            color: var(--text);
            font-size: 14px;
            outline: none;
        }
        .send-btn {
            background: var(--accent);
            border: none;
            border-radius: 50%;
            width: 44px;
            height: 44px;
            color: white;
            cursor: pointer;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .fab {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 56px;
            height: 56px;
            background: var(--accent);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: all 0.2s;
            z-index: 100;
            animation: bounce 0.5s ease;
        }
        .fab:hover { transform: scale(1.05); }
        .fab i { font-size: 24px; color: white; }
        .fab.hide { display: none; }
        
        .fab-menu {
            position: fixed;
            bottom: 90px;
            right: 24px;
            background: var(--bg2);
            border-radius: 20px;
            padding: 12px 0;
            min-width: 200px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 99;
            display: none;
            border: 1px solid var(--border);
        }
        .fab-menu.show { display: block; animation: fadeIn 0.2s ease; }
        .fab-menu-item {
            padding: 14px 20px;
            display: flex;
            align-items: center;
            gap: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .fab-menu-item:hover { background: var(--bg3); }
        .fab-menu-item i { width: 24px; font-size: 18px; color: var(--accent); }
        .fab-menu-item span { font-size: 14px; }
        
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2000;
        }
        .modal-content {
            background: var(--bg2);
            border-radius: 20px;
            width: 450px;
            max-width: 90%;
            max-height: 85vh;
            overflow-y: auto;
            animation: fadeIn 0.3s ease;
        }
        .modal-header {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-body { padding: 20px; }
        .modal-footer {
            padding: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: flex-end;
            gap: 12px;
        }
        .modal-footer button {
            padding: 10px 20px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
        }
        .modal-footer .save { background: var(--accent); color: white; }
        .modal-footer .cancel { background: var(--bg3); color: var(--text); }
        
        .settings-item {
            padding: 14px 0;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }
        .theme-option {
            padding: 12px;
            margin: 8px 0;
            border-radius: 12px;
            cursor: pointer;
            border: 1px solid var(--border);
        }
        .theme-option.selected { border-color: var(--accent); background: var(--bg3); }
        .user-search-result {
            padding: 12px;
            margin: 8px 0;
            background: var(--bg3);
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
        }
        .user-not-found { text-align: center; padding: 20px; color: var(--text2); }
        .notification {
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px 18px;
            max-width: 350px;
            z-index: 1500;
            animation: fadeIn 0.3s ease;
        }
        
        @media (max-width: 768px) {
            .chats-sidebar {
                position: fixed;
                left: 0;
                top: 0;
                height: 100vh;
                z-index: 100;
                transform: translateX(-100%);
                transition: transform 0.3s;
            }
            .chats-sidebar.open { transform: translateX(0); }
            .message { max-width: 85%; }
        }
    </style>
</head>
<body class="dark">
    <div class="login-wrapper" id="loginWrapper">
        <div class="login-card">
            <div style="font-size: 60px; margin-bottom: 20px;">✨</div>
            <h1>ShadowChat</h1>
            <p>Вход в аккаунт</p>
            <input type="text" id="loginUsername" placeholder="Юзернейм">
            <input type="password" id="loginPassword" placeholder="Пароль">
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
                    <div class="profile-username" id="profileUsername"></div>
                    <div class="profile-status" id="profileStatus">🟢 Онлайн</div>
                </div>
                <button class="edit-profile" id="openSettingsBtn">⚙️</button>
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
                <button id="mobileMenuBtn" style="display: none; background: none; border: none; color: var(--text2); font-size: 24px; cursor: pointer;">☰</button>
                <div class="chat-header-avatar" id="chatAvatar">💬</div>
                <div class="chat-header-info">
                    <div class="chat-header-name" id="chatName">ShadowChat</div>
                    <div class="chat-header-username" id="chatUsername"></div>
                    <div class="chat-header-status" id="chatStatus">Выберите чат</div>
                </div>
                <div class="chat-header-actions" id="chatActions" style="display: none;">
                    <button id="chatInfoBtn" title="Инфо">ℹ️</button>
                    <button id="archiveChatBtn" title="Архивировать">📦</button>
                    <button id="deleteChatBtn" title="Удалить/Выйти">🗑️</button>
                </div>
            </div>
            
            <div class="messages-area" id="messagesArea">
                <div style="text-align: center; color: var(--text2); margin-top: 40px;">
                    ✨ ShadowChat<br>Выберите чат из списка слева
                </div>
            </div>
            
            <div class="typing-indicator" id="typingIndicator"></div>
            
            <div class="input-area" id="inputArea" style="display: none;">
                <input type="text" class="message-input" id="messageInput" placeholder="Сообщение...">
                <button class="send-btn" id="sendBtn">📤</button>
            </div>
        </div>
    </div>
    
    <div class="fab" id="fabBtn">
        <i class="fas fa-plus"></i>
    </div>
    <div class="fab-menu" id="fabMenu">
        <div class="fab-menu-item" id="newPrivateChatBtn">
            <i class="fas fa-user-plus"></i>
            <span>Новый чат</span>
        </div>
        <div class="fab-menu-item" id="newGroupBtn">
            <i class="fas fa-users"></i>
            <span>Создать группу</span>
        </div>
        <div class="fab-menu-item" id="newChannelBtn">
            <i class="fas fa-broadcast-tower"></i>
            <span>Создать канал</span>
        </div>
    </div>
    
    <div class="modal" id="profileModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Настройки профиля</h3>
                <button onclick="closeModal('profileModal')" style="background: none; border: none; font-size: 24px; cursor: pointer;">✕</button>
            </div>
            <div class="modal-body">
                <div style="text-align: center; margin-bottom: 20px;">
                    <div class="profile-avatar" id="modalAvatar" style="width: 80px; height: 80px; font-size: 32px; margin: 0 auto;">✨</div>
                </div>
                <label>Ваше имя</label>
                <input type="text" id="editFirstName" placeholder="Имя" style="margin-bottom: 16px; width: 100%; padding: 12px; border-radius: 10px; background: var(--bg3); border: 1px solid var(--border); color: var(--text);">
                <label>Фамилия</label>
                <input type="text" id="editLastName" placeholder="Фамилия" style="margin-bottom: 16px; width: 100%; padding: 12px; border-radius: 10px; background: var(--bg3); border: 1px solid var(--border); color: var(--text);">
                <label>Юзернейм (@username)</label>
                <input type="text" id="editUsername" placeholder="@username" style="margin-bottom: 16px; width: 100%; padding: 12px; border-radius: 10px; background: var(--bg3); border: 1px solid var(--border); color: var(--text);">
                <label>Статус</label>
                <input type="text" id="editStatus" placeholder="Статус..." style="margin-bottom: 16px; width: 100%; padding: 12px; border-radius: 10px; background: var(--bg3); border: 1px solid var(--border); color: var(--text);">
                <label>О себе</label>
                <textarea id="editBio" rows="3" style="width: 100%; padding: 12px; border-radius: 10px; background: var(--bg3); border: 1px solid var(--border); color: var(--text);"></textarea>
            </div>
            <div class="modal-footer">
                <button class="cancel" onclick="closeModal('profileModal')">Отмена</button>
                <button class="save" id="saveProfileBtn">Сохранить</button>
            </div>
        </div>
    </div>
    
    <div class="modal" id="settingsModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Настройки</h3>
                <button onclick="closeModal('settingsModal')" style="background: none; border: none; font-size: 24px; cursor: pointer;">✕</button>
            </div>
            <div class="modal-body">
                <div class="settings-item" id="themeSettingsBtn">
                    <span>🎨 Тема оформления</span>
                    <span id="currentThemeName">Тёмная</span>
                </div>
                <div class="settings-item" id="logoutBtn">
                    <span style="color: var(--danger);">🚪 Выйти из аккаунта</span>
                </div>
            </div>
        </div>
    </div>
    
    <div class="modal" id="themeModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Выберите тему</h3>
                <button onclick="closeModal('themeModal')" style="background: none; border: none; font-size: 24px; cursor: pointer;">✕</button>
            </div>
            <div class="modal-body" id="themeList"></div>
        </div>
    </div>
    
    <div class="modal" id="newChatModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="newModalTitle">Новый чат</h3>
                <button onclick="closeModal('newChatModal')" style="background: none; border: none; font-size: 24px; cursor: pointer;">✕</button>
            </div>
            <div class="modal-body" id="newModalBody"></div>
        </div>
    </div>
    
    <div class="modal" id="chatInfoModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="infoTitle">Информация</h3>
                <button onclick="closeModal('chatInfoModal')" style="background: none; border: none; font-size: 24px; cursor: pointer;">✕</button>
            </div>
            <div class="modal-body" id="infoBody"></div>
            <div class="modal-footer">
                <button class="cancel" onclick="closeModal('chatInfoModal')">Закрыть</button>
            </div>
        </div>
    </div>
    
    <div class="modal" id="searchUsersModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Поиск пользователей</h3>
                <button onclick="closeModal('searchUsersModal')" style="background: none; border: none; font-size: 24px; cursor: pointer;">✕</button>
            </div>
            <div class="modal-body">
                <input type="text" id="globalSearchInput" placeholder="Введите имя или @username" style="width: 100%; padding: 12px; border-radius: 10px; background: var(--bg3); border: 1px solid var(--border); color: var(--text);">
                <div id="globalSearchResults" style="margin-top: 16px;"></div>
            </div>
        </div>
    </div>
    
    <script>
        const socket = io();
        let currentUser = '';
        let currentChat = null;
        let currentChatType = null;
        let currentTheme = localStorage.getItem('shadowchat_theme') || 'dark';
        let typingTimeout;
        let allUsers = [];
        let allUsersData = {};
        let chatsList = [];
        let groupsList = [];
        let channelsList = [];
        
        const loginWrapper = document.getElementById('loginWrapper');
        const chatApp = document.getElementById('chatApp');
        const loginUsername = document.getElementById('loginUsername');
        const loginPassword = document.getElementById('loginPassword');
        const loginBtn = document.getElementById('loginBtn');
        const switchAuthBtn = document.getElementById('switchAuthBtn');
        const loginError = document.getElementById('loginError');
        const profileName = document.getElementById('profileName');
        const profileUsername = document.getElementById('profileUsername');
        const profileAvatar = document.getElementById('profileAvatar');
        const profileBtn = document.getElementById('profileBtn');
        const openSettingsBtn = document.getElementById('openSettingsBtn');
        const chatsListEl = document.getElementById('chatsList');
        const messagesArea = document.getElementById('messagesArea');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const chatName = document.getElementById('chatName');
        const chatUsername = document.getElementById('chatUsername');
        const chatAvatar = document.getElementById('chatAvatar');
        const chatStatus = document.getElementById('chatStatus');
        const chatActions = document.getElementById('chatActions');
        const inputArea = document.getElementById('inputArea');
        const typingIndicator = document.getElementById('typingIndicator');
        const searchChats = document.getElementById('searchChats');
        const archiveChatBtn = document.getElementById('archiveChatBtn');
        const deleteChatBtn = document.getElementById('deleteChatBtn');
        const chatInfoBtn = document.getElementById('chatInfoBtn');
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        
        const fabBtn = document.getElementById('fabBtn');
        const fabMenu = document.getElementById('fabMenu');
        const newPrivateChatBtn = document.getElementById('newPrivateChatBtn');
        const newGroupBtn = document.getElementById('newGroupBtn');
        const newChannelBtn = document.getElementById('newChannelBtn');
        
        let isLoginMode = true;
        
        const themes = {
            dark: { name: '🌙 Тёмная' },
            light: { name: '☀️ Светлая' },
            blue: { name: '💙 Синяя' },
            green: { name: '💚 Зелёная' },
            purple: { name: '💜 Фиолетовая' }
        };
        
        function setTheme(theme) {
            currentTheme = theme;
            document.body.className = theme;
            localStorage.setItem('shadowchat_theme', theme);
            document.getElementById('currentThemeName').innerText = themes[theme].name;
        }
        
        function renderThemeList() {
            const themeList = document.getElementById('themeList');
            themeList.innerHTML = '';
            for (const [key, theme] of Object.entries(themes)) {
                const div = document.createElement('div');
                div.className = `theme-option ${currentTheme === key ? 'selected' : ''}`;
                div.innerHTML = theme.name;
                div.onclick = () => { setTheme(key); closeModal('themeModal'); };
                themeList.appendChild(div);
            }
            openModal('themeModal');
        }
        
        function openModal(id) { document.getElementById(id).style.display = 'flex'; }
        function closeModal(id) { document.getElementById(id).style.display = 'none'; }
        
        function showNotification(title, message) {
            const notif = document.createElement('div');
            notif.className = 'notification';
            notif.innerHTML = `<strong>${escapeHtml(title)}</strong><br>${escapeHtml(message)}`;
            document.body.appendChild(notif);
            setTimeout(() => notif.remove(), 4000);
        }
        
        function updateFabVisibility() {
            if (currentChat) {
                fabBtn.classList.add('hide');
            } else {
                fabBtn.classList.remove('hide');
            }
        }
        
        // Закрыть чат по ESC
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && currentChat) {
                closeChat();
            }
        });
        
        function closeChat() {
            currentChat = null;
            currentChatType = null;
            chatName.innerText = 'ShadowChat';
            chatUsername.innerText = '';
            chatAvatar.innerText = '💬';
            chatStatus.innerText = 'Выберите чат';
            messagesArea.innerHTML = '<div style="text-align: center; color: var(--text2); margin-top: 40px;">✨ Выберите чат из списка слева</div>';
            messageInput.disabled = true;
            inputArea.style.display = 'none';
            chatActions.style.display = 'none';
            updateFabVisibility();
            renderChatsList();
        }
        
        fabBtn.onclick = () => {
            fabMenu.classList.toggle('show');
        };
        
        document.addEventListener('click', (e) => {
            if (!fabBtn.contains(e.target) && !fabMenu.contains(e.target)) {
                fabMenu.classList.remove('show');
            }
        });
        
        newPrivateChatBtn.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('newModalTitle').innerText = 'Новый чат';
            document.getElementById('newModalBody').innerHTML = `
                <input type="text" id="chatUsername" placeholder="@username пользователя" style="width: 100%; padding: 12px; margin-bottom: 16px; background: var(--bg3); border: 1px solid var(--border); border-radius: 10px; color: var(--text);">
                <button onclick="createChat()" style="width: 100%; padding: 12px; background: var(--accent); border: none; border-radius: 10px; color: white; cursor: pointer;">Начать чат</button>
            `;
            openModal('newChatModal');
        };
        
        newGroupBtn.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('newModalTitle').innerText = 'Создать группу';
            document.getElementById('newModalBody').innerHTML = `
                <input type="text" id="groupName" placeholder="Название группы" style="width: 100%; padding: 12px; margin-bottom: 12px; background: var(--bg3); border: 1px solid var(--border); border-radius: 10px; color: var(--text);">
                <textarea id="groupDesc" placeholder="Описание группы" rows="2" style="width: 100%; padding: 12px; margin-bottom: 16px; background: var(--bg3); border: 1px solid var(--border); border-radius: 10px; color: var(--text);"></textarea>
                <button onclick="createGroup()" style="width: 100%; padding: 12px; background: var(--accent); border: none; border-radius: 10px; color: white; cursor: pointer;">Создать группу</button>
            `;
            openModal('newChatModal');
        };
        
        newChannelBtn.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('newModalTitle').innerText = 'Создать канал';
            document.getElementById('newModalBody').innerHTML = `
                <input type="text" id="channelName" placeholder="Название канала" style="width: 100%; padding: 12px; margin-bottom: 12px; background: var(--bg3); border: 1px solid var(--border); border-radius: 10px; color: var(--text);">
                <textarea id="channelDesc" placeholder="Описание канала" rows="2" style="width: 100%; padding: 12px; margin-bottom: 12px; background: var(--bg3); border: 1px solid var(--border); border-radius: 10px; color: var(--text);"></textarea>
                <label style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
                    <input type="checkbox" id="channelPublic"> Публичный канал (все могут найти)
                </label>
                <button onclick="createChannel()" style="width: 100%; padding: 12px; background: var(--accent); border: none; border-radius: 10px; color: white; cursor: pointer;">Создать канал</button>
            `;
            openModal('newChatModal');
        };
        
        switchAuthBtn.onclick = () => {
            isLoginMode = !isLoginMode;
            if (isLoginMode) {
                loginBtn.innerText = 'Войти';
                switchAuthBtn.innerHTML = 'Нет аккаунта? <span>Зарегистрироваться</span>';
                loginError.style.display = 'none';
                loginPassword.value = '';
            } else {
                loginBtn.innerText = 'Зарегистрироваться';
                switchAuthBtn.innerHTML = 'Уже есть аккаунт? <span>Войти</span>';
                loginError.style.display = 'none';
            }
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
            profileName.innerText = data.first_name + ' ' + (data.last_name || '');
            profileUsername.innerText = '@' + data.username;
            profileAvatar.innerText = data.first_name?.charAt(0) || '✨';
            document.getElementById('modalAvatar').innerText = data.first_name?.charAt(0) || '✨';
            loginWrapper.style.display = 'none';
            chatApp.style.display = 'flex';
            updateFabVisibility();
            loadUsers();
            loadChats();
            loadUserData();
            if (Notification.permission === 'default') Notification.requestPermission();
        });
        
        socket.on('register_success', (data) => {
            showNotification('Успех', 'Аккаунт создан! Теперь войдите');
            isLoginMode = true;
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
        
        function loadUsers() { socket.emit('get_users'); }
        function loadChats() { socket.emit('get_chats'); }
        function loadUserData() { socket.emit('get_user_data'); }
        
        socket.on('users_list', (data) => {
            allUsers = data.users;
            allUsersData = data.users_data || {};
        });
        
        socket.on('chats_list', (data) => {
            chatsList = data.chats || [];
            groupsList = data.groups || [];
            channelsList = data.channels || [];
            renderChatsList();
        });
        
        socket.on('user_data', (data) => {
            document.getElementById('editFirstName').value = data.first_name || '';
            document.getElementById('editLastName').value = data.last_name || '';
            document.getElementById('editUsername').value = data.username || currentUser;
            document.getElementById('editStatus').value = data.status || '';
            document.getElementById('editBio').value = data.bio || '';
            profileName.innerText = (data.first_name || '') + ' ' + (data.last_name || '');
            profileUsername.innerText = '@' + (data.username || currentUser);
            if (data.status) document.getElementById('profileStatus').innerHTML = data.status;
        });
        
        socket.on('chat_history', (data) => {
            if (data.chat_id === currentChat) {
                renderMessages(data.messages);
            }
        });
        
        socket.on('new_message', (data) => {
            if (data.chat_id === currentChat) {
                addMessageToChat(data, data.from === currentUser);
                updateChatLastMessage(data.chat_id, data.message, data.time);
            } else {
                updateChatLastMessage(data.chat_id, data.message, data.time);
                if (!document.hasFocus()) showNotification(data.from_name || data.from, data.message);
            }
        });
        
        socket.on('typing', (data) => {
            if (data.chat_id === currentChat) {
                typingIndicator.innerHTML = data.is_typing ? `✏️ ${data.from_name || data.from} печатает...` : '';
            }
        });
        
        socket.on('chat_created', (data) => {
            showNotification('Создано', data.message);
            loadChats();
            setTimeout(() => {
                openChat(data.chat_id, data.type);
            }, 500);
        });
        
        socket.on('chat_deleted', (data) => {
            if (currentChat === data.chat_id) {
                closeChat();
            }
            loadChats();
        });
        
        socket.on('user_not_found', (data) => {
            showNotification('Ошибка', `Пользователь "${data.query}" не найден`);
        });
        
        function renderChatsList() {
            const searchTerm = searchChats.value.toLowerCase();
            let allChats = [];
            
            chatsList.forEach(chat => {
                allChats.push({
                    id: chat.name,
                    type: 'private',
                    name: chat.first_name || chat.name,
                    username: '@' + (chat.username || chat.name),
                    avatar: chat.avatar || chat.name.charAt(0).toUpperCase(),
                    online: chat.online,
                    last_message: chat.last_message,
                    last_time: chat.last_time,
                    unread: chat.unread
                });
            });
            
            groupsList.forEach(group => {
                allChats.push({
                    id: group.id,
                    type: 'group',
                    name: group.name,
                    username: group.description ? group.description.slice(0, 30) : 'Группа',
                    avatar: '👥',
                    online: true,
                    last_message: group.last_message,
                    last_time: group.last_time,
                    unread: group.unread
                });
            });
            
            channelsList.forEach(channel => {
                allChats.push({
                    id: channel.id,
                    type: 'channel',
                    name: channel.name,
                    username: channel.description ? channel.description.slice(0, 30) : 'Канал',
                    avatar: '📢',
                    online: true,
                    last_message: channel.last_message,
                    last_time: channel.last_time,
                    unread: channel.unread
                });
            });
            
            let filtered = allChats.filter(c => 
                c.name.toLowerCase().includes(searchTerm) || 
                c.username.toLowerCase().includes(searchTerm)
            );
            
            chatsListEl.innerHTML = '';
            filtered.forEach(chat => {
                const div = document.createElement('div');
                div.className = `chat-item ${currentChat === chat.id ? 'active' : ''}`;
                div.innerHTML = `
                    <div class="chat-avatar ${chat.type}">
                        ${chat.avatar}
                        ${chat.online && chat.type === 'private' ? '<div class="online-dot"></div>' : ''}
                    </div>
                    <div class="chat-info">
                        <div class="chat-name">${escapeHtml(chat.name)}</div>
                        <div class="chat-username">${escapeHtml(chat.username)}</div>
                        <div class="chat-last-message">${escapeHtml(chat.last_message || '')}</div>
                    </div>
                    <div class="chat-meta">
                        <div class="chat-time">${chat.last_time || ''}</div>
                        ${chat.unread > 0 ? `<div class="chat-unread">${chat.unread}</div>` : ''}
                    </div>
                `;
                div.onclick = () => openChat(chat.id, chat.type);
                chatsListEl.appendChild(div);
            });
        }
        
        function renderMessages(messages) {
            messagesArea.innerHTML = '';
            messages.forEach(msg => addMessageToChat(msg, msg.from === currentUser));
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }
        
        function addMessageToChat(msg, isOwn) {
            const div = document.createElement('div');
            div.className = `message ${isOwn ? 'own' : 'other'}`;
            div.innerHTML = `
                <div class="message-bubble">
                    <div class="message-text">${escapeHtml(msg.message)}</div>
                    <div class="message-time">${msg.time || new Date(msg.timestamp).toLocaleTimeString()}</div>
                </div>
            `;
            messagesArea.appendChild(div);
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }
        
        function updateChatLastMessage(chatId, message, time) {
            renderChatsList();
        }
        
        function openChat(chatId, type) {
            currentChat = chatId;
            currentChatType = type;
            
            inputArea.style.display = 'flex';
            messageInput.disabled = false;
            chatActions.style.display = 'flex';
            updateFabVisibility();
            
            if (type === 'private') {
                const userData = allUsersData[chatId] || {};
                chatName.innerText = userData.first_name || chatId;
                chatUsername.innerText = '@' + (userData.username || chatId);
                chatAvatar.innerText = (userData.first_name?.charAt(0) || chatId.charAt(0)).toUpperCase();
                const userOnline = allUsers.includes(chatId);
                chatStatus.innerHTML = userOnline ? '🟢 Онлайн' : '⚫ Был(а) недавно';
            } else if (type === 'group') {
                const group = groupsList.find(g => g.id === chatId) || {};
                chatName.innerText = group.name || chatId;
                chatUsername.innerText = group.description || 'Группа';
                chatAvatar.innerText = '👥';
                chatStatus.innerHTML = `👥 ${group.members_count || 0} участников`;
            } else if (type === 'channel') {
                const channel = channelsList.find(c => c.id === chatId) || {};
                chatName.innerText = channel.name || chatId;
                chatUsername.innerText = channel.description || 'Канал';
                chatAvatar.innerText = '📢';
                chatStatus.innerHTML = `📢 ${channel.subscribers_count || 0} подписчиков`;
            }
            
            renderChatsList();
            socket.emit('get_chat_history', { chat_id: chatId, type: type });
            if (window.innerWidth <= 768) {
                document.getElementById('chatsSidebar').classList.remove('open');
            }
        }
        
        function sendMessage() {
            if (!currentChat || !messageInput.value.trim()) return;
            const msg = messageInput.value.trim();
            socket.emit('send_message', { 
                chat_id: currentChat, 
                type: currentChatType, 
                message: msg 
            });
            messageInput.value = '';
        }
        
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        sendBtn.onclick = sendMessage;
        
        function handleTyping() {
            if (!currentChat) return;
            socket.emit('typing', { chat_id: currentChat, type: currentChatType, is_typing: true });
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                socket.emit('typing', { chat_id: currentChat, type: currentChatType, is_typing: false });
            }, 1000);
        }
        
        messageInput.addEventListener('input', handleTyping);
        
        function archiveChat() {
            if (!currentChat) return;
            socket.emit('archive_chat', { chat_id: currentChat, type: currentChatType });
            showNotification('Система', `Чат архивирован`);
            loadChats();
        }
        
        function deleteChat() {
            if (!currentChat) return;
            if (confirm(`Удалить/выйти из ${currentChatType === 'private' ? 'чата' : currentChatType === 'group' ? 'группы' : 'канала'}?`)) {
                socket.emit('delete_chat', { chat_id: currentChat, type: currentChatType });
                closeChat();
                loadChats();
            }
        }
        
        function showChatInfo() {
            if (!currentChat) return;
            socket.emit('get_chat_info', { chat_id: currentChat, type: currentChatType });
        }
        
        socket.on('chat_info', (data) => {
            const infoBody = document.getElementById('infoBody');
            if (data.type === 'group') {
                infoBody.innerHTML = `
                    <p><strong>👥 Название:</strong> ${escapeHtml(data.name)}</p>
                    <p><strong>📝 Описание:</strong> ${escapeHtml(data.description || 'Нет')}</p>
                    <p><strong>👤 Создатель:</strong> @${escapeHtml(data.creator)}</p>
                    <p><strong>👥 Участники (${data.members.length}):</strong></p>
                    <ul>${data.members.map(m => `<li>@${escapeHtml(m)}</li>`).join('')}</ul>
                `;
            } else if (data.type === 'channel') {
                infoBody.innerHTML = `
                    <p><strong>📢 Название:</strong> ${escapeHtml(data.name)}</p>
                    <p><strong>📝 Описание:</strong> ${escapeHtml(data.description || 'Нет')}</p>
                    <p><strong>👤 Создатель:</strong> @${escapeHtml(data.creator)}</p>
                    <p><strong>👥 Подписчиков:</strong> ${data.subscribers_count}</p>
                `;
            } else {
                infoBody.innerHTML = `
                    <p><strong>👤 Пользователь:</strong> ${escapeHtml(data.name)}</p>
                    <p><strong>@username:</strong> @${escapeHtml(data.username)}</p>
                    <p><strong>📝 О себе:</strong> ${escapeHtml(data.bio || 'Нет')}</p>
                `;
            }
            document.getElementById('infoTitle').innerText = data.type === 'private' ? 'Информация о пользователе' : data.type === 'group' ? 'Информация о группе' : 'Информация о канале';
            openModal('chatInfoModal');
        });
        
        function createChat() {
            const username = document.getElementById('chatUsername').value.trim().replace('@', '');
            if (!username) {
                showNotification('Ошибка', 'Введите username');
                return;
            }
            socket.emit('create_chat', { with: username });
            closeModal('newChatModal');
        }
        
        function createGroup() {
            const name = document.getElementById('groupName').value.trim();
            const desc = document.getElementById('groupDesc').value.trim();
            if (!name) {
                showNotification('Ошибка', 'Введите название группы');
                return;
            }
            socket.emit('create_group', { name: name, description: desc });
            closeModal('newChatModal');
        }
        
        function createChannel() {
            const name = document.getElementById('channelName').value.trim();
            const desc = document.getElementById('channelDesc').value.trim();
            const isPublic = document.getElementById('channelPublic') ? document.getElementById('channelPublic').checked : false;
            if (!name) {
                showNotification('Ошибка', 'Введите название канала');
                return;
            }
            socket.emit('create_channel', { name: name, description: desc, public: isPublic });
            closeModal('newChatModal');
        }
        
        function saveProfile() {
            const firstName = document.getElementById('editFirstName').value;
            const lastName = document.getElementById('editLastName').value;
            const newUsername = document.getElementById('editUsername').value;
            const status = document.getElementById('editStatus').value;
            const bio = document.getElementById('editBio').value;
            if (newUsername.length < 4) {
                alert('Юзернейм должен быть минимум 4 символа');
                return;
            }
            socket.emit('update_profile', { 
                username: newUsername, 
                first_name: firstName, 
                last_name: lastName, 
                status: status, 
                bio: bio 
            });
            if (newUsername !== currentUser) {
                currentUser = newUsername;
                profileName.innerText = firstName + ' ' + lastName;
                profileUsername.innerText = '@' + newUsername;
                profileAvatar.innerText = firstName?.charAt(0) || '✨';
            }
            closeModal('profileModal');
            showNotification('Профиль', 'Данные сохранены');
        }
        
        function globalSearch() {
            const query = document.getElementById('globalSearchInput').value.trim();
            if (!query) return;
            socket.emit('search_users', { query: query });
        }
        
        socket.on('search_results', (data) => {
            const resultsDiv = document.getElementById('globalSearchResults');
            if (resultsDiv) {
                if (data.users.length === 0) {
                    resultsDiv.innerHTML = `<div class="user-not-found">❌ Пользователь "${data.query}" не найден</div>`;
                    return;
                }
                resultsDiv.innerHTML = '';
                data.users.forEach(user => {
                    const div = document.createElement('div');
                    div.className = 'user-search-result';
                    div.innerHTML = `
                        <div class="chat-avatar" style="width: 40px; height: 40px;">${(user.first_name?.charAt(0) || user.username.charAt(0)).toUpperCase()}</div>
                        <div>
                            <div><strong>${escapeHtml(user.first_name || user.username)} ${escapeHtml(user.last_name || '')}</strong></div>
                            <div style="font-size: 11px; color: var(--text2);">@${escapeHtml(user.username)}</div>
                        </div>
                        <button onclick="startPrivateChat('${user.username}')" style="margin-left: auto; background: var(--accent); border: none; border-radius: 20px; padding: 6px 12px; color: white; cursor: pointer;">Чат</button>
                    `;
                    resultsDiv.appendChild(div);
                });
            }
        });
        
        function startPrivateChat(username) {
            socket.emit('create_chat', { with: username });
            closeModal('searchUsersModal');
        }
        
        function openGlobalSearch() {
            document.getElementById('globalSearchInput').value = '';
            document.getElementById('globalSearchResults').innerHTML = '';
            openModal('searchUsersModal');
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        profileBtn.onclick = () => { loadUserData(); openModal('profileModal'); };
        openSettingsBtn.onclick = () => openModal('settingsModal');
        archiveChatBtn.onclick = archiveChat;
        deleteChatBtn.onclick = deleteChat;
        chatInfoBtn.onclick = showChatInfo;
        document.getElementById('saveProfileBtn').onclick = saveProfile;
        document.getElementById('themeSettingsBtn').onclick = renderThemeList;
        document.getElementById('logoutBtn').onclick = () => { socket.disconnect(); location.reload(); };
        searchChats.oninput = () => renderChatsList();
        
        mobileMenuBtn.onclick = () => document.getElementById('chatsSidebar').classList.toggle('open');
        if (window.innerWidth <= 768) mobileMenuBtn.style.display = 'block';
        
        window.createChat = createChat;
        window.createGroup = createGroup;
        window.createChannel = createChannel;
        window.startPrivateChat = startPrivateChat;
        
        setTheme(currentTheme);
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
    
    if users[username].get('password') != hashlib.md5(password.encode()).hexdigest():
        emit('auth_error', {'error': 'Неверный пароль'})
        return
    
    user_sessions[request.sid] = username
    users[username]['sid'] = request.sid
    users[username]['last_seen'] = datetime.now().strftime('%H:%M')
    users[username]['status'] = '🟢 Онлайн'
    save_users()
    
    emit('login_success', {
        'username': username,
        'first_name': users[username].get('first_name', ''),
        'last_name': users[username].get('last_name', '')
    })
    broadcast_user_status(username, 'online')
    broadcast_users()

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
    
    users[username] = {
        'sid': None,
        'password': hashlib.md5(password.encode()).hexdigest(),
        'first_name': username,
        'last_name': '',
        'avatar': username[0].upper(),
        'status': '🟢 Онлайн',
        'bio': '',
        'phone': '',
        'settings': {'theme': 'dark', 'notifications': True},
        'contacts': [],
        'blocked': [],
        'archived': [],
        'groups': [],
        'channels': [],
        'last_seen': datetime.now().strftime('%H:%M')
    }
    save_users()
    emit('register_success', {'username': username})

@socketio.on('get_users')
def handle_get_users():
    username = user_sessions.get(request.sid)
    if username:
        users_list = []
        users_data = {}
        for u, u_data in users.items():
            if u != username:
                users_list.append(u)
                users_data[u] = {
                    'username': u,
                    'first_name': u_data.get('first_name', u),
                    'last_name': u_data.get('last_name', ''),
                    'status': u_data.get('status', '')
                }
        emit('users_list', {'users': users_list, 'users_data': users_data})

@socketio.on('get_chats')
def handle_get_chats():
    username = user_sessions.get(request.sid)
    if not username:
        return
    
    # Только чаты, которые создал пользователь
    user_created = user_chats.get(username, [])
    
    chat_list = []
    for other_user in user_created:
        if other_user != username and other_user not in users[username].get('blocked', []):
            if other_user in users:
                chat_key = tuple(sorted([username, other_user]))
                msgs = messages.get(f"private_{chat_key}", [])
                last_msg = msgs[-1] if msgs else None
                chat_list.append({
                    'name': other_user,
                    'username': other_user,
                    'first_name': users[other_user].get('first_name', other_user),
                    'last_name': users[other_user].get('last_name', ''),
                    'avatar': users[other_user].get('avatar', other_user[0].upper()),
                    'online': other_user in user_sessions,
                    'last_message': last_msg['message'][:50] if last_msg else '',
                    'last_time': last_msg['time'] if last_msg else '',
                    'unread': 0
                })
    
    group_list = []
    for group_id, group in groups.items():
        if username in group.get('members', []):
            msgs = messages.get(f"group_{group_id}", [])
            last_msg = msgs[-1] if msgs else None
            group_list.append({
                'id': group_id,
                'name': group['name'],
                'description': group.get('description', ''),
                'members_count': len(group.get('members', [])),
                'last_message': last_msg['message'][:50] if last_msg else '',
                'last_time': last_msg['time'] if last_msg else '',
                'unread': 0
            })
    
    channel_list = []
    for channel_id, channel in channels.items():
        if username in channel.get('subscribers', []):
            msgs = messages.get(f"channel_{channel_id}", [])
            last_msg = msgs[-1] if msgs else None
            channel_list.append({
                'id': channel_id,
                'name': channel['name'],
                'description': channel.get('description', ''),
                'subscribers_count': len(channel.get('subscribers', [])),
                'last_message': last_msg['message'][:50] if last_msg else '',
                'last_time': last_msg['time'] if last_msg else '',
                'unread': 0
            })
    
    emit('chats_list', {'chats': chat_list, 'groups': group_list, 'channels': channel_list})

@socketio.on('get_user_data')
def handle_get_user_data():
    username = user_sessions.get(request.sid)
    if username and username in users:
        emit('user_data', {
            'username': username,
            'first_name': users[username].get('first_name', ''),
            'last_name': users[username].get('last_name', ''),
            'status': users[username].get('status', ''),
            'bio': users[username].get('bio', '')
        })

@socketio.on('update_profile')
def handle_update_profile(data):
    username = user_sessions.get(request.sid)
    if username and username in users:
        old_username = username
        new_username = data.get('username', username)
        if new_username != old_username and new_username not in users:
            users[new_username] = users.pop(old_username)
            username = new_username
            user_sessions[request.sid] = new_username
        users[username]['first_name'] = data.get('first_name', users[username].get('first_name', username))
        users[username]['last_name'] = data.get('last_name', users[username].get('last_name', ''))
        users[username]['status'] = data.get('status', users[username].get('status', ''))
        users[username]['bio'] = data.get('bio', users[username].get('bio', ''))
        save_users()
        emit('user_data', {
            'username': username,
            'first_name': users[username].get('first_name', ''),
            'last_name': users[username].get('last_name', ''),
            'status': users[username].get('status', ''),
            'bio': users[username].get('bio', '')
        })
        broadcast_users()

@socketio.on('search_users')
def handle_search_users(data):
    query = data['query'].lower().replace('@', '')
    current_user = user_sessions.get(request.sid)
    results = []
    for u, u_data in users.items():
        if u != current_user and (query in u.lower() or query in u_data.get('first_name', '').lower() or query in u_data.get('last_name', '').lower()):
            results.append({
                'username': u,
                'first_name': u_data.get('first_name', u),
                'last_name': u_data.get('last_name', '')
            })
    if not results:
        emit('user_not_found', {'query': data['query']})
    else:
        emit('search_results', {'users': results, 'query': data['query']})

@socketio.on('create_chat')
def handle_create_chat(data):
    username = user_sessions.get(request.sid)
    if not username:
        return
    other = data['with']
    if other not in users:
        emit('user_not_found', {'query': other})
        return
    
    # Добавляем чат в список созданных для обоих пользователей
    if username not in user_chats:
        user_chats[username] = []
    if other not in user_chats:
        user_chats[other] = []
    
    if other not in user_chats[username]:
        user_chats[username].append(other)
    if username not in user_chats[other]:
        user_chats[other].append(username)
    
    emit('chat_created', {'chat_id': other, 'type': 'private', 'message': f'Чат с {other} создан'}, room=request.sid)
    if other in user_sessions:
        emit('chat_created', {'chat_id': username, 'type': 'private', 'message': f'Чат с {username} создан'}, room=user_sessions[other])

@socketio.on('create_group')
def handle_create_group(data):
    username = user_sessions.get(request.sid)
    if not username:
        return
    group_id = f"group_{secrets.token_hex(4)}"
    groups[group_id] = {
        'name': data['name'],
        'description': data.get('description', ''),
        'creator': username,
        'admins': [username],
        'members': [username],
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    if 'groups' not in users[username]:
        users[username]['groups'] = []
    users[username]['groups'].append(group_id)
    save_users()
    emit('chat_created', {'chat_id': group_id, 'type': 'group', 'message': f'Группа "{data["name"]}" создана'}, room=request.sid)

@socketio.on('create_channel')
def handle_create_channel(data):
    username = user_sessions.get(request.sid)
    if not username:
        return
    channel_id = f"channel_{secrets.token_hex(4)}"
    channels[channel_id] = {
        'name': data['name'],
        'description': data.get('description', ''),
        'creator': username,
        'subscribers': [username],
        'public': data.get('public', False),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    if 'channels' not in users[username]:
        users[username]['channels'] = []
    users[username]['channels'].append(channel_id)
    save_users()
    emit('chat_created', {'chat_id': channel_id, 'type': 'channel', 'message': f'Канал "{data["name"]}" создан'}, room=request.sid)

@socketio.on('get_chat_history')
def handle_get_history(data):
    username = user_sessions.get(request.sid)
    if not username:
        return
    chat_id = data['chat_id']
    chat_type = data['type']
    msg_key = f"{chat_type}_{chat_id}"
    msgs = messages.get(msg_key, [])
    formatted = []
    for msg in msgs[-100:]:
        formatted.append({
            'from': msg['from'],
            'to': msg.get('to', ''),
            'message': msg['message'],
            'time': msg['time'],
            'timestamp': msg['timestamp']
        })
    emit('chat_history', {'chat_id': chat_id, 'type': chat_type, 'messages': formatted})

@socketio.on('send_message')
def handle_send_message(data):
    username = user_sessions.get(request.sid)
    if not username:
        return
    chat_id = data['chat_id']
    chat_type = data['type']
    message = data['message']
    msg_key = f"{chat_type}_{chat_id}"
    
    if msg_key not in messages:
        messages[msg_key] = []
    
    msg_data = {
        'from': username,
        'to': chat_id,
        'message': message,
        'time': datetime.now().strftime('%H:%M'),
        'timestamp': datetime.now().timestamp()
    }
    messages[msg_key].append(msg_data)
    if len(messages[msg_key]) > 500:
        messages[msg_key].pop(0)
    
    if chat_type == 'private':
        if chat_id in user_sessions:
            emit('new_message', {**msg_data, 'chat_id': chat_id, 'type': chat_type, 'from_name': users[username].get('first_name', username)}, room=user_sessions[chat_id])
        emit('new_message', {**msg_data, 'chat_id': chat_id, 'type': chat_type, 'from_name': users[username].get('first_name', username)}, room=request.sid)
    elif chat_type == 'group':
        for member in groups.get(chat_id, {}).get('members', []):
            if member in user_sessions:
                emit('new_message', {**msg_data, 'chat_id': chat_id, 'type': chat_type, 'from_name': users[username].get('first_name', username)}, room=user_sessions[member])
    elif chat_type == 'channel':
        for subscriber in channels.get(chat_id, {}).get('subscribers', []):
            if subscriber in user_sessions:
                emit('new_message', {**msg_data, 'chat_id': chat_id, 'type': chat_type, 'from_name': users[username].get('first_name', username)}, room=user_sessions[subscriber])

@socketio.on('typing')
def handle_typing(data):
    username = user_sessions.get(request.sid)
    if not username:
        return
    chat_id = data['chat_id']
    chat_type = data['type']
    is_typing = data['is_typing']
    
    if chat_type == 'private':
        if chat_id in user_sessions:
            emit('typing', {'chat_id': chat_id, 'from': username, 'from_name': users[username].get('first_name', username), 'is_typing': is_typing}, room=user_sessions[chat_id])
    elif chat_type == 'group':
        for member in groups.get(chat_id, {}).get('members', []):
            if member in user_sessions and member != username:
                emit('typing', {'chat_id': chat_id, 'from': username, 'from_name': users[username].get('first_name', username), 'is_typing': is_typing}, room=user_sessions[member])
    elif chat_type == 'channel':
        for subscriber in channels.get(chat_id, {}).get('subscribers', []):
            if subscriber in user_sessions and subscriber != username:
                emit('typing', {'chat_id': chat_id, 'from': username, 'from_name': users[username].get('first_name', username), 'is_typing': is_typing}, room=user_sessions[subscriber])

@socketio.on('delete_chat')
def handle_delete_chat(data):
    username = user_sessions.get(request.sid)
    if not username:
        return
    chat_id = data['chat_id']
    chat_type = data['type']
    
    msg_key = f"{chat_type}_{chat_id}"
    if msg_key in messages:
        del messages[msg_key]
    
    if chat_type == 'private':
        if username in user_chats:
            if chat_id in user_chats[username]:
                user_chats[username].remove(chat_id)
    
    if chat_type == 'group' and chat_id in groups:
        if username in groups[chat_id].get('members', []):
            groups[chat_id]['members'].remove(username)
    elif chat_type == 'channel' and chat_id in channels:
        if username in channels[chat_id].get('subscribers', []):
            channels[chat_id]['subscribers'].remove(username)
    
    emit('chat_deleted', {'chat_id': chat_id, 'type': chat_type}, room=request.sid)

@socketio.on('get_chat_info')
def handle_get_chat_info(data):
    username = user_sessions.get(request.sid)
    if not username:
        return
    chat_id = data['chat_id']
    chat_type = data['type']
    
    if chat_type == 'private':
        other = chat_id
        emit('chat_info', {
            'type': 'private',
            'name': users[other].get('first_name', other),
            'username': other,
            'bio': users[other].get('bio', '')
        }, room=request.sid)
    elif chat_type == 'group' and chat_id in groups:
        group = groups[chat_id]
        emit('chat_info', {
            'type': 'group',
            'name': group['name'],
            'description': group.get('description', ''),
            'creator': group['creator'],
            'members': group.get('members', [])
        }, room=request.sid)
    elif chat_type == 'channel' and chat_id in channels:
        channel = channels[chat_id]
        emit('chat_info', {
            'type': 'channel',
            'name': channel['name'],
            'description': channel.get('description', ''),
            'creator': channel['creator'],
            'subscribers_count': len(channel.get('subscribers', []))
        }, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    username = user_sessions.pop(request.sid, None)
    if username and username in users:
        users[username]['status'] = '⚫ Офлайн'
        users[username]['last_seen'] = datetime.now().strftime('%H:%M')
        save_users()
        broadcast_user_status(username, 'offline')

def broadcast_users():
    all_users = [u for u in user_sessions.values()]
    for sid in user_sessions.values():
        emit('users_list', {'users': all_users}, room=sid)

def broadcast_user_status(username, status):
    for sid in user_sessions.values():
        emit('user_status', {'username': username, 'status': status}, room=sid)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print('=' * 60)
    print('✨ SHADOWCHAT — ПОЛНАЯ КОПИЯ TELEGRAM')
    print('=' * 60)
    print(f'📍 Локальный доступ: http://127.0.0.1:5000')
    print(f'📍 Доступ в сети: http://{local_ip}:5000')
    print('=' * 60)
    print('✅ НОВЫЕ ФУНКЦИИ:')
    print('   • Чат появляется ТОЛЬКО после вашего создания')
    print('   • Вход только по юзернейму и паролю')
    print('   • ESC — закрыть текущий чат')
    print('=' * 60)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

from flask import Flask, render_template_string, request, session, redirect, url_for
from datetime import datetime
import secrets
import hashlib
import os
import json

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ========== ФАЙЛЫ ДЛЯ ХРАНЕНИЯ ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, 'users.txt')
GROUPS_FILE = os.path.join(BASE_DIR, 'groups.json')
CHANNELS_FILE = os.path.join(BASE_DIR, 'channels.json')

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

def load_groups():
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_groups():
    with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_channels():
    with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)

users = load_users()
groups = load_groups()
channels = load_channels()
messages_storage = {}  # 'chat_id' -> list of messages
user_chats = {}  # username -> list of created chats

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>ShadowChat — как Telegram</title>
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
            <input type="text" id="loginUsername" placeholder="Юзернейм (мин. 4)">
            <input type="password" id="loginPassword" placeholder="Пароль (мин. 8)">
            <div class="error-message" id="loginError"></div>
            <button id="loginBtn">Войти</button>
            <div style="margin-top:15px;">
                <span style="color:var(--text2);cursor:pointer;" id="switchAuthBtn">Нет аккаунта? <span style="color:var(--accent);">Зарегистрироваться</span></span>
            </div>
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
                <div style="text-align: center; color: var(--text2); margin-top: 40px;">✨ Выберите чат из списка слева</div>
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
                <button onclick="closeModal('profileModal')">✕</button>
            </div>
            <div class="modal-body">
                <label>Имя</label>
                <input type="text" id="editFirstName" placeholder="Имя">
                <label>Юзернейм</label>
                <input type="text" id="editUsername" placeholder="@username">
                <label>Статус</label>
                <input type="text" id="editStatus" placeholder="Статус...">
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
                <button onclick="closeModal('settingsModal')">✕</button>
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
                <button onclick="closeModal('themeModal')">✕</button>
            </div>
            <div class="modal-body" id="themeList"></div>
        </div>
    </div>
    
    <div class="modal" id="newChatModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="newModalTitle">Новый чат</h3>
                <button onclick="closeModal('newChatModal')">✕</button>
            </div>
            <div class="modal-body" id="newModalBody"></div>
        </div>
    </div>
    
    <div class="modal" id="chatInfoModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="infoTitle">Информация</h3>
                <button onclick="closeModal('chatInfoModal')">✕</button>
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
                <button onclick="closeModal('searchUsersModal')">✕</button>
            </div>
            <div class="modal-body">
                <input type="text" id="globalSearchInput" placeholder="Введите имя или @username">
                <div id="globalSearchResults"></div>
            </div>
        </div>
    </div>
    
    <script>
        let currentUser = '';
        let currentChat = null;
        let currentChatType = null;
        let currentTheme = localStorage.getItem('shadowchat_theme') || 'dark';
        let allUsers = [];
        let chatsList = [];
        let groupsList = [];
        let channelsList = [];
        let messagesData = {};
        let pollingInterval;
        
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
        const fabBtn = document.getElementById('fabBtn');
        const fabMenu = document.getElementById('fabMenu');
        const newPrivateChatBtn = document.getElementById('newPrivateChatBtn');
        const newGroupBtn = document.getElementById('newGroupBtn');
        const newChannelBtn = document.getElementById('newChannelBtn');
        const archiveChatBtn = document.getElementById('archiveChatBtn');
        const deleteChatBtn = document.getElementById('deleteChatBtn');
        const chatInfoBtn = document.getElementById('chatInfoBtn');
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        
        let isLoginMode = true;
        
        const themes = {
            dark: '🌙 Тёмная',
            light: '☀️ Светлая',
            blue: '💙 Синяя',
            green: '💚 Зелёная',
            purple: '💜 Фиолетовая'
        };
        
        function setTheme(theme) {
            currentTheme = theme;
            document.body.className = theme;
            localStorage.setItem('shadowchat_theme', theme);
            document.getElementById('currentThemeName').innerText = themes[theme];
        }
        
        function renderThemeList() {
            const themeList = document.getElementById('themeList');
            themeList.innerHTML = '';
            for (const [key, name] of Object.entries(themes)) {
                const div = document.createElement('div');
                div.className = `theme-option ${currentTheme === key ? 'selected' : ''}`;
                div.innerHTML = name;
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
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && currentChat) {
                closeChat();
            }
        });
        
        fabBtn.onclick = () => { fabMenu.classList.toggle('show'); };
        document.addEventListener('click', (e) => {
            if (!fabBtn.contains(e.target) && !fabMenu.contains(e.target)) {
                fabMenu.classList.remove('show');
            }
        });
        
        newPrivateChatBtn.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('newModalTitle').innerText = 'Новый чат';
            document.getElementById('newModalBody').innerHTML = `
                <input type="text" id="chatUsername" placeholder="@username пользователя" style="width:100%;padding:12px;margin-bottom:16px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;color:var(--text);">
                <button onclick="createChat()" style="width:100%;padding:12px;background:var(--accent);border:none;border-radius:10px;color:white;cursor:pointer;">Начать чат</button>
            `;
            openModal('newChatModal');
        };
        
        newGroupBtn.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('newModalTitle').innerText = 'Создать группу';
            document.getElementById('newModalBody').innerHTML = `
                <input type="text" id="groupName" placeholder="Название группы" style="width:100%;padding:12px;margin-bottom:12px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;color:var(--text);">
                <textarea id="groupDesc" placeholder="Описание группы" rows="2" style="width:100%;padding:12px;margin-bottom:16px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;color:var(--text);"></textarea>
                <button onclick="createGroup()" style="width:100%;padding:12px;background:var(--accent);border:none;border-radius:10px;color:white;cursor:pointer;">Создать группу</button>
            `;
            openModal('newChatModal');
        };
        
        newChannelBtn.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('newModalTitle').innerText = 'Создать канал';
            document.getElementById('newModalBody').innerHTML = `
                <input type="text" id="channelName" placeholder="Название канала" style="width:100%;padding:12px;margin-bottom:12px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;color:var(--text);">
                <textarea id="channelDesc" placeholder="Описание канала" rows="2" style="width:100%;padding:12px;margin-bottom:12px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;color:var(--text);"></textarea>
                <label style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
                    <input type="checkbox" id="channelPublic"> Публичный канал
                </label>
                <button onclick="createChannel()" style="width:100%;padding:12px;background:var(--accent);border:none;border-radius:10px;color:white;cursor:pointer;">Создать канал</button>
            `;
            openModal('newChatModal');
        };
        
        switchAuthBtn.onclick = () => {
            isLoginMode = !isLoginMode;
            if (isLoginMode) {
                loginBtn.innerText = 'Войти';
                switchAuthBtn.innerHTML = 'Нет аккаунта? <span style="color:var(--accent);">Зарегистрироваться</span>';
                loginError.style.display = 'none';
            } else {
                loginBtn.innerText = 'Зарегистрироваться';
                switchAuthBtn.innerHTML = 'Уже есть аккаунт? <span style="color:var(--accent);">Войти</span>';
                loginError.style.display = 'none';
            }
        };
        
        loginBtn.onclick = async () => {
            const username = loginUsername.value.trim();
            const password = loginPassword.value;
            const url = isLoginMode ? '/login' : '/register';
            
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();
            
            if (data.success) {
                if (isLoginMode) {
                    currentUser = username;
                    profileName.innerText = username;
                    profileUsername.innerText = '@' + username;
                    profileAvatar.innerText = username.charAt(0).toUpperCase();
                    loginWrapper.style.display = 'none';
                    chatApp.style.display = 'flex';
                    updateFabVisibility();
                    loadData();
                    startPolling();
                } else {
                    alert('Аккаунт создан! Теперь войдите');
                    isLoginMode = true;
                    loginBtn.innerText = 'Войти';
                    switchAuthBtn.innerHTML = 'Нет аккаунта? <span style="color:var(--accent);">Зарегистрироваться</span>';
                    loginError.style.display = 'none';
                    loginUsername.value = username;
                    loginPassword.value = '';
                }
            } else {
                loginError.innerText = data.error;
                loginError.style.display = 'block';
            }
        };
        
        async function loadData() {
            const [usersRes, chatsRes, groupsRes, channelsRes, messagesRes] = await Promise.all([
                fetch('/get_users'),
                fetch('/get_chats'),
                fetch('/get_groups'),
                fetch('/get_channels'),
                fetch('/get_messages')
            ]);
            const usersData = await usersRes.json();
            const chatsData = await chatsRes.json();
            const groupsData = await groupsRes.json();
            const channelsData = await channelsRes.json();
            const messagesDataRes = await messagesRes.json();
            
            allUsers = usersData.users.filter(u => u !== currentUser);
            chatsList = chatsData.chats || [];
            groupsList = groupsData.groups || [];
            channelsList = channelsData.channels || [];
            messagesData = messagesDataRes.messages || {};
            renderChatsList();
        }
        
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
                    last_message: chat.last_message,
                    last_time: chat.last_time,
                    unread: 0
                });
            });
            
            groupsList.forEach(group => {
                allChats.push({
                    id: group.id,
                    type: 'group',
                    name: group.name,
                    username: group.description || 'Группа',
                    avatar: '👥',
                    last_message: group.last_message,
                    last_time: group.last_time,
                    unread: 0
                });
            });
            
            channelsList.forEach(channel => {
                allChats.push({
                    id: channel.id,
                    type: 'channel',
                    name: channel.name,
                    username: channel.description || 'Канал',
                    avatar: '📢',
                    last_message: channel.last_message,
                    last_time: channel.last_time,
                    unread: 0
                });
            });
            
            const filtered = allChats.filter(c => 
                c.name.toLowerCase().includes(searchTerm) || 
                c.username.toLowerCase().includes(searchTerm)
            );
            
            chatsListEl.innerHTML = '';
            filtered.forEach(chat => {
                const div = document.createElement('div');
                div.className = `chat-item ${currentChat === chat.id ? 'active' : ''}`;
                div.innerHTML = `
                    <div class="chat-avatar ${chat.type}">${chat.avatar}</div>
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
        
        function renderMessages(msgs) {
            messagesArea.innerHTML = '';
            msgs.forEach(msg => addMessageToChat(msg, msg.from === currentUser));
            messagesArea.scrollTop = messagesArea.scrollHeight;
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
        
        function openChat(chatId, type) {
            currentChat = chatId;
            currentChatType = type;
            inputArea.style.display = 'flex';
            messageInput.disabled = false;
            chatActions.style.display = 'flex';
            updateFabVisibility();
            
            if (type === 'private') {
                chatName.innerText = chatId;
                chatUsername.innerText = '@' + chatId;
                chatAvatar.innerText = chatId.charAt(0).toUpperCase();
                chatStatus.innerHTML = '🟢 Онлайн';
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
            const msgs = messagesData[chatId] || [];
            renderMessages(msgs);
            if (window.innerWidth <= 768) {
                document.getElementById('chatsSidebar').classList.remove('open');
            }
        }
        
        async function sendMessage() {
            if (!currentChat || !messageInput.value.trim()) return;
            const msg = messageInput.value.trim();
            await fetch('/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ to: currentChat, type: currentChatType, message: msg })
            });
            messageInput.value = '';
        }
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
        
        sendBtn.onclick = sendMessage;
        
        async function createChat() {
            const username = document.getElementById('chatUsername').value.trim().replace('@', '');
            if (!username) { showNotification('Ошибка', 'Введите username'); return; }
            await fetch('/create_chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ with: username })
            });
            closeModal('newChatModal');
            loadData();
        }
        
        async function createGroup() {
            const name = document.getElementById('groupName').value.trim();
            const desc = document.getElementById('groupDesc').value.trim();
            if (!name) { showNotification('Ошибка', 'Введите название группы'); return; }
            await fetch('/create_group', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, description: desc })
            });
            closeModal('newChatModal');
            loadData();
        }
        
        async function createChannel() {
            const name = document.getElementById('channelName').value.trim();
            const desc = document.getElementById('channelDesc').value.trim();
            const isPublic = document.getElementById('channelPublic')?.checked || false;
            if (!name) { showNotification('Ошибка', 'Введите название канала'); return; }
            await fetch('/create_channel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, description: desc, public: isPublic })
            });
            closeModal('newChatModal');
            loadData();
        }
        
        async function deleteChat() {
            if (!currentChat) return;
            if (confirm(`Удалить ${currentChatType === 'private' ? 'чат' : currentChatType === 'group' ? 'группу' : 'канал'}?`)) {
                await fetch('/delete_chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ chat_id: currentChat, type: currentChatType })
                });
                closeChat();
                loadData();
            }
        }
        
        function startPolling() {
            if (pollingInterval) clearInterval(pollingInterval);
            pollingInterval = setInterval(() => {
                if (currentUser) loadData();
            }, 3000);
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        profileBtn.onclick = () => openModal('profileModal');
        openSettingsBtn.onclick = () => openModal('settingsModal');
        archiveChatBtn.onclick = () => { if (currentChat) showNotification('Архив', 'Чат архивирован'); };
        deleteChatBtn.onclick = deleteChat;
        document.getElementById('saveProfileBtn').onclick = () => closeModal('profileModal');
        document.getElementById('themeSettingsBtn').onclick = renderThemeList;
        document.getElementById('logoutBtn').onclick = () => { fetch('/logout'); location.reload(); };
        searchChats.oninput = () => renderChatsList();
        
        mobileMenuBtn.onclick = () => document.getElementById('chatsSidebar').classList.toggle('open');
        if (window.innerWidth <= 768) mobileMenuBtn.style.display = 'block';
        
        window.createChat = createChat;
        window.createGroup = createGroup;
        window.createChannel = createChannel;
        
        setTheme(currentTheme);
    </script>
</body>
</html>
'''

# ========== МАРШРУТЫ ==========
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

@app.route('/get_chats')
def get_chats():
    if 'username' not in session:
        return {'chats': []}
    username = session['username']
    user_created = user_chats.get(username, [])
    chats = []
    for other in user_created:
        if other in users:
            chats.append({
                'name': other,
                'username': other,
                'first_name': other,
                'last_name': '',
                'avatar': other[0].upper()
            })
    return {'chats': chats}

@app.route('/get_groups')
def get_groups():
    if 'username' not in session:
        return {'groups': []}
    username = session['username']
    result = []
    for gid, group in groups.items():
        if username in group.get('members', []):
            result.append({
                'id': gid,
                'name': group['name'],
                'description': group.get('description', ''),
                'members_count': len(group.get('members', []))
            })
    return {'groups': result}

@app.route('/get_channels')
def get_channels():
    if 'username' not in session:
        return {'channels': []}
    username = session['username']
    result = []
    for cid, channel in channels.items():
        if username in channel.get('subscribers', []):
            result.append({
                'id': cid,
                'name': channel['name'],
                'description': channel.get('description', ''),
                'subscribers_count': len(channel.get('subscribers', []))
            })
    return {'channels': result}

@app.route('/create_chat', methods=['POST'])
def create_chat():
    if 'username' not in session:
        return {'success': False}
    username = session['username']
    data = request.get_json()
    other = data.get('with')
    
    if other not in users:
        return {'success': False}
    
    if username not in user_chats:
        user_chats[username] = []
    if other not in user_chats:
        user_chats[other] = []
    if other not in user_chats[username]:
        user_chats[username].append(other)
    if username not in user_chats[other]:
        user_chats[other].append(username)
    
    return {'success': True}

@app.route('/create_group', methods=['POST'])
def create_group():
    if 'username' not in session:
        return {'success': False}
    username = session['username']
    data = request.get_json()
    group_id = f"group_{secrets.token_hex(4)}"
    groups[group_id] = {
        'name': data.get('name'),
        'description': data.get('description', ''),
        'creator': username,
        'admins': [username],
        'members': [username]
    }
    save_groups()
    return {'success': True}

@app.route('/create_channel', methods=['POST'])
def create_channel():
    if 'username' not in session:
        return {'success': False}
    username = session['username']
    data = request.get_json()
    channel_id = f"channel_{secrets.token_hex(4)}"
    channels[channel_id] = {
        'name': data.get('name'),
        'description': data.get('description', ''),
        'creator': username,
        'subscribers': [username],
        'public': data.get('public', False)
    }
    save_channels()
    return {'success': True}

@app.route('/send', methods=['POST'])
def send_message():
    if 'username' not in session:
        return {'success': False}
    username = session['username']
    data = request.get_json()
    to_user = data.get('to')
    chat_type = data.get('type', 'private')
    message = data.get('message')
    
    chat_id = to_user if chat_type == 'private' else to_user
    if chat_id not in messages_storage:
        messages_storage[chat_id] = []
    
    messages_storage[chat_id].append({
        'from': username,
        'message': message,
        'time': datetime.now().strftime('%H:%M')
    })
    
    return {'success': True}

@app.route('/get_messages')
def get_messages():
    if 'username' not in session:
        return {'messages': {}}
    username = session['username']
    result = {}
    
    # Добавляем личные чаты
    for other in user_chats.get(username, []):
        if other in users:
            msgs = messages_storage.get(other, [])
            result[other] = msgs
    
    # Добавляем группы
    for gid, group in groups.items():
        if username in group.get('members', []):
            msgs = messages_storage.get(gid, [])
            result[gid] = msgs
    
    # Добавляем каналы
    for cid, channel in channels.items():
        if username in channel.get('subscribers', []):
            msgs = messages_storage.get(cid, [])
            result[cid] = msgs
    
    return {'messages': result}

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    if 'username' not in session:
        return {'success': False}
    username = session['username']
    data = request.get_json()
    chat_id = data.get('chat_id')
    chat_type = data.get('type')
    
    if chat_type == 'private' and chat_id in user_chats.get(username, []):
        user_chats[username].remove(chat_id)
    elif chat_type == 'group' and chat_id in groups:
        if username in groups[chat_id].get('members', []):
            groups[chat_id]['members'].remove(username)
            save_groups()
    elif chat_type == 'channel' and chat_id in channels:
        if username in channels[chat_id].get('subscribers', []):
            channels[chat_id]['subscribers'].remove(username)
            save_channels()
    
    if chat_id in messages_storage:
        del messages_storage[chat_id]
    
    return {'success': True}

@app.route('/logout')
def logout():
    session.pop('username', None)
    return {'success': True}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

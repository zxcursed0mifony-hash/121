from flask import Flask, render_template_string, request, session, jsonify
from datetime import datetime
import secrets
import hashlib
import os
import json
import base64

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB для аватарок

# ========== ФАЙЛЫ ДЛЯ ХРАНЕНИЯ ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, 'users.json')
GROUPS_FILE = os.path.join(BASE_DIR, 'groups.json')
CHANNELS_FILE = os.path.join(BASE_DIR, 'channels.json')
AVATARS_DIR = os.path.join(BASE_DIR, 'avatars')

if not os.path.exists(AVATARS_DIR):
    os.makedirs(AVATARS_DIR)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users():
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

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
messages_storage = {}
user_chats = {}
last_seen = {}

# Сохраняем данные при завершении
import atexit
atexit.register(save_users)
atexit.register(save_groups)
atexit.register(save_channels)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, viewport-fit=cover">
    <title>ShadowChat — Аналог Telegram</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: var(--bg);
            height: 100vh;
            overflow: hidden;
            color: var(--text);
        }
        
        /* ТЕМЫ */
        body.dark {
            --bg: #0a0a0a;
            --bg2: #1a1a1a;
            --bg3: #2a2a2a;
            --bg4: #0f1a2a;
            --text: #ffffff;
            --text2: #8e8e8e;
            --accent: #2b9aff;
            --border: #2a2a2a;
            --danger: #ff4444;
            --success: #4caf50;
            --online: #31a24c;
        }
        body.light {
            --bg: #ffffff;
            --bg2: #f0f0f0;
            --bg3: #e0e0e0;
            --text: #000000;
            --text2: #5e5e5e;
            --accent: #0088cc;
            --border: #d0d0d0;
            --online: #31a24c;
        }
        body.blue {
            --bg: #0a1929;
            --bg2: #132f4c;
            --bg3: #1a3d5c;
            --text: #ffffff;
            --accent: #2196f3;
            --online: #4caf50;
        }
        body.green {
            --bg: #0a2e1a;
            --bg2: #0d3d22;
            --bg3: #12502c;
            --text: #ffffff;
            --accent: #4caf50;
            --online: #81c784;
        }
        body.purple {
            --bg: #1a0a2e;
            --bg2: #2d1b4e;
            --bg3: #3d2568;
            --text: #ffffff;
            --accent: #9c27b0;
            --online: #ce93d8;
        }
        
        /* АНИМАЦИИ */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes messageIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes notificationSlide {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        /* ЛОГИН */
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
        .switch-auth { margin-top: 15px; color: var(--text2); cursor: pointer; }
        .switch-auth span { color: var(--accent); }
        
        /* ОСНОВНОЙ ИНТЕРФЕЙС */
        .chat-app { display: none; height: 100vh; display: flex; }
        
        /* ЛЕВАЯ ПАНЕЛЬ */
        .chats-sidebar {
            width: 380px;
            background: var(--bg2);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            transition: transform 0.3s;
            z-index: 100;
        }
        .profile-header {
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            border-bottom: 1px solid var(--border);
        }
        .profile-header:hover { background: var(--bg3); }
        .profile-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: bold;
            position: relative;
            background-size: cover;
            background-position: center;
            box-shadow: 0 0 0 3px var(--accent);
        }
        .profile-avatar .online-dot {
            position: absolute;
            bottom: 2px;
            right: 2px;
            width: 12px;
            height: 12px;
            background: var(--online);
            border-radius: 50%;
            border: 2px solid var(--bg2);
        }
        .profile-info { flex: 1; }
        .profile-name { font-size: 16px; font-weight: bold; }
        .profile-username { font-size: 12px; color: var(--text2); }
        .profile-status { font-size: 11px; color: var(--online); margin-top: 2px; }
        .edit-profile { background: none; border: none; color: var(--text2); font-size: 20px; cursor: pointer; padding: 8px; border-radius: 50%; }
        .edit-profile:hover { background: var(--bg3); }
        
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
        .search-box button {
            background: none;
            border: none;
            color: var(--text2);
            cursor: pointer;
            font-size: 16px;
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
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            position: relative;
            flex-shrink: 0;
            background-size: cover;
            background-position: center;
            box-shadow: 0 0 0 2px var(--accent);
        }
        .chat-avatar.group { border-radius: 20px; }
        .chat-avatar.channel { border-radius: 20px; background: var(--warning); }
        .online-dot {
            position: absolute;
            bottom: 2px;
            right: 2px;
            width: 10px;
            height: 10px;
            background: var(--online);
            border-radius: 50%;
            border: 2px solid var(--bg2);
        }
        .chat-info { flex: 1; min-width: 0; }
        .chat-name { font-size: 15px; font-weight: 500; display: flex; align-items: center; gap: 5px; }
        .chat-username { font-size: 11px; color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .chat-last-message { font-size: 13px; color: var(--text2); margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .chat-meta { text-align: right; flex-shrink: 0; }
        .chat-time { font-size: 11px; color: var(--text2); }
        .chat-unread {
            background: var(--accent);
            color: white;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 50px;
            margin-top: 4px;
        }
        
        /* ПРАВАЯ ПАНЕЛЬ */
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
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            background-size: cover;
            background-position: center;
            box-shadow: 0 0 0 2px var(--accent);
        }
        .chat-header-info { flex: 1; }
        .chat-header-name { font-size: 17px; font-weight: bold; }
        .chat-header-username { font-size: 12px; color: var(--text2); }
        .chat-header-status { font-size: 11px; color: var(--online); margin-top: 2px; }
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
            gap: 4px;
        }
        .message {
            display: flex;
            max-width: 75%;
            animation: messageIn 0.2s ease;
            margin-bottom: 4px;
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
        .message-text { font-size: 14px; line-height: 1.4; word-break: break-word; }
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
        
        /* ПЛАВАЮЩАЯ КНОПКА */
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
            z-index: 100;
        }
        .fab i { font-size: 24px; color: white; }
        .fab.hide { display: none; }
        
        .fab-menu {
            position: fixed;
            bottom: 90px;
            right: 24px;
            background: var(--bg2);
            border-radius: 20px;
            padding: 8px 0;
            min-width: 200px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 99;
            display: none;
            border: 1px solid var(--border);
        }
        .fab-menu.show { display: block; animation: fadeIn 0.2s ease; }
        .fab-menu-item {
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 14px;
            cursor: pointer;
        }
        .fab-menu-item:hover { background: var(--bg3); }
        .fab-menu-item i { width: 24px; font-size: 18px; color: var(--accent); }
        
        /* МОДАЛКИ */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(5px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2000;
        }
        .modal-content {
            background: var(--bg2);
            border-radius: 28px;
            width: 450px;
            max-width: 90%;
            max-height: 85vh;
            overflow-y: auto;
            animation: fadeIn 0.3s ease;
            border: 1px solid var(--border);
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
            border-radius: 50px;
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
            animation: notificationSlide 0.3s ease;
        }
        
        .avatar-preview {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            margin: 0 auto;
            background-size: cover;
            background-position: center;
            box-shadow: 0 0 0 3px var(--accent);
        }
        
        @media (max-width: 768px) {
            .chats-sidebar {
                position: fixed;
                left: 0;
                top: 0;
                height: 100vh;
                transform: translateX(-100%);
                transition: transform 0.3s;
                z-index: 200;
            }
            .chats-sidebar.open { transform: translateX(0); }
            .message { max-width: 85%; }
            .mobile-menu-btn { display: block; }
        }
        
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: var(--bg3); }
        ::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 4px; }
    </style>
</head>
<body class="dark">
    <div class="login-wrapper" id="loginWrapper">
        <div class="login-card">
            <div style="font-size: 70px; margin-bottom: 20px;">✨</div>
            <h1>ShadowChat</h1>
            <p style="color: var(--text2); margin-bottom: 20px;">Аналог Telegram</p>
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
                <div class="profile-avatar" id="profileAvatar" style="background: linear-gradient(135deg, var(--accent) 0%, #764ba2 100%);"><div class="online-dot"></div></div>
                <div class="profile-info">
                    <div class="profile-name" id="profileName"></div>
                    <div class="profile-username" id="profileUsername"></div>
                    <div class="profile-status" id="profileStatus">Онлайн</div>
                </div>
                <button class="edit-profile" id="openSettingsBtn">⚙️</button>
            </div>
            <div class="search-section">
                <div class="search-box">
                    <input type="text" id="searchChats" placeholder="Поиск...">
                    <button id="globalSearchBtn">🔍</button>
                </div>
            </div>
            <div class="chats-list" id="chatsList"></div>
        </div>
        
        <div class="chat-main">
            <div class="chat-header">
                <button id="mobileMenuBtn" class="mobile-menu-btn" style="display: none; background: none; border: none; color: var(--text2); font-size: 24px; cursor: pointer;">☰</button>
                <div class="chat-header-avatar" id="chatAvatar" style="background: linear-gradient(135deg, var(--accent) 0%, #764ba2 100%);">💬</div>
                <div class="chat-header-info">
                    <div class="chat-header-name" id="chatName">ShadowChat</div>
                    <div class="chat-header-username" id="chatUsername"></div>
                    <div class="chat-header-status" id="chatStatus">Выберите чат</div>
                </div>
                <div class="chat-header-actions" id="chatActions" style="display: none;">
                    <button id="chatInfoBtn" title="Информация">ℹ️</button>
                    <button id="archiveChatBtn" title="Архивировать">📦</button>
                    <button id="deleteChatBtn" title="Удалить">🗑️</button>
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
        <div class="fab-menu-item" id="newPrivateChatBtn"><i class="fas fa-user-plus"></i><span>Новый чат</span></div>
        <div class="fab-menu-item" id="newGroupBtn"><i class="fas fa-users"></i><span>Создать группу</span></div>
        <div class="fab-menu-item" id="newChannelBtn"><i class="fas fa-broadcast-tower"></i><span>Создать канал</span></div>
        <div class="fab-menu-item" id="globalSearchMenuItem"><i class="fas fa-globe"></i><span>Глобальный поиск</span></div>
    </div>
    
    <div class="modal" id="profileModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Настройки профиля</h3>
                <button onclick="closeModal('profileModal')" style="background: none; border: none; font-size: 24px; cursor: pointer;">✕</button>
            </div>
            <div class="modal-body">
                <div class="avatar-preview" id="modalAvatar" style="background: linear-gradient(135deg, var(--accent) 0%, #764ba2 100%);"></div>
                <input type="file" id="avatarUpload" accept="image/*" style="margin: 16px auto; display: block;">
                <label>Имя</label>
                <input type="text" id="editFirstName" placeholder="Имя" style="width:100%; padding:12px; margin-bottom:16px; background:var(--bg3); border:1px solid var(--border); border-radius:12px; color:var(--text);">
                <label>Фамилия</label>
                <input type="text" id="editLastName" placeholder="Фамилия" style="width:100%; padding:12px; margin-bottom:16px; background:var(--bg3); border:1px solid var(--border); border-radius:12px; color:var(--text);">
                <label>Юзернейм</label>
                <input type="text" id="editUsername" placeholder="@username" style="width:100%; padding:12px; margin-bottom:16px; background:var(--bg3); border:1px solid var(--border); border-radius:12px; color:var(--text);">
                <label>Статус</label>
                <input type="text" id="editStatus" placeholder="Статус..." style="width:100%; padding:12px; margin-bottom:16px; background:var(--bg3); border:1px solid var(--border); border-radius:12px; color:var(--text);">
                <label>О себе</label>
                <textarea id="editBio" rows="3" placeholder="О себе..." style="width:100%; padding:12px; background:var(--bg3); border:1px solid var(--border); border-radius:12px; color:var(--text);"></textarea>
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
                <div class="settings-item" id="themeSettingsBtn"><span>🎨 Тема оформления</span><span id="currentThemeName">Тёмная</span></div>
                <div class="settings-item" id="logoutBtn"><span style="color: var(--danger);">🚪 Выйти из аккаунта</span></div>
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
    
    <div class="modal" id="globalSearchModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Глобальный поиск</h3>
                <button onclick="closeModal('globalSearchModal')" style="background: none; border: none; font-size: 24px; cursor: pointer;">✕</button>
            </div>
            <div class="modal-body">
                <input type="text" id="globalSearchInput" placeholder="Введите юзернейм или имя..." style="width:100%; padding:12px; border-radius:50px; background:var(--bg3); border:1px solid var(--border); color:var(--text);">
                <div id="globalSearchResults" style="margin-top: 16px;"></div>
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
        
        // DOM элементы
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
        const globalSearchMenuItem = document.getElementById('globalSearchMenuItem');
        const globalSearchBtn = document.getElementById('globalSearchBtn');
        const archiveChatBtn = document.getElementById('archiveChatBtn');
        const deleteChatBtn = document.getElementById('deleteChatBtn');
        const chatInfoBtn = document.getElementById('chatInfoBtn');
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        const avatarUpload = document.getElementById('avatarUpload');
        
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
            if (currentChat) fabBtn.classList.add('hide');
            else fabBtn.classList.remove('hide');
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
            if (e.key === 'Escape' && currentChat) closeChat();
        });
        
        fabBtn.onclick = () => { fabMenu.classList.toggle('show'); };
        document.addEventListener('click', (e) => {
            if (!fabBtn.contains(e.target) && !fabMenu.contains(e.target)) fabMenu.classList.remove('show');
        });
        
        newPrivateChatBtn.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('newModalTitle').innerText = 'Новый чат';
            document.getElementById('newModalBody').innerHTML = `
                <input type="text" id="chatUsername" placeholder="@username пользователя" style="width:100%;padding:12px;margin-bottom:16px;background:var(--bg3);border:1px solid var(--border);border-radius:12px;color:var(--text);">
                <button onclick="createChat()" style="width:100%;padding:12px;background:var(--accent);border:none;border-radius:12px;color:white;cursor:pointer;">Начать чат</button>
            `;
            openModal('newChatModal');
        };
        
        newGroupBtn.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('newModalTitle').innerText = 'Создать группу';
            document.getElementById('newModalBody').innerHTML = `
                <input type="text" id="groupName" placeholder="Название группы" style="width:100%;padding:12px;margin-bottom:12px;background:var(--bg3);border:1px solid var(--border);border-radius:12px;color:var(--text);">
                <textarea id="groupDesc" placeholder="Описание группы" rows="2" style="width:100%;padding:12px;margin-bottom:16px;background:var(--bg3);border:1px solid var(--border);border-radius:12px;color:var(--text);"></textarea>
                <button onclick="createGroup()" style="width:100%;padding:12px;background:var(--accent);border:none;border-radius:12px;color:white;cursor:pointer;">Создать группу</button>
            `;
            openModal('newChatModal');
        };
        
        newChannelBtn.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('newModalTitle').innerText = 'Создать канал';
            document.getElementById('newModalBody').innerHTML = `
                <input type="text" id="channelName" placeholder="Название канала" style="width:100%;padding:12px;margin-bottom:12px;background:var(--bg3);border:1px solid var(--border);border-radius:12px;color:var(--text);">
                <textarea id="channelDesc" placeholder="Описание канала" rows="2" style="width:100%;padding:12px;margin-bottom:12px;background:var(--bg3);border:1px solid var(--border);border-radius:12px;color:var(--text);"></textarea>
                <label style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
                    <input type="checkbox" id="channelPublic"> Публичный канал
                </label>
                <button onclick="createChannel()" style="width:100%;padding:12px;background:var(--accent);border:none;border-radius:12px;color:white;cursor:pointer;">Создать канал</button>
            `;
            openModal('newChatModal');
        };
        
        globalSearchMenuItem.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('globalSearchInput').value = '';
            document.getElementById('globalSearchResults').innerHTML = '';
            openModal('globalSearchModal');
        };
        
        globalSearchBtn.onclick = () => {
            fabMenu.classList.remove('show');
            document.getElementById('globalSearchInput').value = '';
            document.getElementById('globalSearchResults').innerHTML = '';
            openModal('globalSearchModal');
        };
        
        switchAuthBtn.onclick = () => {
            isLoginMode = !isLoginMode;
            if (isLoginMode) {
                loginBtn.innerText = 'Войти';
                switchAuthBtn.innerHTML = 'Нет аккаунта? <span>Зарегистрироваться</span>';
            } else {
                loginBtn.innerText = 'Зарегистрироваться';
                switchAuthBtn.innerHTML = 'Уже есть аккаунт? <span>Войти</span>';
            }
            loginError.style.display = 'none';
        };
        
        async function uploadAvatar(file) {
            const formData = new FormData();
            formData.append('avatar', file);
            const response = await fetch('/upload_avatar', { method: 'POST', body: formData });
            return await response.json();
        }
        
        async function loadUserAvatar() {
            const response = await fetch('/get_avatar');
            const data = await response.json();
            if (data.avatar) {
                profileAvatar.style.backgroundImage = `url(${data.avatar})`;
                profileAvatar.style.backgroundSize = 'cover';
                profileAvatar.style.backgroundPosition = 'center';
                profileAvatar.innerHTML = '';
                document.getElementById('modalAvatar').style.backgroundImage = `url(${data.avatar})`;
                document.getElementById('modalAvatar').style.backgroundSize = 'cover';
                document.getElementById('modalAvatar').innerHTML = '';
            }
        }
        
        avatarUpload?.addEventListener('change', async (e) => {
            if (e.target.files[0]) {
                const result = await uploadAvatar(e.target.files[0]);
                if (result.success) {
                    showNotification('Успех', 'Аватар загружен');
                    loadUserAvatar();
                } else {
                    showNotification('Ошибка', result.error);
                }
            }
        });
        
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
                    loginWrapper.style.display = 'none';
                    chatApp.style.display = 'flex';
                    updateFabVisibility();
                    loadData();
                    startPolling();
                    loadUserAvatar();
                    showNotification('Добро пожаловать', `Вы вошли как ${username}`);
                } else {
                    showNotification('Успех', 'Аккаунт создан! Теперь войдите');
                    isLoginMode = true;
                    loginBtn.innerText = 'Войти';
                    switchAuthBtn.innerHTML = 'Нет аккаунта? <span>Зарегистрироваться</span>';
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
            
            allUsers = usersData.users || [];
            chatsList = chatsData.chats || [];
            groupsList = groupsData.groups || [];
            channelsList = channelsData.channels || [];
            messagesData = messagesDataRes.messages || {};
            renderChatsList();
            if (currentChat && messagesData[currentChat]) {
                renderMessages(messagesData[currentChat]);
            }
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
                    unread: chat.unread || 0,
                    online: chat.online
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
                    <div class="chat-avatar ${chat.type}" style="background: linear-gradient(135deg, var(--accent) 0%, #764ba2 100%);">${chat.avatar}</div>
                    <div class="chat-info">
                        <div class="chat-name">${escapeHtml(chat.name)}</div>
                        <div class="chat-username">${escapeHtml(chat.username)}</div>
                        <div class="chat-last-message">${escapeHtml(chat.last_message || 'Нет сообщений')}</div>
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
            if (!msgs || msgs.length === 0) {
                messagesArea.innerHTML = '<div style="text-align: center; color: var(--text2); margin-top: 40px;">💬 Нет сообщений</div>';
                return;
            }
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
                const userData = allUsers.find(u => u.username === chatId) || { first_name: chatId, username: chatId };
                chatName.innerText = userData.first_name || chatId;
                chatUsername.innerText = '@' + (userData.username || chatId);
                chatStatus.innerHTML = '🟢 Онлайн';
            } else if (type === 'group') {
                const group = groupsList.find(g => g.id === chatId) || {};
                chatName.innerText = group.name || chatId;
                chatUsername.innerText = group.description || 'Группа';
                chatStatus.innerHTML = `👥 ${group.members_count || 0} участников`;
            } else if (type === 'channel') {
                const channel = channelsList.find(c => c.id === chatId) || {};
                chatName.innerText = channel.name || chatId;
                chatUsername.innerText = channel.description || 'Канал';
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
            const response = await fetch('/create_chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ with: username })
            });
            const data = await response.json();
            if (data.success) {
                closeModal('newChatModal');
                loadData();
                showNotification('Успех', `Чат с ${username} создан`);
            } else {
                showNotification('Ошибка', data.error || 'Пользователь не найден');
            }
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
            showNotification('Успех', `Группа "${name}" создана`);
        }
        
        async function createChannel() {
            const name = document.getElementById('channelName').value.trim();
            const desc = document.getElementById('channelDesc').value.trim();
            if (!name) { showNotification('Ошибка', 'Введите название канала'); return; }
            await fetch('/create_channel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, description: desc, public: false })
            });
            closeModal('newChatModal');
            loadData();
            showNotification('Успех', `Канал "${name}" создан`);
        }
        
        async function globalSearch() {
            const query = document.getElementById('globalSearchInput').value.trim().replace('@', '');
            if (!query) return;
            const response = await fetch('/search_users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });
            const data = await response.json();
            const resultsDiv = document.getElementById('globalSearchResults');
            if (data.users.length === 0) {
                resultsDiv.innerHTML = `<div class="user-not-found">❌ Пользователь "${query}" не найден</div>`;
                return;
            }
            resultsDiv.innerHTML = '';
            data.users.forEach(user => {
                const div = document.createElement('div');
                div.className = 'user-search-result';
                div.innerHTML = `
                    <div class="chat-avatar" style="width: 40px; height: 40px; background: linear-gradient(135deg, var(--accent) 0%, #764ba2 100%);">${(user.first_name?.charAt(0) || user.username.charAt(0)).toUpperCase()}</div>
                    <div><strong>${escapeHtml(user.first_name || user.username)}</strong><br><span style="font-size:11px;color:var(--text2);">@${escapeHtml(user.username)}</span></div>
                    <button onclick="startPrivateChat('${user.username}')" style="margin-left:auto;background:var(--accent);border:none;border-radius:20px;padding:6px 12px;color:white;cursor:pointer;">Чат</button>
                `;
                resultsDiv.appendChild(div);
            });
        }
        
        async function startPrivateChat(username) {
            await fetch('/create_chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ with: username })
            });
            closeModal('globalSearchModal');
            loadData();
            setTimeout(() => openChat(username, 'private'), 500);
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
                showNotification('Успех', 'Чат удалён');
            }
        }
        
        async function saveProfile() {
            const firstName = document.getElementById('editFirstName').value;
            const lastName = document.getElementById('editLastName').value;
            const username = document.getElementById('editUsername').value;
            const status = document.getElementById('editStatus').value;
            const bio = document.getElementById('editBio').value;
            
            const response = await fetch('/update_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ first_name: firstName, last_name: lastName, username: username, status: status, bio: bio })
            });
            const data = await response.json();
            if (data.success) {
                showNotification('Успех', 'Профиль обновлён');
                profileName.innerText = firstName || currentUser;
                profileUsername.innerText = '@' + (username || currentUser);
                closeModal('profileModal');
            } else {
                showNotification('Ошибка', data.error);
            }
        }
        
        function startPolling() {
            if (pollingInterval) clearInterval(pollingInterval);
            pollingInterval = setInterval(() => {
                if (currentUser) loadData();
            }, 2000);
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        profileBtn.onclick = async () => {
            const response = await fetch('/get_user_data');
            const data = await response.json();
            document.getElementById('editFirstName').value = data.first_name || '';
            document.getElementById('editLastName').value = data.last_name || '';
            document.getElementById('editUsername').value = data.username || currentUser;
            document.getElementById('editStatus').value = data.status || '';
            document.getElementById('editBio').value = data.bio || '';
            openModal('profileModal');
        };
        openSettingsBtn.onclick = () => openModal('settingsModal');
        archiveChatBtn.onclick = () => { if (currentChat) showNotification('Архив', 'Чат архивирован'); };
        deleteChatBtn.onclick = deleteChat;
        chatInfoBtn.onclick = () => { if (currentChat) showNotification('Инфо', 'Информация о чате'); };
        document.getElementById('saveProfileBtn').onclick = saveProfile;
        document.getElementById('themeSettingsBtn').onclick = renderThemeList;
        document.getElementById('logoutBtn').onclick = () => { fetch('/logout'); location.reload(); };
        document.getElementById('globalSearchInput').addEventListener('input', globalSearch);
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
    users[username] = {
        'password': password_hash,
        'first_name': username,
        'last_name': '',
        'bio': '',
        'status': 'Онлайн',
        'avatar': '',
        'created_at': datetime.now().isoformat()
    }
    save_users()
    return {'success': True}

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username not in users:
        return {'success': False, 'error': 'Пользователь не найден'}
    if users[username].get('password') != hashlib.md5(password.encode()).hexdigest():
        return {'success': False, 'error': 'Неверный пароль'}
    
    session['username'] = username
    last_seen[username] = datetime.now().isoformat()
    return {'success': True}

@app.route('/get_user_data')
def get_user_data():
    if 'username' not in session:
        return {'success': False}
    username = session['username']
    return {
        'username': username,
        'first_name': users[username].get('first_name', ''),
        'last_name': users[username].get('last_name', ''),
        'status': users[username].get('status', ''),
        'bio': users[username].get('bio', '')
    }

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return {'success': False, 'error': 'Не авторизован'}
    username = session['username']
    data = request.get_json()
    
    new_username = data.get('username')
    if new_username and new_username != username:
        if new_username in users:
            return {'success': False, 'error': 'Юзернейм уже занят'}
        users[new_username] = users.pop(username)
        session['username'] = new_username
        username = new_username
    
    users[username]['first_name'] = data.get('first_name', users[username].get('first_name', ''))
    users[username]['last_name'] = data.get('last_name', users[username].get('last_name', ''))
    users[username]['status'] = data.get('status', users[username].get('status', ''))
    users[username]['bio'] = data.get('bio', users[username].get('bio', ''))
    save_users()
    return {'success': True}

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'username' not in session:
        return {'success': False, 'error': 'Не авторизован'}
    username = session['username']
    
    if 'avatar' not in request.files:
        return {'success': False, 'error': 'Нет файла'}
    
    file = request.files['avatar']
    if file.filename == '':
        return {'success': False, 'error': 'Файл не выбран'}
    
    # Сохраняем как base64 для простоты (на Render нельзя сохранять файлы)
    file_data = base64.b64encode(file.read()).decode('utf-8')
    mime = file.mimetype
    avatar_data = f"data:{mime};base64,{file_data}"
    
    users[username]['avatar'] = avatar_data
    save_users()
    return {'success': True}

@app.route('/get_avatar')
def get_avatar():
    if 'username' not in session:
        return {'avatar': None}
    username = session['username']
    return {'avatar': users[username].get('avatar', '')}

@app.route('/get_users')
def get_users():
    if 'username' not in session:
        return {'users': []}
    users_list = []
    for u, u_data in users.items():
        users_list.append({
            'username': u,
            'first_name': u_data.get('first_name', u),
            'last_name': u_data.get('last_name', ''),
            'bio': u_data.get('bio', ''),
            'avatar': u_data.get('avatar', ''),
            'status': u_data.get('status', '')
        })
    return {'users': users_list}

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
                'first_name': users[other].get('first_name', other),
                'last_name': users[other].get('last_name', ''),
                'avatar': users[other].get('avatar', ''),
                'online': other in last_seen
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
        return {'success': False, 'error': 'Не авторизован'}
    username = session['username']
    data = request.get_json()
    other = data.get('with')
    
    if other not in users:
        return {'success': False, 'error': 'Пользователь не найден'}
    if other == username:
        return {'success': False, 'error': 'Нельзя создать чат с самим собой'}
    
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
        'members': [username],
        'created_at': datetime.now().isoformat()
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
        'public': data.get('public', False),
        'created_at': datetime.now().isoformat()
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
        'time': datetime.now().strftime('%H:%M'),
        'timestamp': datetime.now().isoformat()
    })
    
    return {'success': True}

@app.route('/get_messages')
def get_messages():
    if 'username' not in session:
        return {'messages': {}}
    username = session['username']
    result = {}
    
    for other in user_chats.get(username, []):
        if other in users:
            msgs = messages_storage.get(other, [])
            result[other] = msgs
    
    for gid, group in groups.items():
        if username in group.get('members', []):
            msgs = messages_storage.get(gid, [])
            result[gid] = msgs
    
    for cid, channel in channels.items():
        if username in channel.get('subscribers', []):
            msgs = messages_storage.get(cid, [])
            result[cid] = msgs
    
    return {'messages': result}

@app.route('/search_users', methods=['POST'])
def search_users():
    if 'username' not in session:
        return {'users': []}
    data = request.get_json()
    query = data.get('query', '').lower()
    current_user = session['username']
    
    results = []
    for u, u_data in users.items():
        if u != current_user and (query in u.lower() or query in u_data.get('first_name', '').lower() or query in u_data.get('last_name', '').lower()):
            results.append({
                'username': u,
                'first_name': u_data.get('first_name', u),
                'last_name': u_data.get('last_name', '')
            })
    return {'users': results}

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
    username = session.pop('username', None)
    if username:
        last_seen[username] = datetime.now().isoformat()
    return {'success': True}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

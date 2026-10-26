# Version 5.0 - Ultimate Fixed (Threading + Render Ready + Auto Msg)

import asyncio
import re
import os
import threading
import time
from datetime import datetime, timezone
from flask import Flask, render_template_string, request, jsonify
from telethon import TelegramClient, events
from telethon.sessions import StringSession

app = Flask(__name__)

api_id = int(os.environ.get('API_ID', 0))
api_hash = os.environ.get('API_HASH', '') 
session_str = os.environ.get('SESSION_STR', '')
TARGET_BOT = '@Taskl1_bot'

client = TelegramClient(StringSession(session_str), api_id, api_hash)

clicked_buttons = set()
latest_message = "Welcome" 

is_username_shown = False
is_waiting_for_report = False

# ==========================================
# রিপোর্ট ক্যাশ সিস্টেম
# ==========================================
report_cache = []
last_synced_id = 0
is_syncing = False

async def sync_reports_from_telegram():
    global report_cache, last_synced_id, is_syncing
    if is_syncing: return
    is_syncing = True

    try:
        kwargs = {'limit': None}
        if last_synced_id > 0:
            kwargs['min_id'] = last_synced_id

        new_messages = []
        async for msg in client.iter_messages(TARGET_BOT, **kwargs):
            new_messages.append(msg)

        for msg in new_messages:
            text = msg.text or ""
            if not text: continue

            ds_cnt = text.count("ds_user_id")
            ap_cnt = len(re.findall(r'report approved', text, re.IGNORECASE))
            rj_cnt = len(re.findall(r'report rejected', text, re.IGNORECASE))

            if ds_cnt > 0 or ap_cnt > 0 or rj_cnt > 0:
                report_cache.append({
                    'id': msg.id,
                    'date': msg.date,
                    'text': text,
                    'ds_cnt': ds_cnt,
                    'ap_cnt': ap_cnt,
                    'rj_cnt': rj_cnt
                })

            if msg.id > last_synced_id:
                last_synced_id = msg.id

        report_cache.sort(key=lambda x: x['date'], reverse=True)

    except Exception as e:
        print(f"Sync Error: {e}")
    finally:
        is_syncing = False

# ==========================================
# টেলিগ্রাম লিসেনার
# ==========================================
@client.on(events.NewMessage(from_users=TARGET_BOT))
async def on_bot_reply(event):
    global latest_message, is_username_shown, is_waiting_for_report
    text = event.text or ""
    if not text.strip(): return
    lines = text.strip().split('\n')

    for line in lines:
        if "Login:" in line:
            username = line.replace("Login:", "").replace("`", "").strip()
            latest_message = username 
            is_username_shown = True
            is_waiting_for_report = False
            return

    if is_waiting_for_report:
        display_text = lines[0].strip()
        for line in lines:
            if "received" in line.lower() or "report" in line.lower():
                display_text = line.strip()
                break
        if "Press the button" in text:
            latest_message = "Submit Done ✅"
        else:
            latest_message = display_text
        is_waiting_for_report = False
        is_username_shown = False
        return

# ==========================================
# বাটন খোঁজার ফাংশন
# ==========================================
async def find_and_click_button(btn_text):
    try:
        messages = await client.get_messages(TARGET_BOT, limit=10)
        for message in messages:
            if message.buttons:
                for row in message.buttons:
                    for btn in row:
                        btn_str = getattr(btn, 'text', '')
                        if hasattr(btn_str, 'text'): btn_str = btn_str.text
                        btn_key = f"{message.id}_{btn_str}"
                        is_match = False
                        if "$0" in btn_text:
                            if re.search(r'\$0', str(btn_str)): is_match = True
                        elif str(btn_text).lower() in str(btn_str).lower(): is_match = True
                        if is_match:
                            if btn_key in clicked_buttons: return "already_clicked"
                            await btn.click()
                            clicked_buttons.add(btn_key)
                            return True
        return False
    except Exception:
        return False

# ==========================================
# HTML (আপনার ডিজাইন অপরিবর্তিত)
# ==========================================
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Control Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 15px; background-color: #e9ebee; margin: 0; }
        .news-ticker { width: 100%; background: #c62828; color: white; padding: 8px 0; overflow: hidden; white-space: nowrap; position: relative; margin-bottom: 15px; border-radius: 5px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .ticker-text { display: inline-block; padding-left: 100%; animation: tickerAnim 15s linear infinite; font-weight: bold; font-size: 14px; }
        @keyframes tickerAnim { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
        .live-display { text-align: center; padding: 25px 15px; background: linear-gradient(135deg, #e3f2fd, #bbdefb); border: 2px solid #64b5f6; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 6px 15px rgba(0,0,0,0.1); min-height: 130px; display: flex; flex-direction: column; justify-content: center; align-items: center; width: 100%; box-sizing: border-box; }
        .live-display h4 { margin: 0 0 15px 0; font-size: clamp(18px, 4.5vw, 26px); font-weight: 900; background: linear-gradient(90deg, #0d47a1, #1976d2, #0d47a1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-transform: uppercase; letter-spacing: 2px; width: 100%; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .loader-container { display: none; flex-direction: column; align-items: center; justify-content: center; gap: 8px; }
        .premium-spinner { width: 35px; height: 35px; border: 3px solid rgba(21, 101, 192, 0.15); border-top: 3px solid #1565c0; border-right: 3px solid #1565c0; border-radius: 50%; animation: spin 0.8s cubic-bezier(0.68, -0.55, 0.27, 1.55) infinite; box-shadow: 0 0 10px rgba(21, 101, 192, 0.2); }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .loader-text { font-size: 13px; font-weight: bold; color: #1565c0; letter-spacing: 1px; text-transform: uppercase; animation: pulseText 1.5s infinite; }
        @keyframes pulseText { 0% { opacity: 0.7; } 50% { opacity: 1; } 100% { opacity: 0.7; } }
        .welcome-msg { display: block; color: #1565c0; font-size: clamp(16px, 4.5vw, 22px); font-weight: bold; line-height: 1.4; text-align: center; white-space: nowrap; }
        .welcome-msg span { font-size: clamp(12px, 3.5vw, 16px); color: #d32f2f; display: block; margin-top: 8px;}
        .live-value { display: none; background: #ffffff; color: #1565c0; border: 2px solid #90caf9; padding: 12px 15px; border-radius: 10px; font-weight: 800; font-size: clamp(18px, 5vw, 26px); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: calc(100% - 10px); box-sizing: border-box; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.1); transition: all 0.2s; text-align: center; }
        .live-value:hover { background: #f0f8ff; transform: scale(1.01); }
        .live-value.success-text { color: #2e7d32; border-color: #81c784; background: #e8f5e9; }
        .copied-msg { font-size: 12px; color: #28a745; font-weight: bold; display: none; margin-top: 8px; }
        .send-all-2fa-btn { background: linear-gradient(135deg, #1d4ed8, #3b82f6); color: white; border: none; padding: 12px 18px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 16px; width: 100%; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4); transition: 0.2s; text-transform: uppercase; letter-spacing: 0.5px; }
        .send-all-2fa-btn:hover { background: linear-gradient(135deg, #1e40af, #2563eb); transform: scale(1.02); }
        .send-all-2fa-btn:disabled { background: #ccc; box-shadow: none; transform: none; cursor: not-allowed; }
        .settings-area { background: white; padding: 20px; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: none; }
        .settings-area h4 { margin: 0 0 15px 0; font-size: 16px; color: #444; text-align: center;}
        .msg-input-group { display: flex; gap: 10px; margin-bottom: 10px; }
        .msg-input-group input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; font-size: 15px; }
        .msg-send-btn { background: #0078FF; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 15px; transition: 0.2s; width: 100px; }
        .msg-send-btn:hover { background: #005bb5; }
        .msg-send-btn:disabled { background: #ccc; cursor: not-allowed; }
        .manual-area { background: #e8f5e9; padding: 20px; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border: 1px solid #81c784; display: flex; flex-direction: column;}
        .manual-area h4 { margin: 0 0 15px 0; font-size: 16px; color: #2e7d32; text-align: center;}
        .manual-input-group { display: flex; flex-direction: column; gap: 12px; }
        .manual-input-group textarea { width: 100%; height: 120px; padding: 15px; border: 2px solid #66bb6a; border-radius: 8px; font-size: 16px; outline: none; box-sizing: border-box; transition: 0.2s; resize: vertical; font-family: inherit; }
        .manual-input-group textarea:focus { border-color: #2e7d32; box-shadow: 0 0 8px rgba(46, 125, 50, 0.2); }
        .manual-send-btn { background: #43a047; color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 18px; width: 100%; transition: 0.2s; box-shadow: 0 4px 6px rgba(67, 160, 71, 0.3);}
        .manual-send-btn:hover { background: #2e7d32; }
        .manual-send-btn:disabled { background: #ccc; cursor: not-allowed; }
        .report-area { background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 6px 18px rgba(0,0,0,0.08); border: 2px solid #90caf9; }
        .report-area > h4 { margin: 0 0 15px 0; font-size: 18px; color: #1565c0; text-align: center; letter-spacing: 0.5px; }
        .filter-area { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; background:#f5f9ff; padding: 15px; border-radius: 8px; }
        .filter-group { display: flex; flex-direction: column; gap: 5px; width: 100%; }
        .filter-group label { font-weight: bold; color: #444; font-size: 13px; }
        .filter-group input { padding: 12px 15px; border: 1px solid #90caf9; border-radius: 5px; font-size: 15px; width: 100%; box-sizing: border-box; }
        .filter-group input:disabled { background: #e0e0e0; color: #777; cursor: not-allowed; border-color: #ccc; }
        .btn-row { display: flex; justify-content: center; align-items: center; gap: 12px; width: 100%; margin-top: 10px;}
        .filter-btn { background: #1565c0; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 14px; transition: 0.2s; flex: 1; max-width: 140px;}
        .filter-btn:hover { background: #0d47a1; }
        .filter-btn:disabled { background: #ccc; cursor: not-allowed; }
        .filter-btn.reset { background: #757575; }
        .filter-btn.reset:hover { background: #555; }
        .lock-icon { font-size: 24px; cursor: pointer; user-select: none; transition: transform 0.2s; line-height: 1; display: flex; align-items: center; justify-content: center;}
        .lock-icon:hover { transform: scale(1.1); }
        .counters { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: nowrap; }
        .counter-box { flex: 1; min-width: 0; padding: 10px 5px; border-radius: 8px; text-align: center; background: #e3f2fd; border: 2px solid #64b5f6; }
        .counter-box.approved { background: #e8f5e9; border-color: #81c784; }
        .counter-box.rejected { background: #ffebee; border-color: #ef9a9a; }
        .counter-label { display: block; font-size: 10px; font-weight: bold; color: #555; margin-bottom: 4px; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
        .counter-value { display: block; font-size: 20px; font-weight: bold; color: #1565c0; }
        .counter-box.approved .counter-value { color: #2e7d32; }
        .counter-box.rejected .counter-value { color: #c62828; }
        .tabs { display: flex; width: 100%; margin-bottom: 0; border-radius: 8px 8px 0 0; overflow: hidden; border-bottom: 2px solid #e0e0e0; }
        .tab-btn { flex: 1; padding: 12px 2px; text-align: center; border: none; font-weight: bold; cursor: pointer; font-size: clamp(10px, 3.2vw, 14px); transition: 0.2s; display: flex; flex-direction: column; align-items: center; gap: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: white; opacity: 0.7;}
        .tab-btn:hover { opacity: 1; }
        .tab-btn.submit { background: linear-gradient(135deg, #1e88e5, #1565c0); }
        .tab-btn.approved { background: linear-gradient(135deg, #43a047, #2e7d32); }
        .tab-btn.rejected { background: linear-gradient(135deg, #e53935, #c62828); }
        .tab-btn.active { opacity: 1; box-shadow: inset 0 -4px 0 rgba(0,0,0,0.2); transform: scale(1.02); z-index: 1; }
        .list-section { border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px; overflow: hidden; background: white; }
        .report-list { max-height: 400px; overflow-y: auto; padding: 0; }
        .report-item { display: flex; align-items: center; justify-content: space-between; padding: 12px 10px; border-bottom: 1px solid #f0f0f0; white-space: nowrap; font-size: clamp(11px, 3.5vw, 13px); }
        .report-item:last-child { border-bottom: none; }
        .report-time { display: flex; align-items: center; gap: 4px; color: #555; font-weight: bold; overflow: hidden; text-overflow: ellipsis; margin-right: 8px;}
        .report-status { font-weight: bold; flex-shrink: 0; font-size: clamp(10px, 3vw, 12px);}
        .report-status.success { color: #2e7d32; }
        .report-status.error { color: #c62828; }
        .report-status.info { color: #1565c0; }
        .empty-msg { padding: 30px; text-align: center; color: #999; font-style: italic; font-size: 14px; }
        .count-badge { background: #ff9800; color: white; padding: 1px 5px; border-radius: 10px; font-size: 10px; font-weight: bold; margin-left: 4px; }
    </style>
</head>
<body>
    <div class="news-ticker">
        <div class="ticker-text">📢 নির্দেশনা:কাজ শুরু করার পূর্বে ও শেষ করার পরে অবশ্যই গ্রুপে জানাবেন, যাতে অন্যরাও কাজ করার সুযোগ পায়। কাজ শুরু বা শেষ এটা কনফার্ম করুন। অন্যথায় কাজের রিপোর্ট গ্রহণযোগ্য হবে না।🚨</div>
    </div>

    <div class="live-display">
        <h4>Trending Academy Limited</h4>
        <div id="welcomeMsg" class="welcome-msg">🌐 Welcome to Live Projects 🟢<span>CEO: MD. TAMIM</span></div>
        <div id="loader" class="loader-container">
            <div class="premium-spinner"></div>
            <div class="loader-text"> 06+ Follow Must ☑</div>
        </div>
        <div class="live-value" id="loginDisplay" onclick="copyToClipboard()"></div>
        <div class="copied-msg" id="copyMsg">✔ Copied </div>
    </div>

    <button id="btnAll2FA" class="send-all-2fa-btn" onclick="startAutoSequence(true)">Get Username</button>

    <div class="settings-area">
        <h4>বাটন কন্ট্রোল</h4>
        <div class="msg-input-group"><input type="text" id="m1" value="Tasks" readonly><button id="btn1" class="msg-send-btn" onclick="sendSpecific('m1', 'btn1', true)">Send</button></div>
        <div class="msg-input-group"><input type="text" id="m2" value="$0" readonly><button id="btn2" class="msg-send-btn" onclick="sendSpecific('m2', 'btn2', false)">Send</button></div>
        <div class="msg-input-group"><input type="text" id="m3" value="Create Inst (No mail)" readonly><button id="btn3" class="msg-send-btn" onclick="sendSpecific('m3', 'btn3', false)">Send</button></div>
        <div class="msg-input-group"><input type="text" id="m4" value="Start" readonly><button id="btn4" class="msg-send-btn" onclick="sendSpecific('m4', 'btn4', false)">Send</button></div>
    </div>

    <div class="manual-area">
        <h4>Cookies Submit Please</h4>
        <div class="manual-input-group">
            <textarea id="manualMsg" placeholder="Paste your Instragram Cookies..."></textarea>
            <button id="btnManual" class="manual-send-btn" onclick="sendManualMsg()">Submit Now</button>
        </div>
    </div>

    <div class="report-area">
        <h4>📊 Report Analytics</h4>
        <div class="filter-area">
            <div class="filter-group"><label>From:</label><input type="datetime-local" id="fromDate"></div>
            <div class="filter-group"><label>To:</label><input type="datetime-local" id="toDate"></div>
            <div class="btn-row">
                <button class="filter-btn" id="btnFilter" onclick="fetchReports(event)">🔍 Filter</button>
                <button class="filter-btn reset" onclick="resetFilter()">↺ Reset</button>
                <span class="lock-icon" id="lockIcon" onclick="toggleLock()" title="Lock Date/Time">🔓</span>
            </div>
        </div>
        <div class="counters">
            <div class="counter-box"><span class="counter-label">Total Submit</span><span class="counter-value" id="cntSubmit">0</span></div>
            <div class="counter-box approved"><span class="counter-label">Approved</span><span class="counter-value" id="cntApproved">0</span></div>
            <div class="counter-box rejected"><span class="counter-label">Rejected</span><span class="counter-value" id="cntRejected">0</span></div>
        </div>
        <div class="tabs">
            <button class="tab-btn submit active" id="tabBtn-submit" onclick="switchTab('submit')">📥<br>Submit</button>
            <button class="tab-btn approved" id="tabBtn-approved" onclick="switchTab('approved')">✅<br>Approved</button>
            <button class="tab-btn rejected" id="tabBtn-rejected" onclick="switchTab('rejected')">❌<br>Rejected</button>
        </div>
        <div class="list-section">
            <div id="tabContent-submit" class="report-list" style="display: block;"><div class="empty-msg">Loading data...</div></div>
            <div id="tabContent-approved" class="report-list" style="display: none;"><div class="empty-msg">Loading data...</div></div>
            <div id="tabContent-rejected" class="report-list" style="display: none;"><div class="empty-msg">Loading data...</div></div>
        </div>
    </div>

    <script>
        let lastLoginVal = "Welcome";
        let autoRefreshTimer = null;
        let isFetchingReports = false;
        let isLocked = false;
        let isManualSubmitting = false; 

        function initLock() {
            isLocked = localStorage.getItem('dateFilterLocked') === 'true';
            updateLockUI();
            if (isLocked) {
                const savedFrom = localStorage.getItem('savedFromDate');
                const savedTo = localStorage.getItem('savedToDate');
                if (savedFrom) document.getElementById('fromDate').value = savedFrom;
                if (savedTo) document.getElementById('toDate').value = savedTo;
            }
        }
        function toggleLock() {
            isLocked = !isLocked;
            localStorage.setItem('dateFilterLocked', isLocked);
            if (isLocked) {
                localStorage.setItem('savedFromDate', document.getElementById('fromDate').value);
                localStorage.setItem('savedToDate', document.getElementById('toDate').value);
            }
            updateLockUI();
        }
        function updateLockUI() {
            const lockIcon = document.getElementById('lockIcon');
            const fromInput = document.getElementById('fromDate');
            const toInput = document.getElementById('toDate');
            if (isLocked) {
                lockIcon.innerText = '🔒';
                lockIcon.style.color = '#d32f2f';
                fromInput.disabled = true;
                toInput.disabled = true;
            } else {
                lockIcon.innerText = '🔓';
                lockIcon.style.color = '#2e7d32';
                fromInput.disabled = false;
                toInput.disabled = false;
            }
        }

        async function fetchLogin() {
            try {
                const res = await fetch('/get_login');
                const data = await res.json();
                if (isManualSubmitting && (data.login === "Submit Done ✅" || data.login === "Submit Done")) return;
                if (data.login && data.login !== lastLoginVal) {
                    lastLoginVal = data.login;
                    const display = document.getElementById('loginDisplay');
                    const loader = document.getElementById('loader');
                    const welcome = document.getElementById('welcomeMsg');
                    if (lastLoginVal === "Loading..." || lastLoginVal === "Processing..." || lastLoginVal.includes("Creating")) {
                        welcome.style.display = 'none';
                        loader.style.display = 'flex';
                        display.style.display = 'none';
                    } else if (lastLoginVal === "Welcome") {
                        welcome.style.display = 'block';
                        loader.style.display = 'none';
                        display.style.display = 'none';
                    } else {
                        welcome.style.display = 'none';
                        loader.style.display = 'none';
                        display.style.display = 'block';
                        display.innerText = lastLoginVal; 
                        display.title = lastLoginVal;
                        if (lastLoginVal.includes("Successful") || lastLoginVal.includes("Done") || lastLoginVal.includes("✅")) {
                            display.classList.add('success-text');
                        } else {
                            display.classList.remove('success-text');
                        }
                    }
                }
            } catch(e) {}
        }
        setInterval(fetchLogin, 100);
        window.onload = fetchLogin;

        function copyToClipboard() {
            let text = document.getElementById('loginDisplay').innerText;
            if (text === "" || text.includes("Report") || text.includes("Successful") || text.includes("Welcome")) return;
            navigator.clipboard.writeText(text).then(() => {
                const copyMsg = document.getElementById('copyMsg');
                copyMsg.style.display = 'block';
                setTimeout(() => { copyMsg.style.display = 'none'; }, 2000);
            }).catch(err => {});
        }

        async function startAutoSequence(with2FA) {
            const btnAll2FA = document.getElementById('btnAll2FA');
            btnAll2FA.disabled = true;
            document.getElementById('welcomeMsg').style.display = 'none';
            document.getElementById('loginDisplay').style.display = 'none';
            document.getElementById('loader').style.display = 'flex';
            lastLoginVal = "Loading...";
            const originalText = "Get Username";
            const buttons = [
                { id: 'm1', btnId: 'btn1', isStart: true, percent: 25 },
                { id: 'm2', btnId: 'btn2', isStart: false, percent: 50 },
                { id: 'm3', btnId: 'btn3', isStart: false, percent: 75 },
                { id: 'm4', btnId: 'btn4', isStart: false, percent: 100 }
            ];
            for (let i = 0; i < buttons.length; i++) {
                const item = buttons[i];
                await sendSpecific(item.id, item.btnId, item.isStart);
                btnAll2FA.innerText = `Processing... ${item.percent}%`;
                if (i < buttons.length - 1) await new Promise(r => setTimeout(r, 300));
            }
            if (with2FA) {
                btnAll2FA.innerText = `Processing... (100%)`;
                await new Promise(r => setTimeout(r, 300));
                try { await fetch('/send_2fa', { method: 'POST' }); } catch(e) {}
            }
            btnAll2FA.innerText = originalText;
            btnAll2FA.disabled = false;
        }

        async function sendSpecific(inputId, btnId, isStart) {
            const text = document.getElementById(inputId).value;
            const btn = document.getElementById(btnId);
            if(!text || btn.disabled) return;
            btn.disabled = true;
            document.getElementById('welcomeMsg').style.display = 'none';
            document.getElementById('loginDisplay').style.display = 'none';
            document.getElementById('loader').style.display = 'flex';
            lastLoginVal = "Loading...";
            try {
                await fetch('/click_button_by_text', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({btn_text: text, is_start: isStart})
                });
            } catch (e) {}
            let timeLeft = 2;
            btn.innerText = `Wait ${timeLeft}s`;
            const ci = setInterval(() => {
                timeLeft--;
                if (timeLeft > 0) { btn.innerText = `Wait ${timeLeft}s`; }
                else { clearInterval(ci); btn.disabled = false; btn.innerText = "Send"; }
            }, 500);
        }

        async function sendManualMsg() {
            const input = document.getElementById('manualMsg');
            const btn = document.getElementById('btnManual');
            const text = input.value.trim();
            if(!text || btn.disabled) return;
            isManualSubmitting = true; 
            btn.disabled = true;
            btn.innerText = "Processing..";
            document.getElementById('welcomeMsg').style.display = 'none';
            document.getElementById('loginDisplay').style.display = 'none';
            document.getElementById('loader').style.display = 'flex';
            lastLoginVal = "Loading...";
            try {
                await fetch('/send_manual_msg', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });
                input.value = '';
                await new Promise(r => setTimeout(r, 1000));
                await fetch('/send_manual_registered', { method: 'POST' });
            } catch (e) {}
            setTimeout(() => {
                btn.disabled = false;
                btn.innerText = "Submit Now"; 
                isManualSubmitting = false;
                showSuccessAndRevert();
            }, 3000);
        }

        function showSuccessAndRevert() {
            const display = document.getElementById('loginDisplay');
            const loader = document.getElementById('loader');
            const welcome = document.getElementById('welcomeMsg');
            welcome.style.display = 'none';
            loader.style.display = 'none';
            display.style.display = 'block';
            display.innerText = "Submit Done ✅";
            display.classList.add('success-text');
            lastLoginVal = "Submit Done ✅";
            setTimeout(async () => {
                welcome.style.display = 'block';
                display.style.display = 'none';
                display.classList.remove('success-text');
                lastLoginVal = "Welcome";
                try { await fetch('/reset_welcome', { method: 'POST' }); } catch(e) {}
            }, 5000);
        }

        function escapeHtml(s) {
            return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
        }
        function formatDate(isoString) {
            const d = new Date(isoString);
            const day = String(d.getDate()).padStart(2, '0');
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const year = d.getFullYear();
            let hours = d.getHours();
            const minutes = String(d.getMinutes()).padStart(2, '0');
            const seconds = String(d.getSeconds()).padStart(2, '0');
            const ampm = hours >= 12 ? 'PM' : 'AM';
            hours = hours % 12;
            hours = hours ? hours : 12;
            const strHours = String(hours).padStart(2, '0');
            return `${day}/${month}/${year}, ${strHours}:${minutes}:${seconds} ${ampm}`;
        }

        async function fetchReports(event) {
            if (isFetchingReports) return;
            isFetchingReports = true;
            const btn = document.getElementById('btnFilter');
            if (event && event.type === 'click') {
                btn.disabled = true;
                btn.innerText = "Loading...";
            }
            const fromVal = document.getElementById('fromDate').value;
            const toVal = document.getElementById('toDate').value;
            const start = fromVal ? new Date(fromVal).toISOString() : null;
            const end = toVal ? new Date(toVal).toISOString() : null;
            try {
                const res = await fetch('/get_reports', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ start: start, end: end })
                });
                const data = await res.json();
                if (data.error) {
                    console.error("Error: " + data.error);
                    return;
                }
                document.getElementById('cntSubmit').innerText = data.total_submit;
                document.getElementById('cntApproved').innerText = data.approved;
                document.getElementById('cntRejected').innerText = data.rejected;
                renderTabList('tabContent-submit', data.submit_list, 'submit');
                renderTabList('tabContent-approved', data.approved_list, 'approved');
                renderTabList('tabContent-rejected', data.rejected_list, 'rejected');
            } catch (e) {
                console.error("Failed: " + e.message);
            } finally {
                isFetchingReports = false;
                if (event && event.type === 'click') {
                    btn.disabled = false;
                    btn.innerText = "🔍 Filter";
                }
            }
        }

        function renderTabList(id, items, type) {
            const container = document.getElementById(id);
            if (!items || items.length === 0) {
                container.innerHTML = '<div class="empty-msg">No data found in this time range</div>';
                return;
            }
            let icon = "📥";
            let text = "Report Submitted";
            let className = "info";
            if (type === 'approved') {
                icon = "✅";
                text = "Report Verified";
                className = "success";
            } else if (type === 'rejected') {
                icon = "❌";
                text = "Report Rejected";
                className = "error";
            }
            container.innerHTML = items.map(item => {
                const localTime = formatDate(item.time);
                const badge = item.count > 1 ? `<span class="count-badge">×${item.count}</span>` : '';
                return `<div class="report-item">
                    <div class="report-time">🕐 ${escapeHtml(localTime)} ${badge}</div>
                    <div class="report-status ${className}">${icon} ${text}</div>
                </div>`;
            }).join('');
        }

        function switchTab(tabName) {
            document.getElementById('tabContent-submit').style.display = 'none';
            document.getElementById('tabContent-approved').style.display = 'none';
            document.getElementById('tabContent-rejected').style.display = 'none';
            document.getElementById('tabBtn-submit').classList.remove('active');
            document.getElementById('tabBtn-approved').classList.remove('active');
            document.getElementById('tabBtn-rejected').classList.remove('active');
            document.getElementById('tabContent-' + tabName).style.display = 'block';
            document.getElementById('tabBtn-' + tabName).classList.add('active');
        }

        function resetFilter() {
            document.getElementById('fromDate').value = '';
            document.getElementById('toDate').value = '';
            if (isLocked) {
                localStorage.removeItem('savedFromDate');
                localStorage.removeItem('savedToDate');
            }
            fetchReports();
        }

        window.addEventListener('DOMContentLoaded', () => {
            initLock();
            fetchReports(null); 
            autoRefreshTimer = setInterval(() => fetchReports(null), 10000); 
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/get_login')
def get_login():
    global latest_message
    return jsonify({"login": latest_message})

@app.route('/reset_welcome', methods=['POST'])
def reset_welcome():
    global latest_message
    latest_message = "Welcome"
    return jsonify({'status': 'ok'})

# ==========================================
# Threading দিয়ে ফিক্স করা রুটগুলো
# ==========================================
@app.route('/get_reports', methods=['POST'])
def get_reports():
    data = request.get_json() or {}
    start_str = data.get('start')
    end_str = data.get('end')

    def parse_dt(s):
        if not s: return None
        try:
            dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

    start_dt = parse_dt(start_str)
    end_dt = parse_dt(end_str)

    def fetch_data_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run():
            await sync_reports_from_telegram()
            result = {'total_submit': 0, 'approved': 0, 'rejected': 0, 'submit_list': [], 'approved_list': [], 'rejected_list': []}
            for item in report_cache:
                mdate = item['date']
                if mdate.tzinfo is None: mdate = mdate.replace(tzinfo=timezone.utc)
                else: mdate = mdate.astimezone(timezone.utc)
                if start_dt is not None and mdate < start_dt: continue
                if end_dt is not None and mdate > end_dt: continue
                iso_time = mdate.isoformat()
                if item['ds_cnt'] > 0:
                    result['total_submit'] += item['ds_cnt']
                    result['submit_list'].append({'time': iso_time, 'count': item['ds_cnt']})
                if item['ap_cnt'] > 0:
                    result['approved'] += item['ap_cnt']
                    result['approved_list'].append({'time': iso_time, 'count': item['ap_cnt']})
                if item['rj_cnt'] > 0:
                    result['rejected'] += item['rj_cnt']
                    result['rejected_list'].append({'time': iso_time, 'count': item['rj_cnt']})
            return result

        try:
            res_data = loop.run_until_complete(run())
        except Exception as e:
            res_data = {'error': str(e)}
        finally:
            loop.close()
        return res_data

    # থ্রেডে রান করে ডেটা নেওয়া হচ্ছে
    result_container = []
    t = threading.Thread(target=lambda: result_container.append(fetch_data_thread()))
    t.start()
    t.join()

    if result_container and 'error' in result_container[0]:
        return jsonify({'error': result_container[0]['error']}), 500
    return jsonify(result_container[0])

@app.route('/click_button_by_text', methods=['POST'])
def click_button_by_text():
    global latest_message, is_username_shown, is_waiting_for_report
    data = request.get_json()
    btn_text = data.get('btn_text', '')
    is_start = data.get('is_start', False)

    latest_message = "Loading..."
    is_username_shown = False
    is_waiting_for_report = False

    def action_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def run():
            try:
                if is_start:
                    await client.send_message(TARGET_BOT, "/start")
                    await asyncio.sleep(0.7)
                await find_and_click_button(btn_text)
                await asyncio.sleep(0.7)
            except Exception:
                pass
        loop.run_until_complete(run())
        loop.close()

    t = threading.Thread(target=action_thread)
    t.start()
    t.join()

    return jsonify({'status': 'ok'})

@app.route('/send_manual_msg', methods=['POST'])
def send_manual_msg():
    global latest_message
    data = request.get_json()
    text = data.get('text', '')
    if not text: return jsonify({'status': 'error'})

    latest_message = "Loading..."

    def action_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def run():
            try:
                await client.send_message(TARGET_BOT, text)
            except Exception:
                pass
        loop.run_until_complete(run())
        loop.close()

    t = threading.Thread(target=action_thread)
    t.start()
    t.join()

    return jsonify({'status': 'ok'})

@app.route('/send_manual_registered', methods=['POST'])
def send_manual_registered():
    global is_waiting_for_report, is_username_shown
    is_waiting_for_report = True
    is_username_shown = True

    def action_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def run():
            try:
                await client.send_message(TARGET_BOT, "✅ Account registered")
                await asyncio.sleep(2)
                await client.send_message(TARGET_BOT, "✅ Yes, I made 5+ subscriptions")
            except Exception:
                pass
        loop.run_until_complete(run())
        loop.close()

    t = threading.Thread(target=action_thread)
    t.start()
    t.join()

    return jsonify({'status': 'ok'})

@app.route('/send_2fa', methods=['POST'])
def send_2fa():
    def action_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def run():
            try:
                await client.send_message(TARGET_BOT, "BQQ6 SYLR NRVW 5DWH")
            except Exception:
                pass
        loop.run_until_complete(run())
        loop.close()

    t = threading.Thread(target=action_thread)
    t.start()
    t.join()

    return jsonify({'status': 'ok'})

# ==========================================
# Startup Logic (Termux + Render)
# ==========================================
def start_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client.connect())
        if not loop.run_until_complete(client.is_user_authorized()):
            print("❌ Session not authorized!")
        else:
            print("✅ Telegram Connected Successfully!")
    except Exception as e:
        print("❌ Connection Error:", e)
    
    loop.run_until_complete(client.run_until_disconnected())

if __name__ == '__main__':
    print("Connecting..")
    t = threading.Thread(target=start_telegram_bot, daemon=True)
    t.start()
    time.sleep(3)
    print("✅ Website running...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)

# Version 5.0 - Simple + Load Free (No Report Section)

import asyncio
import re
import os
import threading
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
# FIX: Single Event Loop + Lock (deadlock প্রতিরোধ)
# ==========================================
_tg_lock = threading.Lock()
_loop = None
_loop_thread = None

def _start_event_loop():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

def start_loop():
    global _loop_thread
    _loop_thread = threading.Thread(target=_start_event_loop, daemon=True)
    _loop_thread.start()

def run_async(coro, timeout=20):
    """Thread-safe, timeout সহ coroutine চালায়। কখনো hang করবে না।"""
    if _loop is None:
        return None
    with _tg_lock:
        future = asyncio.run_coroutine_threadsafe(
            asyncio.wait_for(coro, timeout=timeout),
            _loop
        )
        try:
            return future.result(timeout=timeout + 5)
        except Exception as e:
            print(f"[run_async] {e}")
            return None

# ==========================================
# টেলিগ্রাম লিসেনার
# ==========================================
@client.on(events.NewMessage(from_users=TARGET_BOT))
async def on_bot_reply(event):
    global latest_message, is_username_shown, is_waiting_for_report
    text = event.text or ""
    if not text.strip():
        return

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
                        if hasattr(btn_str, 'text'):
                            btn_str = btn_str.text

                        btn_key = f"{message.id}_{btn_str}"
                        is_match = False

                        if "$0" in btn_text:
                            if re.search(r'\$0', str(btn_str)):
                                is_match = True
                        elif str(btn_text).lower() in str(btn_str).lower():
                            is_match = True

                        if is_match:
                            if btn_key in clicked_buttons:
                                return "already_clicked"
                            await btn.click()
                            clicked_buttons.add(btn_key)
                            return True
        return False
    except Exception:
        return False

# ==========================================
# HTML (শুধু উপরের অংশ)
# ==========================================
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Control Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 15px; background-color: #e9ebee; margin: 0; }

        .news-ticker {
            width: 100%; background: #c62828; color: white; padding: 8px 0; overflow: hidden;
            white-space: nowrap; position: relative; margin-bottom: 15px; border-radius: 5px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        .ticker-text {
            display: inline-block; padding-left: 100%; animation: tickerAnim 15s linear infinite;
            font-weight: bold; font-size: 14px;
        }
        @keyframes tickerAnim {
            0% { transform: translate3d(0, 0, 0); }
            100% { transform: translate3d(-100%, 0, 0); }
        }

        .live-display {
            text-align: center; padding: 25px 15px; background: linear-gradient(135deg, #e3f2fd, #bbdefb);
            border: 2px solid #64b5f6; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 6px 15px rgba(0,0,0,0.1);
            min-height: 130px; display: flex; flex-direction: column; justify-content: center; align-items: center;
            width: 100%; box-sizing: border-box;
        }
        .live-display h4 {
            margin: 0 0 15px 0;
            font-size: clamp(18px, 4.5vw, 26px);
            font-weight: 900;
            background: linear-gradient(90deg, #0d47a1, #1976d2, #0d47a1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
            letter-spacing: 2px;
            width: 100%;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .loader-container {
            display: none; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
        }
        .premium-spinner {
            width: 35px; height: 35px; border: 3px solid rgba(21, 101, 192, 0.15);
            border-top: 3px solid #1565c0; border-right: 3px solid #1565c0;
            border-radius: 50%; animation: spin 0.8s cubic-bezier(0.68, -0.55, 0.27, 1.55) infinite;
            box-shadow: 0 0 10px rgba(21, 101, 192, 0.2);
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .loader-text { font-size: 13px; font-weight: bold; color: #1565c0; letter-spacing: 1px; text-transform: uppercase; animation: pulseText 1.5s infinite; }
        @keyframes pulseText { 0% { opacity: 0.7; } 50% { opacity: 1; } 100% { opacity: 0.7; } }

        .welcome-msg {
            display: block; color: #1565c0; font-size: clamp(16px, 4.5vw, 22px); font-weight: bold; line-height: 1.4;
            text-align: center; white-space: nowrap;
        }
        .welcome-msg span { font-size: clamp(12px, 3.5vw, 16px); color: #d32f2f; display: block; margin-top: 8px;}

        .live-value {
            display: none; background: #ffffff; color: #1565c0; border: 2px solid #90caf9;
            padding: 12px 15px; border-radius: 10px; font-weight: 800;
            font-size: clamp(18px, 5vw, 26px);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            width: calc(100% - 10px); box-sizing: border-box;
            cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.1); transition: all 0.2s;
            text-align: center;
        }
        .live-value:hover { background: #f0f8ff; transform: scale(1.01); }
        .live-value.success-text { color: #2e7d32; border-color: #81c784; background: #e8f5e9; }

        .copied-msg { font-size: 12px; color: #28a745; font-weight: bold; display: none; margin-top: 8px; }

        .send-all-2fa-btn {
            background: linear-gradient(135deg, #1d4ed8, #3b82f6);
            color: white; border: none; padding: 12px 18px; border-radius: 8px;
            cursor: pointer; font-weight: bold; font-size: 16px; width: 100%;
            margin-bottom: 20px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
            transition: 0.2s; text-transform: uppercase; letter-spacing: 0.5px;
        }
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
    </style>
</head>
<body>

    <div class="news-ticker">
        <div class="ticker-text">📢 নির্দেশনা:কাজ শুরু করার পূর্বে ও শেষ করার পরে অবশ্যই গ্রুপে জানাবেন, যাতে অন্যরাও কাজ করার সুযোগ পায়। কাজ শুরু বা শেষ এটা কনফার্ম করুন। অন্যথায় কাজের রিপোর্ট গ্রহণযোগ্য হবে না।🚨</div>
    </div>

    <div class="live-display">
        <h4>Trending Academy Limited</h4>

        <div id="welcomeMsg" class="welcome-msg">
            🌐 Welcome to Live Projects 🟢
            <span>CEO: MD. TAMIM</span>
        </div>

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
        <div class="msg-input-group">
            <input type="text" id="m1" value="Tasks" readonly>
            <button id="btn1" class="msg-send-btn" onclick="sendSpecific('m1', 'btn1', true)">Send</button>
        </div>
        <div class="msg-input-group">
            <input type="text" id="m2" value="$0" readonly>
            <button id="btn2" class="msg-send-btn" onclick="sendSpecific('m2', 'btn2', false)">Send</button>
        </div>
        <div class="msg-input-group">
            <input type="text" id="m3" value="Create Inst (No mail)" readonly>
            <button id="btn3" class="msg-send-btn" onclick="sendSpecific('m3', 'btn3', false)">Send</button>
        </div>
        <div class="msg-input-group">
            <input type="text" id="m4" value="Start" readonly>
            <button id="btn4" class="msg-send-btn" onclick="sendSpecific('m4', 'btn4', false)">Send</button>
        </div>
    </div>

    <div class="manual-area">
        <h4>Cookies Submit Please</h4>
        <div class="manual-input-group">
            <textarea id="manualMsg" placeholder="Paste your Instragram Cookies..."></textarea>
            <button id="btnManual" class="manual-send-btn" onclick="sendManualMsg()">Submit Now</button>
        </div>
    </div>

    <script>
        let lastLoginVal = "Welcome";
        let isManualSubmitting = false;
        let polling = false;

        async function fetchLogin() {
            if (polling) return;
            polling = true;
            try {
                const res = await fetch('/get_login');
                const data = await res.json();

                if (isManualSubmitting && (data.login === "Submit Done ✅" || data.login === "Submit Done")) {
                    return;
                }

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
            finally { polling = false; }
        }
        setInterval(fetchLogin, 1000);
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

                if (i < buttons.length - 1) {
                    await new Promise(r => setTimeout(r, 300));
                }
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
    </script>
</body>
</html>
'''

# ==========================================
# Routes
# ==========================================
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

@app.route('/click_button_by_text', methods=['POST'])
def click_button_by_text():
    global latest_message, is_username_shown, is_waiting_for_report
    data = request.get_json()
    btn_text = data.get('btn_text', '')
    is_start = data.get('is_start', False)

    latest_message = "Loading..."
    is_username_shown = False
    is_waiting_for_report = False

    async def action():
        try:
            if is_start:
                await client.send_message(TARGET_BOT, "/start")
                await asyncio.sleep(0.7)
            result = await find_and_click_button(btn_text)
            await asyncio.sleep(0.7)
            return result
        except Exception:
            return False

    result = run_async(action(), timeout=20)

    if result == "already_clicked":
        return jsonify({'status': 'error', 'msg': 'এই বাটনে আগেই ক্লিক করা হয়েছে!'})
    elif result:
        return jsonify({'status': 'ok'})
    else:
        # ✅ Hang হলে loader আটকে না থাকার জন্য welcome এ ফেরত
        if latest_message == "Loading...":
            latest_message = "Welcome"
        return jsonify({'status': 'error', 'msg': 'বাটনটি পাওয়া যায়নি!'})

@app.route('/send_manual_msg', methods=['POST'])
def send_manual_msg():
    global latest_message
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({'status': 'error'})

    latest_message = "Loading..."

    async def send_action():
        try:
            await client.send_message(TARGET_BOT, text)
            return True
        except Exception:
            return False

    success = run_async(send_action(), timeout=20)
    if not success and latest_message == "Loading...":
        latest_message = "Welcome"
    return jsonify({'status': 'ok' if success else 'error'})

@app.route('/send_manual_registered', methods=['POST'])
def send_manual_registered():
    global is_waiting_for_report, is_username_shown
    is_waiting_for_report = True
    is_username_shown = True

    async def send_action():
        try:
            await client.send_message(TARGET_BOT, "✅ Account registered")
            await asyncio.sleep(2)
            await client.send_message(TARGET_BOT, "✅ Yes, I made 5+ subscriptions")
            return True
        except Exception:
            return False

    success = run_async(send_action(), timeout=20)
    return jsonify({'status': 'ok' if success else 'error'})

@app.route('/send_2fa', methods=['POST'])
def send_2fa():
    async def send_action():
        try:
            await client.send_message(TARGET_BOT, "BQQ6 SYLR NRVW 5DWH")
            return True
        except Exception:
            return False

    success = run_async(send_action(), timeout=20)
    return jsonify({'status': 'ok' if success else 'error'})

# ==========================================
# Main
# ==========================================
if __name__ == '__main__':
    print("Connecting..")
    start_loop()   # background event loop চালু

    async def _connect():
        await client.connect()
        if not await client.is_user_authorized():
            raise Exception("Session invalid!")

    run_async(_connect(), timeout=30)
    print("Success! Website running...")

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)

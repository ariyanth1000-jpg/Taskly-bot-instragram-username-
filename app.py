# Version 3.7 - Render Deployment Ready

import asyncio
import re
import os
import threading
import time
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from telethon import TelegramClient, events
from telethon.sessions import StringSession

app = Flask(__name__)

# Render-এর Environment Variable থেকে ডেটা নেওয়া হচ্ছে (লোকালে config.py কাজ করবে)
try:
    import config
    api_id = config.API_ID
    api_hash = config.API_HASH
    session_str = config.SESSION_STR
except ImportError:
    api_id = int(os.environ.get('API_ID', 0))
    api_hash = os.environ.get('API_HASH', '')
    session_str = os.environ.get('SESSION_STR', '')

TARGET_BOT = '@Taskl1_bot' 

client = TelegramClient(StringSession(session_str), api_id, api_hash)

clicked_buttons = set() 
latest_message = "Username Creating....." 

# স্টেট ভেরিয়েবল
is_username_shown = False 
is_waiting_for_report = False 

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
    
    # ১. ইউজারনেম চেক
    for line in lines:
        if "Login:" in line:
            username = line.replace("Login:", "").replace("`", "").strip()
            latest_message = f"Username ☞ {username}"
            is_username_shown = True 
            is_waiting_for_report = False
            return 

    # ২. রিপোর্ট চেক (যদি অপেক্ষায় থাকি)
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
    except Exception as e:
        return False

# ==========================================
# ওয়েবসাইট ডিজাইন
# ==========================================
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Control Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 15px; background-color: #e9ebee; margin: 0; }
        
        .live-display { 
            text-align: center; padding: 20px 15px; background: linear-gradient(135deg, #e3f2fd, #bbdefb); 
            border: 2px solid #64b5f6; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 6px 15px rgba(0,0,0,0.1); 
            min-height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center;
        }
        .live-display h4 { margin: 0 0 10px 0; font-size: 14px; color: #1565c0; text-transform: uppercase; letter-spacing: 1px;}
        
        .live-value { 
            font-size: 20px; font-weight: bold; color: #d32f2f; white-space: nowrap; overflow: hidden; 
            text-overflow: ellipsis; cursor: pointer; padding: 5px 10px; border-radius: 5px; transition: background 0.2s, color 0.2s; width: 100%; box-sizing: border-box;
        }
        .live-value.success-text { color: #2e7d32; }
        
        .live-value:hover { background: rgba(255,255,255,0.6); }
        .copied-msg { font-size: 12px; color: #28a745; font-weight: bold; display: none; margin-top: 5px; }
        .pulse { animation: pulseAnim 1s infinite; }
        @keyframes pulseAnim { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }

        .send-all-2fa-btn { background: #0078FF; color: white; border: none; padding: 18px; border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 20px; width: 100%; margin-bottom: 20px; box-shadow: 0 6px 12px rgba(0, 120, 255, 0.3); transition: 0.2s;}
        .send-all-2fa-btn:hover { background: #005bb5; transform: scale(1.02); }
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
    <div class="live-display">
        <h4>Trending Academy Limited </h4>
        <div class="live-value" id="loginDisplay" onclick="copyToClipboard()">Username Creating Robot</div>
        <div class="copied-msg" id="copyMsg">✔ Copied </div>
    </div>

    <button id="btnAll2FA" class="send-all-2fa-btn" onclick="startAutoSequence(true)">🚀 Get Instragram Username</button>

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
        let lastLoginVal = "Processing..";

        async function fetchLogin() {
            try {
                const res = await fetch('/get_login');
                const data = await res.json();
                if (data.login && data.login !== lastLoginVal) {
                    lastLoginVal = data.login;
                    const display = document.getElementById('loginDisplay');
                    display.innerText = lastLoginVal;
                    display.title = lastLoginVal;
                    
                    if (lastLoginVal.includes("Submit Done")) {
                        display.classList.add('success-text');
                        display.classList.add('pulse');
                        setTimeout(() => display.classList.remove('pulse'), 2000);
                    } else {
                        display.classList.remove('success-text');
                        if (lastLoginVal !== "Username Creating...") {
                            display.classList.add('pulse');
                            setTimeout(() => display.classList.remove('pulse'), 2000);
                        }
                    }
                }
            } catch(e) {}
        }
        
        setInterval(fetchLogin, 100);
        window.onload = fetchLogin;

        function copyToClipboard() {
            let text = document.getElementById('loginDisplay').innerText;
            if (text === "Username Creating...." || text === "") return;
            if (text.includes("Username ☞ ")) { text = text.replace("Username ☞ ", ""); }

            navigator.clipboard.writeText(text).then(() => {
                const copyMsg = document.getElementById('copyMsg');
                copyMsg.style.display = 'block';
                setTimeout(() => { copyMsg.style.display = 'none'; }, 2000);
            }).catch(err => {});
        }

        async function startAutoSequence(with2FA) {
            const btnAll2FA = document.getElementById('btnAll2FA');
            btnAll2FA.disabled = true;
            
            document.getElementById('loginDisplay').innerText = "Username Creating......";
            lastLoginVal = "অপেক্ষা করা হচ্ছে...";
            
            const originalText = "🚀 Get Instragram Username";

            const buttons = [
                { id: 'm1', btnId: 'btn1', isStart: true, percent: 25 },
                { id: 'm2', btnId: 'btn2', isStart: false, percent: 50 },
                { id: 'm3', btnId: 'btn3', isStart: false, percent: 75 },
                { id: 'm4', btnId: 'btn4', isStart: false, percent: 100 }
            ];

            for (let i = 0; i < buttons.length; i++) {
                const item = buttons[i];
                
                await sendSpecific(item.id, item.btnId, item.isStart);
                
                btnAll2FA.innerText = `🚀 Processing... ${item.percent}%`;
                
                if (i < buttons.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }
            }

            if (with2FA) {
                btnAll2FA.innerText = `🚀 Get Instragram Username... (100%)`;
                await new Promise(resolve => setTimeout(resolve, 3000)); 
                try {
                    await fetch('/send_2fa', { method: 'POST' });
                } catch(e) {}
            }

            btnAll2FA.innerText = originalText;
            btnAll2FA.disabled = false;
        }

        async function sendSpecific(inputId, btnId, isStart) {
            const text = document.getElementById(inputId).value;
            const btn = document.getElementById(btnId);
            if(!text || btn.disabled) return;

            btn.disabled = true;
            document.getElementById('loginDisplay').innerText = "Username Creating......";
            lastLoginVal = "Username Creating...";

            try {
                await fetch('/click_button_by_text', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({btn_text: text, is_start: isStart})
                });
            } catch (e) {}

            let timeLeft = 5;
            btn.innerText = `Wait ${timeLeft}s`;

            const countdownInterval = setInterval(() => {
                timeLeft--;
                if (timeLeft > 0) {
                    btn.innerText = `Wait ${timeLeft}s`;
                } else {
                    clearInterval(countdownInterval);
                    btn.disabled = false;
                    btn.innerText = "Send";
                }
            }, 1000);
        }

        async function sendManualMsg() {
            const input = document.getElementById('manualMsg');
            const btn = document.getElementById('btnManual');
            const text = input.value.trim();

            if(!text || btn.disabled) return;

            btn.disabled = true;
            btn.innerText = "Processing..";

            document.getElementById('loginDisplay').innerText = "অপেক্ষা করা হচ্ছে...";
            lastLoginVal = "Processing...";
            document.getElementById('loginDisplay').classList.remove('success-text');

            try {
                await fetch('/send_manual_msg', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });
                input.value = ''; 

                await new Promise(resolve => setTimeout(resolve, 3000));
                await fetch('/send_manual_registered', { method: 'POST' });

            } catch (e) {}

            setTimeout(() => {
                btn.disabled = false;
                btn.innerText = "Submit Now";
            }, 6000);
        }
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

@app.route('/click_button_by_text', methods=['POST'])
def click_button_by_text():
    global latest_message, is_username_shown, is_waiting_for_report
    data = request.get_json()
    btn_text = data.get('btn_text', '')
    is_start = data.get('is_start', False)

    latest_message = "Processing.." 
    is_username_shown = False
    is_waiting_for_report = False

    async def action():
        try:
            if is_start:
                await client.send_message(TARGET_BOT, "/start")
                await asyncio.sleep(2) 
            
            result = await find_and_click_button(btn_text)
            await asyncio.sleep(2)
            return result
        except Exception as e:
            return False

    result = client.loop.run_until_complete(action())
    
    if result == "already_clicked":
        return jsonify({'status': 'error', 'msg': 'এই বাটনে আগেই ক্লিক করা হয়েছে!'})
    elif result:
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'status': 'error', 'msg': 'বাটনটি পাওয়া যায়নি!'})

@app.route('/send_manual_msg', methods=['POST'])
def send_manual_msg():
    data = request.get_json()
    text = data.get('text', '')
    if not text: return jsonify({'status': 'error'})
    
    async def send_action():
        try:
            await client.send_message(TARGET_BOT, text)
            return True
        except Exception as e:
            return False

    success = client.loop.run_until_complete(send_action())
    return jsonify({'status': 'ok' if success else 'error'})

@app.route('/send_manual_registered', methods=['POST'])
def send_manual_registered():
    global is_waiting_for_report, is_username_shown
    is_waiting_for_report = True 
    is_username_shown = True 
    
    async def send_action():
        try:
            await client.send_message(TARGET_BOT, "✅ Account registered")
            return True
        except Exception as e:
            return False

    success = client.loop.run_until_complete(send_action())
    return jsonify({'status': 'ok' if success else 'error'})

@app.route('/send_2fa', methods=['POST'])
def send_2fa():
    async def send_action():
        try:
            await client.send_message(TARGET_BOT, "BQQ6 SYLR NRVW 5DWH")
            return True
        except Exception as e:
            return False

    success = client.loop.run_until_complete(send_action())
    return jsonify({'status': 'ok' if success else 'error'})


# ==========================================
# Render-এর জন্য নতুন স্টার্টআপ ব্লক
# ==========================================
def start_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.start())
    print("টেলিগ্রাম কানেক্টেড!")
    loop.run_until_complete(client.run_until_disconnected())

if __name__ == '__main__':
    print("Connecting..")
    # Render-এ টেলিগ্রামকে আলাদা থ্রেডে চালানো হচ্ছে
    t = threading.Thread(target=start_telegram_bot, daemon=True)
    t.start()
    time.sleep(3) # কানেক্ট হওয়ার জন্য অপেক্ষা

    print("Success! Website running...")
    # Render-এর ডাইনামিক পোর্ট নেওয়া হচ্ছে
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)

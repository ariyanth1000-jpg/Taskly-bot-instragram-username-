# Version 5.0 - Professional Minimal Look + Live Counter Sync

import asyncio
import re
import os
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
# রিপোর্ট ক্যাশ সিস্টেম (Live Sync)
# ==========================================
report_cache = {}

async def sync_reports_from_telegram():
    global report_cache
    new_cache = {}
    try:
        # টেলিগ্রাম থেকে ডেটা রিড করা
        async for msg in client.iter_messages(TARGET_BOT, limit=3000):
            text = msg.text or ""
            if not text:
                continue

            ds_cnt = text.count("ds_user_id")
            ap_cnt = len(re.findall(r'report approved', text, re.IGNORECASE))
            rj_cnt = len(re.findall(r'report rejected', text, re.IGNORECASE))

            # মেসেজ ডিলিট হলে এখানে থাকবে না, তাই লাইভ আপডেট হবে
            if ds_cnt > 0 or ap_cnt > 0 or rj_cnt > 0:
                report_cache[msg.id] = {
                    'id': msg.id,
                    'date': msg.date,
                    'ds_cnt': ds_cnt,
                    'ap_cnt': ap_cnt,
                    'rj_cnt': rj_cnt
                }
    except Exception as e:
        print(f"Sync Error: {e}")
        return

    # পুরনো ক্যাশ মুছে ফেলা
    report_cache = new_cache

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
# HTML
# ==========================================
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Control Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root { --primary: #2563eb; --bg: #f8fafc; --card: #ffffff; --text: #1e293b; --success: #10b981; --danger: #ef4444; }
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 15px; background-color: var(--bg); margin: 0; color: var(--text); }

        /* News Ticker */
        .news-ticker { width: 100%; background: #0f172a; color: #f8fafc; padding: 8px 0; overflow: hidden; white-space: nowrap; border-radius: 8px; margin-bottom: 20px; font-size: 13px;}
        .ticker-text { display: inline-block; padding-left: 100%; animation: tickerAnim 20s linear infinite; font-weight: 600; letter-spacing: 0.5px;}
        @keyframes tickerAnim { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

        /* Live Display */
        .live-display { text-align: center; padding: 24px 16px; background: var(--card); border-radius: 16px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); min-height: 140px; display: flex; flex-direction: column; justify-content: center; align-items: center; border: 1px solid #e2e8f0;}
        .live-display h4 { margin: 0 0 16px 0; font-size: clamp(16px, 4vw, 22px); font-weight: 800; color: var(--text); text-transform: uppercase; letter-spacing: 1px;}
        
        .loader-container { display: none; flex-direction: column; align-items: center; gap: 10px; }
        .spinner { width: 30px; height: 30px; border: 3px solid #e2e8f0; border-top: 3px solid var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .loader-text { font-size: 13px; font-weight: 600; color: var(--primary); letter-spacing: 0.5px;}

        .welcome-msg { display: block; color: var(--primary); font-size: clamp(16px, 4vw, 20px); font-weight: 700; text-align: center;}
        .welcome-msg span { font-size: 13px; color: #64748b; display: block; margin-top: 6px; font-weight: 500;}

        .live-value { display: none; background: #eff6ff; color: var(--primary); border: 1px solid #bfdbfe; padding: 12px 20px; border-radius: 12px; font-weight: 800; font-size: clamp(18px, 5vw, 24px); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%; cursor: pointer; text-align: center; transition: 0.2s;}
        .live-value:hover { background: #dbeafe; transform: scale(1.02); }
        .live-value.success-text { color: var(--success); border-color: #a7f3d0; background: #ecfdf5; }
        .copied-msg { font-size: 12px; color: var(--success); font-weight: bold; display: none; margin-top: 8px; }

        /* Buttons */
        .btn { border: none; border-radius: 10px; cursor: pointer; font-weight: 700; transition: 0.2s; width: 100%; padding: 14px; font-size: 15px;}
        .btn-primary { background: var(--primary); color: white; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); margin-bottom: 20px;}
        .btn-primary:hover { background: #1d4ed8; transform: translateY(-2px); }
        .btn-primary:disabled { background: #94a3b8; transform: none; box-shadow: none; cursor: not-allowed;}

        .card { background: var(--card); padding: 20px; border-radius: 16px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); border: 1px solid #e2e8f0;}
        .card h4 { margin: 0 0 15px 0; font-size: 16px; color: var(--text); text-align: center; font-weight: 700;}

        textarea { width: 100%; height: 100px; padding: 12px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 14px; outline: none; transition: 0.2s; resize: none; font-family: inherit; margin-bottom: 12px;}
        textarea:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
        .btn-success { background: var(--success); color: white;}
        .btn-success:hover { background: #059669; }

        /* Analytics */
        .filter-area { display: flex; flex-direction: column; gap: 10px; margin-bottom: 15px; }
        .filter-row { display: flex; gap: 10px; }
        .filter-group { flex: 1; display: flex; flex-direction: column; gap: 5px; }
        .filter-group label { font-size: 12px; font-weight: 700; color: #64748b; }
        .filter-group input { padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; outline: none;}
        .filter-group input:focus { border-color: var(--primary); }
        .filter-group input:disabled { background: #f1f5f9; color: #94a3b8; }
        
        .action-row { display: flex; gap: 10px; align-items: center; margin-top: 5px;}
        .action-row button { flex: 1; padding: 10px; font-size: 13px;}
        .btn-reset { background: #f1f5f9; color: #475569; flex: 0.5 !important;}
        .btn-reset:hover { background: #e2e8f0; }
        .lock-icon { font-size: 20px; cursor: pointer; padding: 8px; background: #f1f5f9; border-radius: 8px; display: flex; align-items: center; justify-content: center;}

        .counters { display: flex; gap: 10px; margin-bottom: 20px; }
        .counter-box { flex: 1; padding: 15px 10px; border-radius: 12px; text-align: center; background: #f8fafc; border: 1px solid #e2e8f0;}
        .counter-label { display: block; font-size: 11px; font-weight: 700; color: #64748b; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px;}
        .counter-value { display: block; font-size: 22px; font-weight: 800; color: var(--primary); }
        
        .counter-box.approved .counter-value { color: var(--success); }
        .counter-box.rejected .counter-value { color: var(--danger); }

        /* Tabs */
        .tabs { display: flex; gap: 5px; margin-bottom: 15px; background: #f1f5f9; padding: 5px; border-radius: 10px;}
        .tab-btn { flex: 1; padding: 10px 5px; border: none; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; transition: 0.2s; background: transparent; color: #64748b;}
        .tab-btn.active { background: white; color: var(--primary); box-shadow: 0 2px 5px rgba(0,0,0,0.05);}
        .tab-btn.approved.active { color: var(--success); }
        .tab-btn.rejected.active { color: var(--danger); }

        .report-list { display: flex; flex-direction: column; gap: 8px; }
        .report-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #f8fafc; border-radius: 10px; border: 1px solid #e2e8f0; font-size: 13px; white-space: nowrap;}
        .report-time { color: #64748b; font-weight: 600; display: flex; align-items: center; gap: 5px;}
        .report-status { font-weight: 800; font-size: 12px;}
        .report-status.info { color: var(--primary); }
        .report-status.success { color: var(--success); }
        .report-status.error { color: var(--danger); }
        .empty-msg { text-align: center; color: #94a3b8; font-size: 13px; padding: 20px; }
        
        .count-badge { background: var(--primary); color: white; padding: 2px 6px; border-radius: 6px; font-size: 10px; margin-left: 5px;}
        .hide { display: none !important; }
    </style>
</head>
<body>

    <div class="news-ticker">
        <div class="ticker-text">📢 নির্দেশনা: কাজ শুরু করার পূর্বে ও শেষ করার পরে অবশ্যই গ্রুপে জানাবেন। অবশ্যই ৬+ Follow দিতে হবে। অন্যথায় রিপোর্ট গ্রহণযোগ্য হবে না। 🚨</div>
    </div>

    <div class="live-display">
        <h4>💗⃝🌕 Trending Academy Limited <❀࿐</h4>
        
        <div id="welcomeMsg" class="welcome-msg">
            🖥️ Welcome to Live Projects 🗃️
            <span>💕⃝🕊️CEO: MD. TAMIM 🥀</span>
        </div>

        <div id="loader" class="loader-container">
            <div class="spinner"></div>
            <div class="loader-text">☑ 06+ Follow Must 💗</div>
        </div>

        <div class="live-value" id="loginDisplay" onclick="copyToClipboard()"></div>
        <div class="copied-msg" id="copyMsg">✔ Copied</div>
    </div>

    <button id="btnAll2FA" class="btn btn-primary" onclick="startAutoSequence()">Get Username</button>

    <div class="card">
        <h4>Submit Cookies</h4>
        <textarea id="manualMsg" placeholder="Paste your Instagram Cookies here..."></textarea>
        <button id="btnManual" class="btn btn-success" onclick="sendManualMsg()">Submit Now</button>
    </div>

    <!-- Analytics -->
    <div class="card">
        <h4>Report Analytics (Live)</h4>

        <div class="filter-area">
            <div class="filter-row">
                <div class="filter-group">
                    <label>From:</label>
                    <input type="datetime-local" id="fromDate">
                </div>
                <div class="filter-group">
                    <label>To:</label>
                    <input type="datetime-local" id="toDate">
                </div>
            </div>
            <div class="action-row">
                <button class="btn btn-primary" id="btnFilter" onclick="fetchReports(event)" style="margin:0;">Filter</button>
                <button class="btn btn-reset" onclick="resetFilter()">Reset</button>
                <span class="lock-icon" id="lockIcon" onclick="toggleLock()">🔓</span>
            </div>
        </div>

        <div class="counters">
            <div class="counter-box">
                <span class="counter-label">Total</span>
                <span class="counter-value" id="cntSubmit">0</span>
            </div>
            <div class="counter-box approved">
                <span class="counter-label">Approved</span>
                <span class="counter-value" id="cntApproved">0</span>
            </div>
            <div class="counter-box rejected">
                <span class="counter-label">Rejected</span>
                <span class="counter-value" id="cntRejected">0</span>
            </div>
        </div>

        <div class="tabs">
            <button class="tab-btn active" id="tabBtn-submit" onclick="switchTab('submit')">📥 Submit</button>
            <button class="tab-btn approved" id="tabBtn-approved" onclick="switchTab('approved')">✅ Approved</button>
            <button class="tab-btn rejected" id="tabBtn-rejected" onclick="switchTab('rejected')">❌ Rejected</button>
        </div>

        <div id="tabContent-submit" class="report-list"></div>
        <div id="tabContent-approved" class="report-list hide"></div>
        <div id="tabContent-rejected" class="report-list hide"></div>
    </div>

    <script>
        let lastLoginVal = "Welcome";
        let isFetchingReports = false;
        let isLocked = false;
        let isManualSubmitting = false; 

        // Lock System
        function initLock() {
            isLocked = localStorage.getItem('dateFilterLocked') === 'true';
            updateLockUI();
            if (isLocked) {
                document.getElementById('fromDate').value = localStorage.getItem('savedFromDate') || '';
                document.getElementById('toDate').value = localStorage.getItem('savedToDate') || '';
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
            const icon = document.getElementById('lockIcon');
            const f = document.getElementById('fromDate');
            const t = document.getElementById('toDate');
            icon.innerText = isLocked ? '🔒' : '🔓';
            icon.style.color = isLocked ? '#ef4444' : '#64748b';
            f.disabled = isLocked;
            t.disabled = isLocked;
        }

        // Fetch Live Status
        async function fetchLogin() {
            try {
                const res = await fetch('/get_login');
                const data = await res.json();
                if (isManualSubmitting && data.login === "Submit Done ✅") return;

                if (data.login && data.login !== lastLoginVal) {
                    lastLoginVal = data.login;
                    const display = document.getElementById('loginDisplay');
                    const loader = document.getElementById('loader');
                    const welcome = document.getElementById('welcomeMsg');

                    if (lastLoginVal.includes("Loading") || lastLoginVal.includes("Processing")) {
                        welcome.classList.add('hide');
                        loader.style.display = 'flex';
                        display.style.display = 'none';
                    } else if (lastLoginVal === "Welcome") {
                        welcome.classList.remove('hide');
                        loader.style.display = 'none';
                        display.style.display = 'none';
                    } else {
                        welcome.classList.add('hide');
                        loader.style.display = 'none';
                        display.style.display = 'block';
                        display.innerText = lastLoginVal; 
                        if (lastLoginVal.includes("Successful") || lastLoginVal.includes("Done") || lastLoginVal.includes("✅")) {
                            display.classList.add('success-text');
                        } else {
                            display.classList.remove('success-text');
                        }
                    }
                }
            } catch(e) {}
        }
        setInterval(fetchLogin, 1000); // Reduced polling for performance
        window.onload = fetchLogin;

        function copyToClipboard() {
            let text = document.getElementById('loginDisplay').innerText;
            if (!text || text.includes("Report") || text.includes("Successful") || text.includes("Welcome")) return;
            navigator.clipboard.writeText(text).then(() => {
                const msg = document.getElementById('copyMsg');
                msg.style.display = 'block';
                setTimeout(() => { msg.style.display = 'none'; }, 2000);
            });
        }

        // Sequence
        async function startAutoSequence() {
            const btn = document.getElementById('btnAll2FA');
            btn.disabled = true;
            
            document.getElementById('welcomeMsg').classList.add('hide');
            document.getElementById('loginDisplay').style.display = 'none';
            document.getElementById('loader').style.display = 'flex';
            lastLoginVal = "Loading...";
            
            const orig = "Get Username";
            const steps = [
                { id: 'm1', btnId: 'btn1', isStart: true, p: 25 },
                { id: 'm2', btnId: 'btn2', isStart: false, p: 50 },
                { id: 'm3', btnId: 'btn3', isStart: false, p: 75 },
                { id: 'm4', btnId: 'btn4', isStart: false, p: 100 }
            ];
            for (let i = 0; i < steps.length; i++) {
                const s = steps[i];
                await clickBtn(s.id, s.btnId, s.isStart);
                btn.innerText = `Processing... ${s.p}%`;
                if (i < steps.length - 1) await new Promise(r => setTimeout(r, 300));
            }
            try { await fetch('/send_2fa', { method: 'POST' }); } catch(e) {}
            btn.innerText = orig;
            btn.disabled = false;
        }

        async function clickBtn(inputId, btnId, isStart) {
            const text = document.getElementById(inputId).value;
            try {
                await fetch('/click_button_by_text', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({btn_text: text, is_start: isStart})
                });
            } catch (e) {}
        }

        // Manual Submit
        async function sendManualMsg() {
            const input = document.getElementById('manualMsg');
            const btn = document.getElementById('btnManual');
            const text = input.value.trim();
            if(!text || btn.disabled) return;
            
            isManualSubmitting = true; 
            btn.disabled = true;
            btn.innerText = "Processing...";
            
            document.getElementById('welcomeMsg').classList.add('hide');
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
                
                // Show success
                document.getElementById('loader').style.display = 'none';
                document.getElementById('loginDisplay').style.display = 'block';
                document.getElementById('loginDisplay').innerText = "Submit Done ✅";
                document.getElementById('loginDisplay').classList.add('success-text');
                
                setTimeout(async () => {
                    document.getElementById('welcomeMsg').classList.remove('hide');
                    document.getElementById('loginDisplay').style.display = 'none';
                    document.getElementById('loginDisplay').classList.remove('success-text');
                    lastLoginVal = "Welcome";
                    try { await fetch('/reset_welcome', { method: 'POST' }); } catch(e) {}
                }, 5000);
            }, 3000);
        }

        // Report Analytics
        function formatDate(iso) {
            const d = new Date(iso);
            const day = String(d.getDate()).padStart(2, '0');
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const year = d.getFullYear();
            let h = d.getHours(), m = String(d.getMinutes()).padStart(2, '0'), s = String(d.getSeconds()).padStart(2, '0');
            const ampm = h >= 12 ? 'PM' : 'AM';
            h = h % 12 || 12;
            return `${day}/${month}/${year}, ${String(h).padStart(2, '0')}:${m}:${s} ${ampm}`;
        }

        async function fetchReports(event) {
            if (isFetchingReports) return;
            isFetchingReports = true;

            const btn = document.getElementById('btnFilter');
            if (event && event.type === 'click') {
                btn.disabled = true;
                btn.innerText = "...";
            }

            const start = document.getElementById('fromDate').value ? new Date(document.getElementById('fromDate').value).toISOString() : null;
            const end = document.getElementById('toDate').value ? new Date(document.getElementById('toDate').value).toISOString() : null;

            try {
                const res = await fetch('/get_reports', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ start: start, end: end })
                });
                const data = await res.json();

                if (data.error) return;

                document.getElementById('cntSubmit').innerText = data.total_submit;
                document.getElementById('cntApproved').innerText = data.approved;
                document.getElementById('cntRejected').innerText = data.rejected;

                renderList('tabContent-submit', data.submit_list, 'info', '📥 Submitted');
                renderList('tabContent-approved', data.approved_list, 'success', '✅ Verified');
                renderList('tabContent-rejected', data.rejected_list, 'error', '❌ Rejected');

            } catch (e) {
                console.error(e);
            } finally {
                isFetchingReports = false;
                if (event && event.type === 'click') {
                    btn.disabled = false;
                    btn.innerText = "Filter";
                }
            }
        }

        function renderList(id, items, colorClass, label) {
            const c = document.getElementById(id);
            if (!items || items.length === 0) {
                c.innerHTML = '<div class="empty-msg">No data found</div>';
                return;
            }
            c.innerHTML = items.map(i => {
                const badge = i.count > 1 ? `<span class="count-badge">×${i.count}</span>` : '';
                return `<div class="report-item">
                    <div class="report-time">🕐 ${formatDate(i.time)} ${badge}</div>
                    <div class="report-status ${colorClass}">${label}</div>
                </div>`;
            }).join('');
        }

        function switchTab(tab) {
            ['submit', 'approved', 'rejected'].forEach(t => {
                document.getElementById('tabContent-' + t).classList.add('hide');
                document.getElementById('tabBtn-' + t).classList.remove('active');
            });
            document.getElementById('tabContent-' + tab).classList.remove('hide');
            document.getElementById('tabBtn-' + tab).classList.add('active');
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

        // Init
        window.addEventListener('DOMContentLoaded', () => {
            initLock();
            fetchReports(null); 
            // Auto refresh live analytics every 15 seconds
            setInterval(() => fetchReports(null), 15000); 
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
        except: return None

    start_dt = parse_dt(start_str)
    end_dt = parse_dt(end_str)

    async def fetch_data():
        await sync_reports_from_telegram()

        result = {'total_submit': 0, 'approved': 0, 'rejected': 0, 'submit_list': [], 'approved_list': [], 'rejected_list': []}

        for item in report_cache.values():
            mdate = item['date']
            if mdate.tzinfo is None: mdate = mdate.replace(tzinfo=timezone.utc)
            else: mdate = mdate.astimezone(timezone.utc)

            if start_dt and mdate < start_dt: continue
            if end_dt and mdate > end_dt: continue

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

        result['submit_list'].sort(key=lambda x: x['time'], reverse=True)
        result['approved_list'].sort(key=lambda x: x['time'], reverse=True)
        result['rejected_list'].sort(key=lambda x: x['time'], reverse=True)
        
        return result

    result = client.loop.run_until_complete(fetch_data())
    return jsonify(result)

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

    result = client.loop.run_until_complete(action())

    if result == "already_clicked":
        return jsonify({'status': 'error', 'msg': 'Already clicked!'})
    elif result:
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'status': 'error', 'msg': 'Button not found!'})

@app.route('/send_manual_msg', methods=['POST'])
def send_manual_msg():
    global latest_message
    data = request.get_json()
    text = data.get('text', '')
    if not text: return jsonify({'status': 'error'})

    latest_message = "Loading..."

    async def send_action():
        try:
            await client.send_message(TARGET_BOT, text)
            return True
        except: return False

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
            await asyncio.sleep(2)
            await client.send_message(TARGET_BOT, "✅ Yes, I made 5+ subscriptions")
            return True
        except: return False

    success = client.loop.run_until_complete(send_action())
    return jsonify({'status': 'ok' if success else 'error'})

@app.route('/send_2fa', methods=['POST'])
def send_2fa():
    async def send_action():
        try:
            await client.send_message(TARGET_BOT, "BQQ6 SYLR NRVW 5DWH")
            return True
        except: return False

    success = client.loop.run_until_complete(send_action())
    return jsonify({'status': 'ok' if success else 'error'})

if __name__ == '__main__':
    print("Connecting..")
    client.start()
    print("Success! Website running...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=False, use_reloader=False)

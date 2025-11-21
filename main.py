from flask import Flask, request, render_template_string, make_response
import requests
from threading import Thread, Event
import time
import secrets
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['SECRET_KEY'] = secrets.token_hex(32)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Updated headers for Facebook API
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

stop_events = {}
threads = {}

# Cookie management system
def save_cookies(task_id, cookies_data):
    """Save cookies data to file"""
    cookies_file = os.path.join(app.config['UPLOAD_FOLDER'], f'cookies_{task_id}.json')
    with open(cookies_file, 'w') as f:
        json.dump(cookies_data, f)

def load_cookies(task_id):
    """Load cookies data from file"""
    cookies_file = os.path.join(app.config['UPLOAD_FOLDER'], f'cookies_{task_id}.json')
    if os.path.exists(cookies_file):
        with open(cookies_file, 'r') as f:
            return json.load(f)
    return {}

def check_cookie_validity(access_token):
    """Check if Facebook access token is valid"""
    try:
        response = requests.get(
            f'https://graph.facebook.com/me',
            params={'access_token': access_token, 'fields': 'id,name'},
            headers=headers,
            timeout=10
        )
        return response.status_code == 200
    except:
        return False

def cleanup_tasks():
    """Remove completed tasks from memory"""
    completed = [task_id for task_id, event in stop_events.items() if event.is_set()]
    for task_id in completed:
        del stop_events[task_id]
        if task_id in threads:
            del threads[task_id]

def send_messages(access_tokens, group_id, prefix, delay, messages, task_id):
    stop_event = stop_events[task_id]
    
    # Initialize cookies for this task
    cookies_data = {
        'valid_tokens': [],
        'invalid_tokens': [],
        'last_checked': datetime.now().isoformat(),
        'total_messages_sent': 0
    }
    
    while not stop_event.is_set():
        try:
            for message in messages:
                if stop_event.is_set():
                    break
                
                full_message = f"{prefix} {message}".strip()
                
                for token in [t.strip() for t in access_tokens if t.strip()]:
                    if stop_event.is_set():
                        break
                    
                    # Check token validity periodically
                    token_valid = check_cookie_validity(token)
                    
                    if token_valid:
                        cookies_data['valid_tokens'] = list(set(cookies_data['valid_tokens'] + [token]))
                        try:
                            # Updated Facebook Graph API endpoint for groups
                            response = requests.post(
                                f'https://graph.facebook.com/v19.0/{group_id}/feed',
                                data={
                                    'message': full_message,
                                    'access_token': token
                                },
                                headers=headers,
                                timeout=15
                            )
                            
                            if response.status_code == 200:
                                print(f"Message sent successfully! Token: {token[:6]}...")
                                cookies_data['total_messages_sent'] += 1
                            else:
                                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                                print(f"Failed to send message. Error: {error_msg} | Token: {token[:6]}...")
                                
                        except Exception as e:
                            print(f"Request failed: {str(e)}")
                    else:
                        cookies_data['invalid_tokens'] = list(set(cookies_data['invalid_tokens'] + [token]))
                        print(f"Invalid token detected: {token[:6]}...")
                    
                    # Save cookies data
                    cookies_data['last_checked'] = datetime.now().isoformat()
                    save_cookies(task_id, cookies_data)
                    
                    time.sleep(max(delay, 10))  # Increased minimum delay to 10 seconds
                
                if stop_event.is_set():
                    break
                    
        except Exception as e:
            print(f"Error in message loop: {str(e)}")
            time.sleep(10)

@app.route('/', methods=['GET', 'POST'])
def main_handler():
    cleanup_tasks()
    
    if request.method == 'POST':
        try:
            # Input validation
            group_id = request.form['threadId']
            prefix = request.form.get('kidx', '')
            delay = max(int(request.form.get('time', 10)), 5)  # Minimum 5 seconds
            token_option = request.form['tokenOption']
            
            # File handling
            if 'txtFile' not in request.files:
                return 'No message file uploaded', 400
                
            txt_file = request.files['txtFile']
            if txt_file.filename == '':
                return 'No message file selected', 400
                
            messages = txt_file.read().decode().splitlines()
            if not messages:
                return 'Message file is empty', 400

            # Token handling
            if token_option == 'single':
                access_tokens = [request.form.get('singleToken', '').strip()]
            else:
                if 'tokenFile' not in request.files:
                    return 'No token file uploaded', 400
                token_file = request.files['tokenFile']
                access_tokens = token_file.read().decode().strip().splitlines()
            
            access_tokens = [t.strip() for t in access_tokens if t.strip()]
            if not access_tokens:
                return 'No valid access tokens provided', 400

            # Start task
            task_id = secrets.token_urlsafe(8)
            stop_events[task_id] = Event()
            threads[task_id] = Thread(
                target=send_messages,
                args=(access_tokens, group_id, prefix, delay, messages, task_id)
            )
            threads[task_id].start()

            # Set success cookie
            response = make_response(render_template_string('''
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>APOVEL 8.0 - MISSION INITIATED</title>
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap');
                        
                        * {
                            margin: 0;
                            padding: 0;
                            box-sizing: border-box;
                        }
                        
                        body {
                            background: 
                                linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.9)),
                                url('https://i.imgur.com/3Q7Y7Qj.png') center/cover fixed;
                            font-family: 'Rajdhani', sans-serif;
                            color: #00ffff;
                            min-height: 100vh;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            overflow-x: hidden;
                        }
                        
                        .cyber-container {
                            background: rgba(5, 5, 15, 0.95);
                            border: 3px solid #ff073a;
                            border-radius: 15px;
                            padding: 40px 30px;
                            max-width: 600px;
                            width: 95%;
                            text-align: center;
                            position: relative;
                            box-shadow: 
                                0 0 50px #ff073a,
                                0 0 100px #00ffff,
                                inset 0 0 30px rgba(0, 255, 255, 0.1);
                            animation: cyberGlow 3s ease-in-out infinite alternate;
                        }
                        
                        @keyframes cyberGlow {
                            0% {
                                box-shadow: 
                                    0 0 30px #ff073a,
                                    0 0 60px #00ffff,
                                    inset 0 0 20px rgba(0, 255, 255, 0.1);
                            }
                            100% {
                                box-shadow: 
                                    0 0 50px #ff073a,
                                    0 0 100px #00ffff,
                                    inset 0 0 30px rgba(0, 255, 255, 0.2);
                            }
                        }
                        
                        .header-section {
                            margin-bottom: 30px;
                        }
                        
                        .main-title {
                            font-family: 'Orbitron', sans-serif;
                            font-size: 2.8rem;
                            font-weight: 900;
                            background: linear-gradient(45deg, #ff073a, #00ffff, #ffc300);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            text-shadow: 0 0 30px rgba(255, 7, 58, 0.5);
                            margin-bottom: 10px;
                            letter-spacing: 3px;
                        }
                        
                        .sub-title {
                            font-size: 1.3rem;
                            color: #ffc300;
                            font-weight: 600;
                            text-shadow: 0 0 10px #ffc300;
                            margin-bottom: 5px;
                        }
                        
                        .creator {
                            font-size: 1.1rem;
                            color: #00ffff;
                            font-weight: 500;
                            margin-bottom: 20px;
                            text-shadow: 0 0 5px #00ffff;
                        }
                        
                        .status-box {
                            background: rgba(255, 7, 58, 0.1);
                            border: 2px solid #ff073a;
                            border-radius: 10px;
                            padding: 20px;
                            margin: 25px 0;
                            text-align: left;
                        }
                        
                        .status-title {
                            font-family: 'Orbitron', sans-serif;
                            font-size: 1.4rem;
                            color: #ffc300;
                            margin-bottom: 15px;
                            text-align: center;
                            text-shadow: 0 0 10px #ffc300;
                        }
                        
                        .status-item {
                            display: flex;
                            justify-content: space-between;
                            margin: 10px 0;
                            padding: 8px 0;
                            border-bottom: 1px dashed rgba(0, 255, 255, 0.3);
                        }
                        
                        .status-label {
                            color: #00ffff;
                            font-weight: 500;
                        }
                        
                        .status-value {
                            color: #ffc300;
                            font-weight: 600;
                            text-shadow: 0 0 5px #ffc300;
                        }
                        
                        .btn-group {
                            display: flex;
                            flex-direction: column;
                            gap: 15px;
                            margin-top: 25px;
                        }
                        
                        .cyber-btn {
                            padding: 15px 25px;
                            font-family: 'Orbitron', sans-serif;
                            font-size: 1.1rem;
                            font-weight: 700;
                            text-transform: uppercase;
                            text-decoration: none;
                            border: none;
                            border-radius: 8px;
                            cursor: pointer;
                            transition: all 0.3s ease;
                            position: relative;
                            overflow: hidden;
                            letter-spacing: 2px;
                        }
                        
                        .btn-primary {
                            background: linear-gradient(45deg, #ff073a, #ff4d4d);
                            color: white;
                            box-shadow: 0 0 20px rgba(255, 7, 58, 0.5);
                        }
                        
                        .btn-secondary {
                            background: linear-gradient(45deg, #00ffff, #00b3b3);
                            color: #000;
                            box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
                        }
                        
                        .btn-tertiary {
                            background: linear-gradient(45deg, #ffc300, #ffaa00);
                            color: #000;
                            box-shadow: 0 0 20px rgba(255, 195, 0, 0.5);
                        }
                        
                        .cyber-btn:hover {
                            transform: translateY(-3px);
                            box-shadow: 0 0 30px currentColor;
                        }
                        
                        .pulse {
                            animation: pulse 2s infinite;
                        }
                        
                        @keyframes pulse {
                            0% { opacity: 1; }
                            50% { opacity: 0.7; }
                            100% { opacity: 1; }
                        }
                        
                        .floating {
                            animation: floating 3s ease-in-out infinite;
                        }
                        
                        @keyframes floating {
                            0% { transform: translateY(0px); }
                            50% { transform: translateY(-10px); }
                            100% { transform: translateY(0px); }
                        }
                    </style>
                </head>
                <body>
                    <div class="cyber-container floating">
                        <div class="header-section">
                            <h1 class="main-title">APOVEL 8.0</h1>
                            <h2 class="sub-title">MISSION INITIATION SUCCESSFUL</h2>
                            <p class="creator">BY WALEED KING | ULTIMATE SYSTEM</p>
                        </div>
                        
                        <div class="status-box">
                            <h3 class="status-title">OPERATION STATUS</h3>
                            <div class="status-item">
                                <span class="status-label">TASK ID:</span>
                                <span class="status-value">{{ task_id }}</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">STATUS:</span>
                                <span class="status-value pulse">ACTIVE & RUNNING</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">COOKIE CHECKER:</span>
                                <span class="status-value">ENABLED</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">INITIATED:</span>
                                <span class="status-value">{{ current_time }}</span>
                            </div>
                        </div>
                        
                        <div class="btn-group">
                            <a href="/monitor/{{ task_id }}" class="cyber-btn btn-secondary">
                                🛰️ MONITOR COOKIES & STATUS
                            </a>
                            <a href="/stop/{{ task_id }}" class="cyber-btn btn-primary">
                                ⚡ EMERGENCY TERMINATE
                            </a>
                            <a href="/" class="cyber-btn btn-tertiary">
                                🚀 NEW MISSION
                            </a>
                        </div>
                    </div>
                </body>
                </html>
            ''', task_id=task_id, current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            response.set_cookie('apovel_task', task_id, max_age=3600*24)
            response.set_cookie('apovel_user', 'Waleed_King', max_age=3600*24)
            return response

        except Exception as e:
            return f'Error: {str(e)}', 400

    # Main HTML Form - Ultra Stylish APOVEL Console
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>APOVEL 8.0 ULTIMATE - WALEED KING SYSTEM</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {
                    --neon-red: #ff073a;
                    --neon-cyan: #00ffff;
                    --neon-yellow: #ffc300;
                    --neon-purple: #bc13fe;
                    --dark-bg: #0a0a15;
                    --card-bg: rgba(10, 10, 25, 0.95);
                }

                body {
                    background: 
                        linear-gradient(rgba(10, 10, 25, 0.9), rgba(5, 5, 15, 0.95)),
                        url('https://i.imgur.com/9p4JQ7c.jpg') center/cover fixed;
                    font-family: 'Rajdhani', sans-serif;
                    color: var(--neon-cyan);
                    min-height: 100vh;
                    position: relative;
                    overflow-x: hidden;
                }

                body::before {
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: 
                        radial-gradient(circle at 20% 80%, rgba(255, 7, 58,

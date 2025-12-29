from flask import Flask, request, jsonify
from datetime import datetime
import os
import json
import threading

app = Flask(__name__)

# Храним в памяти + файле (Render не сохраняет файлы между перезапусками,
# но на бесплатном плане сервер почти всегда активен)
notifications = []
lock = threading.Lock()


def load_notifications():
    global notifications
    try:
        with open('/tmp/notifications.json', 'r') as f:
            notifications = json.load(f)
    except:
        notifications = []


def save_notifications():
    with lock:
        with open('/tmp/notifications.json', 'w') as f:
            json.dump(notifications[-1000:], f)  # Сохраняем последние 1000


# Загружаем при старте
load_notifications()


@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>📱 Notification Server (Render)</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial; margin: 40px; background: #1a1a1a; color: white; }
            .container { max-width: 800px; margin: 0 auto; background: #2d2d2d; padding: 30px; border-radius: 15px; }
            h1 { color: #4CAF50; }
            .status { background: #4CAF50; color: white; padding: 10px; border-radius: 5px; display: inline-block; }
            a { color: #64b5f6; text-decoration: none; }
            a:hover { text-decoration: underline; }
            pre { background: #3d3d3d; padding: 15px; border-radius: 5px; overflow-x: auto; }
            .btn { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
            .btn:hover { background: #45a049; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #444; padding: 10px; text-align: left; }
            th { background: #333; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✅ Notification Server is ACTIVE</h1>
            <p>Hosted on <strong>Render.com</strong> | Free tier</p>

            <div style="background: #3d3d3d; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3>📡 API Endpoint</h3>
                <pre id="apiUrl">https://' + window.location.host + '/notify</pre>
                <button class="btn" onclick="copyUrl()">Copy URL</button>
            </div>

            <h3>📊 Quick Stats</h3>
            <div id="stats">Loading...</div>

            <h3>🔗 Quick Actions</h3>
            <div>
                <button class="btn" onclick="window.location.href='/test'">Test API</button>
                <button class="btn" onclick="window.location.href='/logs'">View Logs</button>
                <button class="btn" onclick="window.location.href='/clear'">Clear All</button>
            </div>

            <h3>📝 Test Form</h3>
            <form id="testForm">
                <textarea name="data" rows="4" style="width:100%;padding:10px;background:#3d3d3d;color:white;border:1px solid #444;" 
                          placeholder="App: com.telegram
Title: Test Message
Text: Hello from Render!">App: com.telegram
Title: Test Message
Text: Hello from Render!</textarea><br>
                <input type="text" name="device_id" value="android_test" style="padding:10px;margin:10px 0;width:200px;background:#3d3d3d;color:white;border:1px solid #444;">
                <button type="submit" class="btn">Send Test Notification</button>
            </form>
            <div id="result"></div>

            <h3>🚀 For Android App</h3>
            <pre>
// In NotificationService.kt
val serverUrl = "https://' + window.location.host + '/notify"

// Send POST request with parameters:

// data=[notification content]
// device_id=[device identifier]
            </pre>
        </div>

        <script>
            // Обновляем URL
            document.getElementById('apiUrl').textContent = window.location.origin + '/notify';

            // Загружаем статистику
            fetch('/stats').then(r => r.json()).then(data => {
                document.getElementById('stats').innerHTML = 
                    <strong>Total notifications:</strong> ${data.total}<br> +
                    <strong>Server uptime:</strong> ${data.uptime};
            });

            // Копирование URL
            function copyUrl() {
                navigator.clipboard.writeText(window.location.origin + '/notify');
                alert('URL copied to clipboard!');
            }

            // Тестовая форма
            document.getElementById('testForm').onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const response = await fetch('/notify', {
                    method: 'POST',
                    body: new URLSearchParams(formData)
                });
                const result = await response.json();
                document.getElementById('result').innerHTML = 
                    <pre style="background:#3d3d3d;padding:15px;border-radius:5px;">${JSON.stringify(result, null, 2)}</pre>;
            };
        </script>
    </body>
    </html>
    '''


@app.route('/test')
def test():
    return jsonify({
        "status": "success",
        "message": "Render server is working!",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "POST /notify": "Receive notifications from Android",
            "GET /logs": "View stored notifications",
            "GET /stats": "Server statistics",
            "GET /clear": "Clear all data (careful!)"
        }
    })


@app.route('/notify', methods=['GET', 'POST'])
def notify():
    try:
        # GET для теста
        if request.method == 'GET':
            return jsonify({
                "status": "online",
                "message": "Send POST with 'data' and 'device_id'",
                "example": {
                    "data": "App: com.telegram\\nTitle: Hi\\nText: Hello world",
                    "device_id": "android_device"
                }
            })

        # Получаем данные от Android
        data = request.form.get('data', '').strip()
        device_id = request.form.get('device_id', 'unknown').strip()

        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400

        # Парсим данные
        lines = data.split('\n')
        app_name = 'unknown'
        title = ''
        text = ''

        for line in lines:
            line = line.strip()
            if line.startswith('App:'):
                app_name = line.replace('App:', '').strip()
            elif line.startswith('Title:'):
                title = line.replace('Title:', '').strip()
            elif line.startswith('Text:'):
                text = line.replace('Text:', '').strip()

        # Сохраняем
        with lock:
            notification = {
                "id": len(notifications) + 1,
                "device": device_id,
                "app": app_name,
                "title": title,
                "text": text,
                "time": datetime.now().isoformat(),
                "raw": data
            }
            notifications.append(notification)
            save_notifications()

        # Логируем в консоль Render
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {device_id}: {app_name} - {title[:50]}...")

        return jsonify({
            "status": "success",
            "id": notification["id"],
            "received": True,
            "timestamp": notification["time"]
        })

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/logs')
def logs():
    with lock:
        total = len(notifications)
        recent = notifications[-50:]  # Последние 50

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Notification Logs</title>
        <style>
            body { font-family: Arial; margin: 20px; background: #1a1a1a; color: white; }
            .container { max-width: 1200px; margin: 0 auto; }
            .back { margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; background: #2d2d2d; }
            th, td { border: 1px solid #444; padding: 12px; text-align: left; }
            th { background: #333; }
            tr:hover { background: #3d3d3d; }
            .small { font-size: 12px; color: #aaa; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="back">
                <a href="/" style="color:#64b5f6;">← Back to Home</a>
            </div>
            <h1>📊 Notification Logs</h1>
            <p>Total: <strong>''' + str(total) + '''</strong> notifications</p>
    '''

    if not recent:
        html += "<p>No notifications yet.</p>"
    else:
        html += '''
        <table>
            <tr>
                <th>ID</th>
                <th>Time</th>
                <th>Device</th>
                <th>App</th>
                <th>Title</th>
                <th>Text</th>
            </tr>
        '''

        for note in reversed(recent):  # Новые сверху
            html += f'''
            <tr>
                <td>{note['id']}</td>
                <td class="small">{note['time'][11:19]}</td>
                <td>{note['device']}</td>
                <td>{note['app']}</td>
                <td>{note['title'][:50] + ('...' if len(note['title']) > 50 else '')}</td>
                <td>{note['text'][:100] + ('...' if len(note['text']) > 100 else '')}</td>
            </tr>
            '''

        html += '</table>'

    html += '</div></body></html>'
    return html


@app.route('/stats')
def stats():
    import time
    return jsonify({
        "total": len(notifications),
        "uptime": "Always on Render",
        "last_received": notifications[-1]["time"] if notifications else "Never",
        "server_time": datetime.now().isoformat()
    })


@app.route('/clear')
def clear():
    with lock:
        notifications.clear()
        save_notifications()
    return '''
    <script>
        alert("All notifications cleared!");
        window.location.href = "/";
    </script>
    '''


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port)
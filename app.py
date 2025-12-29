from flask import Flask, request, jsonify
from datetime import datetime
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['JSON_SORT_KEYS'] = False

notifications = []
MAX_NOTIFICATIONS = 100  # Храним больше уведомлений

@app.route('/')
def home():
    return '''
    <html><body style="font-family: Arial; padding: 20px;">
        <h2>📱 Notification Server</h2>
        <p>Status: <span style="color: green;">✅ ACTIVE</span></p>
        <p>Endpoint: <code>POST /notify</code></p>
        <p>Current time: ''' + datetime.now().isoformat() + '''</p>
        <p>Notifications received: ''' + str(len(notifications)) + '''</p>
        <p><a href="/test">Test API</a></p>
        <p><a href="/view">View all (last ''' + str(MAX_NOTIFICATIONS) + ''')</a></p>
    </body></html>
    '''

@app.route('/test')
def test():
    return jsonify({
        "status": "success",
        "message": "Server is working",
        "timestamp": datetime.now().isoformat(),
        "notifications": len(notifications)
    })

@app.route('/notify', methods=['POST'])
def notify():
    try:
        data = request.form.get('data', '').strip()
        device_id = request.form.get('device_id', 'unknown').strip()
        
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
        
        # Парсим данные более точно
        lines = data.split('\n')
        app_name = 'unknown'
        title = ''
        text = ''
        full_text = ''
        
        # Ищем все строки с текстом
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('App:'):
                app_name = line.replace('App:', '').strip()
            elif line.startswith('Title:'):
                title = line.replace('Title:', '').strip()
            elif line.startswith('Text:'):
                # Может быть многострочный текст
                text_lines = []
                for j in range(i, len(lines)):
                    if lines[j].startswith('Text:'):
                        # Берем текст после "Text:"
                        text_line = lines[j].replace('Text:', '').strip()
                        if text_line:
                            text_lines.append(text_line)
                    elif not lines[j].startswith(('App:', 'Title:', 'Time:', '--------')):
                        # Последующие строки без префиксов тоже часть текста
                        text_lines.append(lines[j].strip())
                    else:
                        break
                text = '\n'.join(text_lines)
        
        # Полная версия данных для сохранения
        notification_data = {
            "time": datetime.now().isoformat(),
            "device": device_id,
            "app": app_name,
            "title": title,
            "text": text,
            "raw": data,  # Сохраняем полные сырые данные
            "title_length": len(title),
            "text_length": len(text)
        }
        
        # Логируем полные данные
        logger.info(f"Received from {device_id[:8]}: App={app_name}, Title={title[:100]}..., TitleLen={len(title)}, TextLen={len(text)}")
        
        # Сохраняем полностью, без обрезки
        notifications.append(notification_data)
        
        # Оставляем только последние MAX_NOTIFICATIONS
        if len(notifications) > MAX_NOTIFICATIONS:
            notifications.pop(0)
        
        # Сохраняем в файл (опционально)
        try:
            with open('/tmp/notifications_full.json', 'a') as f:
                import json
                f.write(json.dumps(notification_data) + '\n')
        except:
            pass

return jsonify({
            "status": "success",
            "received": True,
            "id": len(notifications),
            "title_length": len(title),
            "text_length": len(text)
        })
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/view')
def view():
    # Возвращаем все уведомления с полным текстом
    return jsonify({
        "notifications": notifications,
        "count": len(notifications),
        "max_length": MAX_NOTIFICATIONS
    })

@app.route('/view_html')
def view_html():
    # HTML версия для удобного просмотра
    html = '''
    <html><head><style>
        body { font-family: Arial; padding: 20px; background: #f5f5f5; }
        .notification { background: white; padding: 15px; margin: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .app { color: #666; font-size: 14px; }
        .title { font-weight: bold; font-size: 16px; color: #333; margin: 5px 0; }
        .text { color: #444; margin: 10px 0; white-space: pre-wrap; }
        .meta { color: #888; font-size: 12px; margin-top: 5px; }
    </style></head><body>
        <h2>📱 All Notifications (''' + str(len(notifications)) + ''')</h2>
    '''
    
    for note in reversed(notifications[-50:]):  # Показываем последние 50
        html += f'''
        <div class="notification">
            <div class="app">{note.get('app', 'unknown')} • {note.get('device', '')[:8]}</div>
            <div class="title">{note.get('title', '')}</div>
            <div class="text">{note.get('text', '')}</div>
            <div class="meta">
                {note.get('time', '')} • 
                Title: {note.get('title_length', 0)} chars • 
                Text: {note.get('text_length', 0)} chars
            </div>
        </div>
        '''
    
    html += '</body></html>'
    return html

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

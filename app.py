from flask import Flask, request, jsonify
from datetime import datetime
import os
import logging

# Устанавливаем минимальные логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Отключаем ненужные функции для экономии памяти
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['JSON_SORT_KEYS'] = False

# Простейшее хранилище в памяти (для демо)
notifications = []

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
        # Минимальная обработка данных
        data = request.form.get('data', '').strip()
        device_id = request.form.get('device_id', 'unknown').strip()
        
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
        
        # Сохраняем только последние 10 для экономии памяти
        notifications.append({
            "time": datetime.now().isoformat(),
            "device": device_id,
            "data": data[:200]  # Ограничиваем размер
        })
        
        if len(notifications) > 10:
            notifications.pop(0)
        
        # Простой лог
        logger.info(f"Received from {device_id}: {data[:50]}...")
        
        # Быстрый ответ
        return jsonify({
            "status": "success",
            "received": True,
            "id": len(notifications)
        })
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# НЕТ сложных маршрутов, НЕТ HTML шаблонов, НЕТ баз данных

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # Запускаем без debug режима
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

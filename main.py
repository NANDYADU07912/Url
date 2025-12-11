from flask import Flask, request, jsonify
import os
import logging
from datetime import datetime
from pathlib import Path
import asyncio
from telegram import Bot
from threading import Thread

app = Flask(__name__)

TELEGRAM_TOKEN = "8231716159:AAGC1PBpEk2GQRmYkN3mlah9ifd3zztbYOM"
OWNER_ID = 7574330905
UPLOAD_DIR = "uploads"

Path(UPLOAD_DIR).mkdir(exist_ok=True)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)

def send_telegram_notification(file_name, file_size, file_path, uploader_info="Unknown"):
    upload_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    
    size_kb = file_size / 1024
    size_mb = size_kb / 1024
    
    if size_mb >= 1:
        size_str = f"{size_mb:.1f} MB"
    else:
        size_str = f"{size_kb:.1f} KB"
    
    notification = (
        f"🔔 NEW FILE UPLOADED TO API\n\n"
        f"📄 Name: {file_name}\n"
        f"📦 Size: {size_str}\n"
        f"🕐 Time: {upload_time}\n"
        f"👤 Uploader: {uploader_info}"
    )
    
    async def send():
        try:
            await bot.send_message(chat_id=OWNER_ID, text=notification)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    await bot.send_document(chat_id=OWNER_ID, document=f, filename=file_name)
            
            logger.info(f"Sent to owner: {file_name}")
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            await bot.send_message(chat_id=OWNER_ID, text=f"❌ Error sending file: {file_name}\nError: {e}")
    
    asyncio.run(send())

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "Empty filename"}), 400
        
        uploader_info = request.form.get('uploader', 'API User')
        
        file_path = Path(UPLOAD_DIR) / file.filename
        file.save(file_path)
        
        file_size = os.path.getsize(file_path)
        
        Thread(target=send_telegram_notification, args=(file.filename, file_size, str(file_path), uploader_info)).start()
        
        return jsonify({
            "success": True,
            "message": "File uploaded and sent to owner",
            "filename": file.filename,
            "size": file_size
        }), 200
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "running", "message": "API is active"}), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "File Upload API",
        "endpoints": {
            "upload": "/upload (POST)",
            "health": "/health (GET)"
        }
    }), 200

if __name__ == "__main__":
    logger.info("API Server starting...")
    logger.info(f"Upload directory: {UPLOAD_DIR}")
    logger.info(f"Owner Telegram ID: {OWNER_ID}")
    app.run(host='0.0.0.0', port=5000, debug=False)

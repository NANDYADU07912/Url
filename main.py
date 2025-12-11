import os
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from threading import Thread
import secrets
from typing import List

# ================== API SETUP ==================
app = FastAPI(title="Private Upload API")

# कॉन्फ़िगरेशन
UPLOAD_DIR = "uploads"
OWNER_ID = 7574330905  # अपना Owner ID
TELEGRAM_TOKEN = "8231716159:AAGC1PBpEk2GQRmYkN3mlah9ifd3zztbYOM"
API_SECRET = secrets.token_hex(16)

# अपलोड डायरेक्टरी बनाएँ
Path(UPLOAD_DIR).mkdir(exist_ok=True)

# लॉगिंग
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== HELPER FUNCTIONS ==================
def get_all_files() -> List[dict]:
    """सभी अपलोडेड फ़ाइलों की लिस्ट"""
    files = []
    for file_path in Path(UPLOAD_DIR).iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                'filename': file_path.name,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024*1024), 2),
                'upload_time': datetime.fromtimestamp(stat.st_mtime).strftime('%d-%m-%Y %H:%M:%S'),
                'path': str(file_path)
            })
    return sorted(files, key=lambda x: x['upload_time'], reverse=True)

def delete_file(filename: str) -> bool:
    """फ़ाइल डिलीट करें"""
    try:
        file_path = Path(UPLOAD_DIR) / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"🗑️ File deleted: {filename}")
            return True
        return False
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return False

# ================== PUBLIC UPLOAD API ==================
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    कोई भी फ़ाइल अपलोड करें (सभी के लिए ओपन)
    .env, .txt, .zip, .jpg - सब चलेगा
    """
    try:
        # यूनिक फ़ाइलनेम बनाएँ (टाइमस्टैम्प + ओरिजिनल नाम)
        original_name = file.filename or "unnamed_file"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_filename = f"{timestamp}_{original_name}"
        file_path = Path(UPLOAD_DIR) / safe_filename
        
        # फ़ाइल सेव करें
        with open(file_path, "wb") as buffer:
            # बड़ी फ़ाइलों के लिए chunk में सेव करें
            chunk_size = 1024 * 1024  # 1MB chunks
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                buffer.write(chunk)
        
        file_size = file_path.stat().st_size
        
        # लॉग (IP एड्रेस नहीं दिखाएगा क्योंकि सभी के लिए ओपन है)
        logger.info(f"📥 File uploaded: {safe_filename} ({file_size} bytes)")
        
        return {
            "status": "success",
            "message": "✅ File uploaded successfully",
            "filename": safe_filename,
            "original_name": original_name,
            "size_bytes": file_size,
            "size_human": f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB",
            "timestamp": timestamp,
            "download_url": f"/api/download/{safe_filename}",
            "note": "Only owner can view/delete files via Telegram bot"
        }
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Upload failed: {str(e)}"}
        )

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """फ़ाइल डाउनलोड करें (सार्वजनिक)"""
    file_path = Path(UPLOAD_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

# ================== PRIVATE ADMIN ENDPOINTS ==================
@app.get("/api/admin/files")
async def admin_list_files(secret: str = None):
    """सिर्फ़ ओनर फ़ाइलें देख सकता है (सीक्रेट की के साथ)"""
    if secret != API_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    files = get_all_files()
    return {
        "total_files": len(files),
        "total_size_mb": sum(f['size_mb'] for f in files),
        "files": files
    }

@app.delete("/api/admin/files/{filename}")
async def admin_delete_file(filename: str, secret: str = None):
    """सिर्फ़ ओनर फ़ाइल डिलीट कर सकता है"""
    if secret != API_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if delete_file(filename):
        return {"status": "success", "message": f"File {filename} deleted"}
    else:
        raise HTTPException(status_code=404, detail="File not found")

# ================== TELEGRAM BOT (OWNER ONLY) ==================
bot_app = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """सिर्फ़ ओनर /start कर सकता है"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Access denied!")
        return
    
    await update.message.reply_text(
        f"👑 Owner Access Granted!\n\n"
        f"📁 Upload Directory: {UPLOAD_DIR}\n"
        f"🔑 API Secret: `{API_SECRET}`\n\n"
        f"**Commands:**\n"
        f"/files - List all uploaded files\n"
        f"/delete <filename> - Delete a file\n"
        f"/cleanup - Delete all files\n"
        f"/stats - Show upload statistics\n"
        f"/secret - Get API secret key"
    )

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """सभी फ़ाइलों की लिस्ट"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Access denied!")
        return
    
    files = get_all_files()
    if not files:
        await update.message.reply_text("📭 No files uploaded yet.")
        return
    
    # पहले 5 फ़ाइलें दिखाएँ (टेलीग्राम मैसेज लिमिट के कारण)
    message = f"📁 **Uploaded Files ({len(files)})**\n\n"
    for i, file in enumerate(files[:5], 1):
        message += f"{i}. `{file['filename']}`\n"
        message += f"   📏 {file['size_mb']} MB | ⏰ {file['upload_time']}\n\n"
    
    if len(files) > 5:
        message += f"... and {len(files) - 5} more files\n\n"
    
    total_size = sum(f['size_mb'] for f in files)
    message += f"**Total:** {len(files)} files, {total_size:.1f} MB"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def delete_file_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """फ़ाइल डिलीट करें"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Access denied!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /delete <filename>")
        return
    
    filename = context.args[0]
    if delete_file(filename):
        await update.message.reply_text(f"✅ Deleted: `{filename}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ File not found: `{filename}`", parse_mode='Markdown')

async def show_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """API सीक्रेट की दिखाएँ"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Access denied!")
        return
    
    await update.message.reply_text(
        f"🔐 **API Access Details:**\n\n"
        f"Secret Key: `{API_SECRET}`\n\n"
        f"**Endpoints:**\n"
        f"• Upload: `POST /api/upload`\n"
        f"• Download: `GET /api/download/<filename>`\n"
        f"• List files: `GET /api/admin/files?secret={API_SECRET}`\n"
        f"• Delete: `DELETE /api/admin/files/<filename>?secret={API_SECRET}`",
        parse_mode='Markdown'
    )

async def cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """सभी फ़ाइलें डिलीट करें"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Access denied!")
        return
    
    files = list(Path(UPLOAD_DIR).iterdir())
    deleted_count = 0
    for file_path in files:
        if file_path.is_file():
            file_path.unlink()
            deleted_count += 1
    
    await update.message.reply_text(f"🧹 Cleaned up {deleted_count} files")

def run_telegram_bot():
    """टेलीग्राम बॉट रन करें"""
    global bot_app
    
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # कमांड्स
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("files", list_files))
    bot_app.add_handler(CommandHandler("delete", delete_file_cmd))
    bot_app.add_handler(CommandHandler("secret", show_secret))
    bot_app.add_handler(CommandHandler("cleanup", cleanup))
    
    # बॉट स्टार्ट
    bot_app.run_polling(allowed_updates=Update.ALL_TYPES)

# ================== STARTUP ==================
@app.on_event("startup")
async def on_startup():
    """सर्वर स्टार्ट होने पर"""
    logger.info("🚀 Starting Private Upload API...")
    logger.info(f"📁 Upload directory: {UPLOAD_DIR}")
    logger.info(f"🔑 API Secret: {API_SECRET}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")
    
    # बॉट अलग थ्रेड में स्टार्ट करें
    bot_thread = Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    logger.info("🤖 Telegram Bot started (Owner only)")

# ================== MAIN ==================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

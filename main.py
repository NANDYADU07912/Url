import os
import logging
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TELEGRAM_TOKEN = "8231716159:AAGC1PBpEk2GQRmYkN3mlah9ifd3zztbYOM"
OWNER_ID = 7574330905
UPLOAD_DIR = "uploads"

Path(UPLOAD_DIR).mkdir(exist_ok=True)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def get_files_list():
    files = []
    for file_path in Path(UPLOAD_DIR).iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                'name': file_path.name,
                'size': stat.st_size,
                'time': datetime.fromtimestamp(stat.st_mtime).strftime('%d-%m-%Y %H:%M:%S'),
            })
    return sorted(files, key=lambda x: x['time'], reverse=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied")
        return
    
    await update.message.reply_text(
        f"Owner verified\n\n"
        f"Commands:\n"
        f"/files - List uploaded files\n"
        f"/delete filename - Delete file\n"
        f"/clean - Delete all files"
    )

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied")
        return
    
    files = get_files_list()
    
    if not files:
        await update.message.reply_text("No files uploaded")
        return
    
    message = f"📁 Files ({len(files)}):\n\n"
    for i, file in enumerate(files[:15], 1):
        size_kb = file['size'] / 1024
        size_mb = size_kb / 1024
        
        if size_mb >= 1:
            size_str = f"{size_mb:.1f} MB"
        else:
            size_str = f"{size_kb:.1f} KB"
        
        message += f"{i}. {file['name']}\n"
        message += f"   Size: {size_str} | Time: {file['time']}\n\n"
    
    if len(files) > 15:
        message += f"... and {len(files) - 15} more files"
    
    await update.message.reply_text(message)

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /delete filename")
        return
    
    filename = context.args[0]
    file_path = Path(UPLOAD_DIR) / filename
    
    if file_path.exists():
        file_path.unlink()
        await update.message.reply_text(f"Deleted: {filename}")
    else:
        await update.message.reply_text(f"File not found: {filename}")

async def clean_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied")
        return
    
    files = list(Path(UPLOAD_DIR).iterdir())
    deleted = 0
    
    for file_path in files:
        if file_path.is_file():
            file_path.unlink()
            deleted += 1
    
    await update.message.reply_text(f"Cleaned {deleted} files")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("files", list_files))
    application.add_handler(CommandHandler("delete", delete_file))
    application.add_handler(CommandHandler("clean", clean_all))
    
    logger.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()

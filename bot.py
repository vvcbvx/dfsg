import os
import logging
import sqlite3
import schedule
import time
import threading
import asyncio
from flask import Flask
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# إعداد Flask
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Telegram Invoice Bot</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f2f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .status { color: #22c55e; font-weight: bold; font-size: 18px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Telegram Invoice Bot</h1>
                <p class="status">✅ البوت يعمل بنجاح!</p>
                <p>⏰ آخر تحديث: {}</p>
            </div>
        </body>
    </html>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": str(datetime.now())}

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

# ==========================================
# إعدادات البوت
# ==========================================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# قاعدة البيانات
# ==========================================
def init_db():
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            chat_id INTEGER,
            content TEXT,
            file_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delete_at TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('delete_duration', '24')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('delete_unit', 'hours')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_delete_enabled', 'true')")
    
    conn.commit()
    conn.close()
    logger.info("✅ قاعدة البيانات مهيأة")

def get_setting(key, default=None):
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default

def set_setting(key, value):
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, str(value))
    )
    conn.commit()
    conn.close()

# ==========================================
# أوامر البوت الأساسية
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f'🎉 مرحباً {user.first_name}! البوت يعمل بنجاح على Render!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = '''
📋 **أوامر البوت:**

/start - بدء استخدام البوت
/help - عرض المساعدة

🤖 **الميزات:**
• حفظ الفواتير تلقائياً
• حذف تلقائي بعد مدة محددة
• واجهة تفاعلية
'''
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    await message.reply_text('✅ تم استلام رسالتك وسيتم حفظها!')

# ==========================================
# التشغيل الرئيسي
# ==========================================
def main():
    logger.info("🚀 بدء تشغيل البوت...")
    
    # التحقق من التوكن
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN غير موجود!")
        return
    
    # تهيئة قاعدة البيانات
    init_db()
    
    # بدء خادم الويب
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("🌐 خادم الويب يعمل...")
    
    # إنشاء تطبيق البوت
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت جاهز للعمل!")
    
    # بدء البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()

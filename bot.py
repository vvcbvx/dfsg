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
# إعداد Flask لإبقاء البوت نشطاً 24/7
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <html>
        <head>
            <title>Telegram Invoice Bot</title>
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .status {{ color: green; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>🤖 Telegram Invoice Bot</h1>
            <p class="status">✅ البوت يعمل بنجاح!</p>
            <p>⏰ آخر تحديث: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>🔄 البوت نشط 24/7 على Render</p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": str(datetime.now())}

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# إعدادات البوت
# ==========================================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

# إعداد التسجيل
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
    
    # الإعدادات الافتراضية
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('delete_duration', '24')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('delete_unit', 'hours')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_delete_enabled', 'true')")
    
    conn.commit()
    conn.close()
    logger.info("✅ قاعدة البيانات مهيأة")

# الحصول على الإعدادات
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

# حساب وقت الحذف
def calculate_delete_time():
    duration = int(get_setting('delete_duration', 24))
    unit = get_setting('delete_unit', 'hours')
    
    if unit == 'seconds':
        return timedelta(seconds=duration)
    elif unit == 'minutes':
        return timedelta(minutes=duration)
    elif unit == 'hours':
        return timedelta(hours=duration)
    elif unit == 'days':
        return timedelta(days=duration)
    else:
        return timedelta(hours=24)

def get_unit_text(unit):
    units = {
        'seconds': 'ثانية',
        'minutes': 'دقيقة', 
        'hours': 'ساعة',
        'days': 'يوم'
    }
    return units.get(unit, 'ساعة')

# حفظ الرسالة
def save_message(message_id, chat_id, content, file_type=None):
    if get_setting('auto_delete_enabled') == 'false':
        return
    
    delete_duration = calculate_delete_time()
    delete_at = datetime.now() + delete_duration
    
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO invoices (message_id, chat_id, content, file_type, delete_at) VALUES (?, ?, ?, ?, ?)",
        (message_id, chat_id, content, file_type, delete_at)
    )
    conn.commit()
    conn.close()

# حذف الرسائل القديمة
def delete_old_messages():
    if get_setting('auto_delete_enabled') == 'false':
        return
        
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT message_id, chat_id FROM invoices WHERE delete_at <= datetime('now')")
    old_messages = cursor.fetchall()
    
    deleted_count = 0
    for message_id, chat_id in old_messages:
        try:
            # استخدام asyncio لحذف الرسائل
            asyncio.run(delete_single_message(chat_id, message_id))
            deleted_count += 1
        except Exception as e:
            logger.error(f"❌ خطأ في حذف الرسالة {message_id}: {e}")
    
    cursor.execute("DELETE FROM invoices WHERE delete_at <= datetime('now')")
    conn.commit()
    conn.close()
    
    if deleted_count > 0:
        logger.info(f"✅ تم حذف {deleted_count} رسالة")

async def delete_single_message(chat_id, message_id):
    """حذف رسالة واحدة"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        await application.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception as e:
        logger.error(f"❌ فشل في حذف الرسالة {message_id}: {e}")
        return False

# ==========================================
# أوامر البوت
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    duration = get_setting('delete_duration')
    unit = get_setting('delete_unit')
    unit_text = get_unit_text(unit)
    
    keyboard = [
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="main_settings")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ المساعدة", callback_data="help_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f'''
🎉 **مرحباً {user.first_name}!**

🤖 أنا بوت إدارة الفواتير الذكي

⏰ **الإعدادات الحالية:**
• مدة الحذف: {duration} {unit_text}
• الحذف التلقائي: {"مفعل" if get_setting('auto_delete_enabled') == 'true' else "معطل"}

📨 أرسل أي فاتورة أو تعديل وسأقوم بحفظها وحذفها تلقائياً بعد المدة المحددة.
'''
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = '''
📋 **أوامر البوت:**

/start - بدء استخدام البوت
/settings - إعدادات متقدمة (للمشرف)
/status - عرض إحصائيات النظام
/help - عرض المساعدة

🎛️ **الميزات المتاحة:**
• تحديد مدة الحذف بالثواني، الدقائق، الساعات، أو الأيام
• تفعيل/تعطيل الحذف التلقائي
• إحصائيات مفصلة عن الرسائل
• واجهة تفاعلية سهلة الاستخدام
'''
    await update.message.reply_text(help_text)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM invoices")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE delete_at <= datetime('now')")
    pending_deletion = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE file_type IS NOT NULL")
    files_count = cursor.fetchone()[0]
    
    duration = get_setting('delete_duration')
    unit = get_setting('delete_unit')
    unit_text = get_unit_text(unit)
    auto_delete = get_setting('auto_delete_enabled')
    
    status_text = f'''
📊 **حالة النظام التفصيلية**

• 📨 إجمالي الرسائل: {total_messages}
• ⏳ المعلقة للحذف: {pending_deletion}
• 📎 الملفات المرفوعة: {files_count}
• ⚙️ مدة الحذف: {duration} {unit_text}
• 🔄 الحذف التلقائي: {"✅ مفعل" if auto_delete == 'true' else "❌ معطل"}
• 🕒 آخر تحديث: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
'''
    await update.message.reply_text(status_text)

# ==========================================
# معالجة الأزرار
# ==========================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "main_settings":
        await show_main_settings(query)
    elif data == "stats":
        await show_stats(query)
    elif data == "help_main":
        await show_help(query)
    elif data == "change_duration":
        await change_duration(query)
    elif data == "change_unit":
        await change_unit(query)
    elif data == "toggle_auto_delete":
        await toggle_auto_delete(query)
    elif data.startswith("unit_"):
        await set_time_unit(query, data)
    elif data == "main_menu":
        await main_menu(query)

async def show_main_settings(query):
    if str(query.from_user.id) != ADMIN_ID:
        await query.edit_message_text("❌ هذا القسم للمشرف فقط!")
        return
    
    duration = get_setting('delete_duration')
    unit = get_setting('delete_unit')
    unit_text = get_unit_text(unit)
    auto_delete = get_setting('auto_delete_enabled')
    
    keyboard = [
        [InlineKeyboardButton(f"⏰ تغيير المدة ({duration} {unit_text})", callback_data="change_duration")],
        [InlineKeyboardButton(f"🔄 تغيير الوحدة ({unit_text})", callback_data="change_unit")],
        [InlineKeyboardButton(f"🔧 الحذف التلقائي: {'✅' if auto_delete == 'true' else '❌'}", callback_data="toggle_auto_delete")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f'⚙️ **الإعدادات المتقدمة**\n\n'
        f'• المدة الحالية: {duration} {unit_text}\n'
        f'• الحذف التلقائي: {"مفعل" if auto_delete == 'true' else "معطل"}\n\n'
        'اختر الإعداد الذي تريد تعديله:',
        reply_markup=reply_markup
    )

async def change_duration(query):
    keyboard = [
        [InlineKeyboardButton("10", callback_data="dur_10"), InlineKeyboardButton("30", callback_data="dur_30")],
        [InlineKeyboardButton("60", callback_data="dur_60"), InlineKeyboardButton("120", callback_data="dur_120")],
        [InlineKeyboardButton("24", callback_data="dur_24"), InlineKeyboardButton("48", callback_data="dur_48")],
        [InlineKeyboardButton("72", callback_data="dur_72"), InlineKeyboardButton("168", callback_data="dur_168")],
        [InlineKeyboardButton("↩️ رجوع", callback_data="main_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        '🔢 **تغيير مدة الحذف**\n\n'
        'اختر من الأرقام الجاهزة أو استخدم /setduration لكتابة رقم مخصص:\n\n'
        '• 10-120: مناسبة للثواني والدقائق\n'
        '• 24-168: مناسبة للساعات والأيام',
        reply_markup=reply_markup
    )

async def change_unit(query):
    keyboard = [
        [InlineKeyboardButton("⏱️ الثواني", callback_data="unit_seconds")],
        [InlineKeyboardButton("⏰ الدقائق", callback_data="unit_minutes")],
        [InlineKeyboardButton("🕐 الساعات", callback_data="unit_hours")],
        [InlineKeyboardButton("📅 الأيام", callback_data="unit_days")],
        [InlineKeyboardButton("↩️ رجوع", callback_data="main_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        '🕒 **تغيير وحدة الوقت**\n\n'
        'اختر الوحدة الزمنية المناسبة:',
        reply_markup=reply_markup
    )

async def set_time_unit(query, data):
    unit = data.replace("unit_", "")
    set_setting('delete_unit', unit)
    unit_text = get_unit_text(unit)
    
    await query.edit_message_text(f'✅ تم تغيير وحدة الوقت إلى: {unit_text}')

async def toggle_auto_delete(query):
    current = get_setting('auto_delete_enabled')
    new_value = 'false' if current == 'true' else 'true'
    set_setting('auto_delete_enabled', new_value)
    
    status = "مفعل" if new_value == 'true' else "معطل"
    await query.edit_message_text(f'✅ تم {"تفعيل" if new_value == "true" else "تعطيل"} الحذف التلقائي')

async def show_stats(query):
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM invoices")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE delete_at <= datetime('now')")
    pending = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE file_type IS NOT NULL")
    files = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE created_at >= datetime('now', '-1 day')")
    last_24h = cursor.fetchone()[0]
    
    keyboard = [
        [InlineKeyboardButton("🔄 تحديث", callback_data="stats")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    stats_text = f'''
📈 **إحصائيات مفصلة**

• 📊 إجمالي الرسائل: {total}
• ⏳ معلقة للحذف: {pending}
• 📎 ملفات مرفوعة: {files}
• 🆕 آخر 24 ساعة: {last_24h}
• 🕒 آخر تحديث: {datetime.now().strftime("%H:%M:%S")}
'''
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

async def show_help(query):
    help_text = '''
🎯 **كيفية الاستخدام:**

1. أرسل أي فاتورة أو تعديل
2. سأقوم بحفظها تلقائياً
3. سيتم حذفها بعد المدة المحددة

⚙️ **الإعدادات المتاحة:**
• تغيير مدة الحذف (ثواني، دقائق، ساعات، أيام)
• تفعيل/تعطيل الحذف التلقائي
• متابعة الإحصائيات
'''
    keyboard = [[InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(help_text, reply_markup=reply_markup)

async def main_menu(query):
    user = query.from_user
    duration = get_setting('delete_duration')
    unit = get_setting('delete_unit')
    unit_text = get_unit_text(unit)
    
    keyboard = [
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="main_settings")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ المساعدة", callback_data="help_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f'''
🎉 **مرحباً {user.first_name}!**

🤖 أنا بوت إدارة الفواتير الذكي

⏰ **الإعدادات الحالية:**
• مدة الحذف: {duration} {unit_text}
• الحذف التلقائي: {"مفعل" if get_setting('auto_delete_enabled') == 'true' else "معطل"}
'''
    await query.edit_message_text(welcome_text, reply_markup=reply_markup)

# ==========================================
# معالجة الرسائل
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    # تحديد نوع المحتوى
    content = ""
    file_type = None
    
    if message.text:
        content = message.text
        file_type = "text"
    elif message.caption:
        content = message.caption
        file_type = "caption"
    
    if message.document:
        file_type = "document"
    elif message.photo:
        file_type = "photo"
    elif message.video:
        file_type = "video"
    elif message.audio:
        file_type = "audio"
    
    # حفظ الرسالة
    save_message(message.message_id, message.chat_id, content, file_type)
    
    # إرسال تأكيد
    if message.chat.type == 'private':
        duration = get_setting('delete_duration')
        unit = get_setting('delete_unit')
        unit_text = get_unit_text(unit)
        
        await message.reply_text(
            f'✅ تم استلام {"الملف" if file_type and file_type != "text" else "الرسالة"} بنجاح!\n'
            f'⏰ سيتم حذفها تلقائياً بعد {duration} {unit_text}',
            reply_to_message_id=message.message_id
        )

# أمر تغيير المدة
async def set_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للمشرف فقط!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 الاستخدام: /setduration <رقم>\nمثال: /setduration 30"
        )
        return
    
    try:
        duration = int(context.args[0])
        if duration <= 0:
            await update.message.reply_text("❌ يجب أن يكون الرقم أكبر من الصفر!")
            return
            
        set_setting('delete_duration', duration)
        unit = get_setting('delete_unit')
        unit_text = get_unit_text(unit)
        
        await update.message.reply_text(f'✅ تم تعيين مدة الحذف إلى {duration} {unit_text}')
        
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!")

# ==========================================
# الجدولة والمهام الخلفية
# ==========================================
def schedule_jobs():
    schedule.every(1).minutes.do(delete_old_messages)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    logger.info("🚀 بدء تشغيل البوت...")
    
    # تهيئة قاعدة البيانات
    init_db()
    
    # بدء خادم الويب في thread منفصل
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("🌐 خادم الويب يعمل...")
    
    # بدء الجدولة في thread منفصل
    scheduler_thread = threading.Thread(target=schedule_jobs, daemon=True)
    scheduler_thread.start()
    logger.info("⏰ نظام الجدولة يعمل...")
    
    # إنشاء تطبيق البوت
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("setduration", set_duration))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت جاهز للعمل!")
    
    # بدء البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

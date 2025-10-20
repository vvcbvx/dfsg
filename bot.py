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
    return """
    <html>
        <head>
            <title>Telegram Invoice Bot</title>
            <meta http-equiv="refresh" content="30">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f2f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .status { color: #22c55e; font-weight: bold; font-size: 18px; }
                .info { color: #666; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Telegram Invoice Bot</h1>
                <p class="status">✅ البوت يعمل بنجاح!</p>
                <p class="info">⏰ آخر تحديث: {}</p>
                <p class="info">🌐 البوت نشط 24/7 على Render</p>
                <p class="info">📞 للحصول على المساعدة: @hitham_bot</p>
            </div>
        </body>
    </html>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": str(datetime.now()), "service": "telegram-invoice-bot"}

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

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
            delete_at TIMESTAMP,
            is_deleted BOOLEAN DEFAULT FALSE
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

def get_unit_emoji(unit):
    emojis = {
        'seconds': '⏱️',
        'minutes': '⏰', 
        'hours': '🕐',
        'days': '📅'
    }
    return emojis.get(unit, '⏰')

# ==========================================
# إدارة الرسائل
# ==========================================
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

async def delete_single_message(chat_id, message_id):
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        await application.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception as e:
        logger.error(f"❌ فشل في حذف الرسالة {message_id}: {e}")
        return False

def delete_old_messages():
    if get_setting('auto_delete_enabled') == 'false':
        return
        
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT message_id, chat_id FROM invoices WHERE delete_at <= datetime('now') AND is_deleted = FALSE")
    old_messages = cursor.fetchall()
    
    deleted_count = 0
    for message_id, chat_id in old_messages:
        try:
            # استخدام asyncio لحذف الرسائل
            asyncio.run(delete_single_message(chat_id, message_id))
            cursor.execute("UPDATE invoices SET is_deleted = TRUE WHERE message_id = ? AND chat_id = ?", (message_id, chat_id))
            deleted_count += 1
        except Exception as e:
            logger.error(f"❌ خطأ في حذف الرسالة {message_id}: {e}")
    
    conn.commit()
    conn.close()
    
    if deleted_count > 0:
        logger.info(f"✅ تم حذف {deleted_count} رسالة")

# ==========================================
# أوامر البوت الرئيسية
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    duration = get_setting('delete_duration')
    unit = get_setting('delete_unit')
    unit_text = get_unit_text(unit)
    unit_emoji = get_unit_emoji(unit)
    
    keyboard = [
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="main_settings")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ المساعدة", callback_data="help_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f'''
🎉 **مرحباً {user.first_name}!**

🤖 أنا بوت إدارة الفواتير الذكي

{unit_emoji} **الإعدادات الحالية:**
• مدة الحذف: {duration} {unit_text}
• الحذف التلقائي: {"✅ مفعل" if get_setting('auto_delete_enabled') == 'true' else "❌ معطل"}

📨 **كيفية الاستخدام:**
ما عليك سوى إرسال أي فاتورة أو تعديل وسأقوم بحفظها وحذفها تلقائياً بعد المدة المحددة.
'''
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = '''
📋 **أوامر البوت:**

/start - بدء استخدام البوت
/settings - إعدادات متقدمة (للمشرف)
/status - عرض إحصائيات النظام
/help - عرض المساعدة

🎛️ **الميزات المتاحة:**
• ⏱️ تحديد مدة الحذف بالثواني، الدقائق، الساعات، أو الأيام
• 🔄 تفعيل/تعطيل الحذف التلقائي
• 📊 إحصائيات مفصلة عن الرسائل
• 🎯 واجهة تفاعلية سهلة الاستخدام

🔧 **للمشرفين:**
• التحكم الكامل في إعدادات الحذف
• مراقبة أداء النظام
• إدارة كافة الرسائل
'''
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM invoices")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE delete_at <= datetime('now') AND is_deleted = FALSE")
    pending_deletion = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE file_type IS NOT NULL")
    files_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE created_at >= datetime('now', '-1 day')")
    last_24h = cursor.fetchone()[0]
    
    duration = get_setting('delete_duration')
    unit = get_setting('delete_unit')
    unit_text = get_unit_text(unit)
    auto_delete = get_setting('auto_delete_enabled')
    
    status_text = f'''
📊 **حالة النظام التفصيلية**

• 📨 إجمالي الرسائل: {total_messages}
• ⏳ المعلقة للحذف: {pending_deletion}
• 📎 الملفات المرفوعة: {files_count}
• 🆕 آخر 24 ساعة: {last_24h}
• ⚙️ مدة الحذف: {duration} {unit_text}
• 🔄 الحذف التلقائي: {"✅ مفعل" if auto_delete == 'true' else "❌ معطل"}
• 🕒 آخر تحديث: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
'''
    await update.message.reply_text(status_text, parse_mode='Markdown')

# ==========================================
# معالجة الأزرار والواجهة التفاعلية
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
    elif data.startswith("dur_"):
        await set_duration_callback(query, data)
    elif data == "main_menu":
        await main_menu(query)
    elif data == "refresh_stats":
        await show_stats(query)

async def show_main_settings(query):
    if str(query.from_user.id) != ADMIN_ID:
        await query.edit_message_text("❌ هذا القسم للمشرف فقط!")
        return
    
    duration = get_setting('delete_duration')
    unit = get_setting('delete_unit')
    unit_text = get_unit_text(unit)
    unit_emoji = get_unit_emoji(unit)
    auto_delete = get_setting('auto_delete_enabled')
    
    keyboard = [
        [InlineKeyboardButton(f"{unit_emoji} تغيير المدة ({duration} {unit_text})", callback_data="change_duration")],
        [InlineKeyboardButton("🕒 تغيير الوحدة الزمنية", callback_data="change_unit")],
        [InlineKeyboardButton(f"🔧 الحذف التلقائي: {'✅ مفعل' if auto_delete == 'true' else '❌ معطل'}", callback_data="toggle_auto_delete")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f'⚙️ **الإعدادات المتقدمة**\n\n'
        f'• المدة الحالية: {duration} {unit_text}\n'
        f'• الحذف التلقائي: {"✅ مفعل" if auto_delete == 'true' else "❌ معطل"}\n\n'
        'اختر الإعداد الذي تريد تعديله:',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def change_duration(query):
    keyboard = [
        [InlineKeyboardButton("⏱️ 30 ثانية", callback_data="dur_30"), InlineKeyboardButton("⏱️ 60 ثانية", callback_data="dur_60")],
        [InlineKeyboardButton("⏰ 5 دقائق", callback_data="dur_5"), InlineKeyboardButton("⏰ 10 دقائق", callback_data="dur_10")],
        [InlineKeyboardButton("🕐 1 ساعة", callback_data="dur_1"), InlineKeyboardButton("🕐 6 ساعات", callback_data="dur_6")],
        [InlineKeyboardButton("📅 24 ساعة", callback_data="dur_24"), InlineKeyboardButton("📅 3 أيام", callback_data="dur_72")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        '🔢 **تغيير مدة الحذف**\n\n'
        'اختر من المدد الجاهزة أو استخدم /setduration لكتابة رقم مخصص:\n\n'
        '💡 **المدد المقترحة:**\n'
        '• 30-60 ثانية: للتجارب السريعة\n'
        '• 5-10 دقائق: للاختبارات\n'
        '• 1-6 ساعات: للاستخدام اليومي\n'
        '• 24+ ساعة: للتخزين المؤقت',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def change_unit(query):
    current_unit = get_setting('delete_unit')
    keyboard = [
        [InlineKeyboardButton(f"⏱️ الثواني {'✅' if current_unit == 'seconds' else ''}", callback_data="unit_seconds")],
        [InlineKeyboardButton(f"⏰ الدقائق {'✅' if current_unit == 'minutes' else ''}", callback_data="unit_minutes")],
        [InlineKeyboardButton(f"🕐 الساعات {'✅' if current_unit == 'hours' else ''}", callback_data="unit_hours")],
        [InlineKeyboardButton(f"📅 الأيام {'✅' if current_unit == 'days' else ''}", callback_data="unit_days")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        '🕒 **تغيير وحدة الوقت**\n\n'
        'اختر الوحدة الزمنية المناسبة لاحتياجاتك:\n\n'
        '• ⏱️ الثواني: للحذف السريع\n'
        '• ⏰ الدقائق: للاختبارات\n'
        '• 🕐 الساعات: للاستخدام اليومي\n'
        '• 📅 الأيام: للتخزين المؤقت',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def set_time_unit(query, data):
    unit = data.replace("unit_", "")
    set_setting('delete_unit', unit)
    unit_text = get_unit_text(unit)
    unit_emoji = get_unit_emoji(unit)
    
    await query.edit_message_text(f'✅ {unit_emoji} تم تغيير وحدة الوقت إلى: **{unit_text}**', parse_mode='Markdown')

async def set_duration_callback(query, data):
    duration = data.replace("dur_", "")
    set_setting('delete_duration', duration)
    unit = get_setting('delete_unit')
    unit_text = get_unit_text(unit)
    unit_emoji = get_unit_emoji(unit)
    
    await query.edit_message_text(f'✅ {unit_emoji} تم تعيين مدة الحذف إلى: **{duration} {unit_text}**', parse_mode='Markdown')

async def toggle_auto_delete(query):
    current = get_setting('auto_delete_enabled')
    new_value = 'false' if current == 'true' else 'true'
    set_setting('auto_delete_enabled', new_value)
    
    status_text = "تفعيل" if new_value == 'true' else "تعطيل"
    emoji = "✅" if new_value == 'true' else "❌"
    
    await query.edit_message_text(f'{emoji} تم **{status_text}** الحذف التلقائي', parse_mode='Markdown')

async def show_stats(query):
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM invoices")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE delete_at <= datetime('now') AND is_deleted = FALSE")
    pending = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE file_type IS NOT NULL")
    files = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE created_at >= datetime('now', '-1 day')")
    last_24h = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE is_deleted = TRUE")
    deleted = cursor.fetchone()[0]
    
    duration = get_setting('delete_duration')
    unit = get_setting('delete_unit')
    unit_text = get_unit_text(unit)
    auto_delete = get_setting('auto_delete_enabled')
    
    keyboard = [
        [InlineKeyboardButton("🔄 تحديث", callback_data="refresh_stats")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="main_settings")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    stats_text = f'''
📈 **إحصائيات مفصلة**

• 📊 إجمالي الرسائل: **{total}**
• ⏳ معلقة للحذف: **{pending}**
• 🗑️ تم حذفها: **{deleted}**
• 📎 ملفات مرفوعة: **{files}**
• 🆕 آخر 24 ساعة: **{last_24h}**

⚙️ **الإعدادات:**
• مدة الحذف: **{duration} {unit_text}**
• الحذف التلقائي: **{"✅ مفعل" if auto_delete == 'true' else "❌ معطل"}**

🕒 آخر تحديث: {datetime.now().strftime("%H:%M:%S")}
'''
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_help(query):
    help_text = '''
🎯 **كيفية الاستخدام:**

1. **أرسل أي فاتورة أو تعديل** 📨
2. **سأقوم بحفظها تلقائياً** 💾
3. **سيتم حذفها بعد المدة المحددة** ⏰

⚙️ **الإعدادات المتاحة:**
• ⏱️ تغيير مدة الحذف (ثواني، دقائق، ساعات، أيام)
• 🔄 تفعيل/تعطيل الحذف التلقائي
• 📊 متابعة الإحصائيات الحيوية

🔧 **للمشرف:** استخدم /settings للتحكم الكامل في الإعدادات
'''
    keyboard = [
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="main_settings")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def main_menu(query):
    user = query.from_user
    duration = get_setting('delete_duration')
    unit = get_setting('delete_unit')
    unit_text = get_unit_text(unit)
    unit_emoji = get_unit_emoji(unit)
    
    keyboard = [
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="main_settings")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ المساعدة", callback_data="help_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f'''
🎉 **مرحباً {user.first_name}!**

🤖 أنا بوت إدارة الفواتير الذكي

{unit_emoji} **الإعدادات الحالية:**
• مدة الحذف: {duration} {unit_text}
• الحذف التلقائي: {"✅ مفعل" if get_setting('auto_delete_enabled') == 'true' else "❌ معطل"}

📨 **كيفية الاستخدام:**
ما عليك سوى إرسال أي فاتورة أو تعديل وسأقوم بحفظها وحذفها تلقائياً بعد المدة المحددة.
'''
    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

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
    elif message.voice:
        file_type = "voice"
    elif message.sticker:
        file_type = "sticker"
    
    # حفظ الرسالة
    save_message(message.message_id, message.chat_id, content, file_type)
    
    # إرسال تأكيد
    if message.chat.type == 'private':
        duration = get_setting('delete_duration')
        unit = get_setting('delete_unit')
        unit_text = get_unit_text(unit)
        unit_emoji = get_unit_emoji(unit)
        
        confirmation_text = f'''
✅ تم استلام {get_file_type_text(file_type)} بنجاح!

{unit_emoji} **سيتم حذفها تلقائياً بعد:** {duration} {unit_text}

💾 **تم الحفظ في قاعدة البيانات**
'''
        await message.reply_text(
            confirmation_text,
            reply_to_message_id=message.message_id,
            parse_mode='Markdown'
        )

def get_file_type_text(file_type):
    types = {
        'text': 'الرسالة النصية',
        'caption': 'النص المصاحب',
        'document': 'الملف',
        'photo': 'الصورة',
        'video': 'الفيديو',
        'audio': 'الصوت',
        'voice': 'التسجيل الصوتي',
        'sticker': 'الملصق'
    }
    return types.get(file_type, 'الرسالة')

# ==========================================
# الأوامر الإضافية
# ==========================================
async def set_duration_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للمشرف فقط!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 **الاستخدام:** `/setduration <رقم>`\n"
            "**مثال:** `/setduration 30`\n"
            "**مثال:** `/setduration 120`",
            parse_mode='Markdown'
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
        unit_emoji = get_unit_emoji(unit)
        
        await update.message.reply_text(
            f'✅ {unit_emoji} تم تعيين مدة الحذف إلى: **{duration} {unit_text}**',
            parse_mode='Markdown'
        )
        
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

def run_scheduler():
    scheduler_thread = threading.Thread(target=schedule_jobs, daemon=True)
    scheduler_thread.start()
    logger.info("⏰ نظام الجدولة يعمل...")

# ==========================================
# التشغيل الرئيسي
# ==========================================
def main():
    logger.info("🚀 بدء تشغيل البوت...")
    
    # التحقق من وجود التوكن
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN غير موجود!")
        return
    if not ADMIN_ID:
        logger.error("❌ ADMIN_ID غير موجود!")
        return
    
    # تهيئة قاعدة البيانات
    init_db()
    
    # بدء خادم الويب
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("🌐 خادم الويب يعمل...")
    
    # بدء الجدولة
    run_scheduler()
    
    # إنشاء تطبيق البوت
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("setduration", set_duration_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت جاهز للعمل!")
    logger.info(f"🌐 رابط الخدمة: https://dfsg-0oqu.onrender.com")
    
    # بدء البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()

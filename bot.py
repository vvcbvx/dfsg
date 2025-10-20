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
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ==========================================
# إعداد Flask
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
    <html>
        <head>
            <title>Telegram Invoice Bot</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
                .status {{ color: #22c55e; font-weight: bold; font-size: 20px; margin: 20px 0; }}
                .info {{ color: #666; margin: 10px 0; font-size: 16px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="color: #333;">🤖 Telegram Invoice Bot</h1>
                <p class="status">✅ البوت يعمل بنجاح!</p>
                <p class="info">⏰ آخر تحديث: {current_time}</p>
                <p class="info">🌐 نظام الحذف التلقائي نشط</p>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": str(datetime.now()), "deletion_system": "active"}

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

# ==========================================
# إعدادات البوت
# ==========================================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

# حالات المحادثة
CUSTOM_DURATION = 1

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# قاعدة البيانات المتقدمة
# ==========================================
def init_db():
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول الرسائل مع تفاصيل الوقت
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT,
            file_type TEXT,
            message_date TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delete_at TIMESTAMP NOT NULL,
            is_deleted BOOLEAN DEFAULT FALSE,
            delete_reason TEXT
        )
    ''')
    
    # جدول الإعدادات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # جدول سجل الحذف
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deletion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            chat_id INTEGER,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT
        )
    ''')
    
    # الإعدادات الافتراضية
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('delete_duration', '1440')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('delete_unit', 'minutes')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_delete_enabled', 'true')")
    
    conn.commit()
    conn.close()
    logger.info("✅ قاعدة البيانات المهيأة مع نظام التوقيت المتقدم")

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
# نظام التوقيت والحذف المتقدم
# ==========================================
def calculate_delete_time(message_date):
    """حساب وقت الحذف بناءً على وقت الرسالة والمدة المحددة"""
    duration = int(get_setting('delete_duration', 1440))
    unit = get_setting('delete_unit', 'minutes')
    
    # حساب المدة المضافة بناءً على الوحدة
    if unit == 'seconds':
        delete_delta = timedelta(seconds=duration)
    elif unit == 'minutes':
        delete_delta = timedelta(minutes=duration)
    elif unit == 'hours':
        delete_delta = timedelta(hours=duration)
    elif unit == 'days':
        delete_delta = timedelta(days=duration)
    else:
        delete_delta = timedelta(minutes=1440)
    
    # وقت الحذف = وقت الرسالة + المدة المحددة
    delete_at = message_date + delete_delta
    return delete_at

def get_time_remaining(delete_at):
    """حساب الوقت المتبقي للحذف"""
    now = datetime.now()
    remaining = delete_at - now
    
    if remaining.total_seconds() <= 0:
        return "⏰ انتهى الوقت - جاهز للحذف"
    
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    seconds = remaining.seconds % 60
    
    if days > 0:
        return f"⏳ {days} يوم {hours} ساعة {minutes} دقيقة"
    elif hours > 0:
        return f"⏳ {hours} ساعة {minutes} دقيقة {seconds} ثانية"
    elif minutes > 0:
        return f"⏳ {minutes} دقيقة {seconds} ثانية"
    else:
        return f"⏳ {seconds} ثانية"

def format_duration(duration, unit):
    """تنسيق عرض المدة"""
    unit_text = get_unit_text(unit)
    
    if unit == 'seconds':
        if duration < 60:
            return f"{duration} ثانية"
        elif duration < 3600:
            return f"{duration//60} دقيقة {duration%60} ثانية"
        else:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            return f"{hours} ساعة {minutes} دقيقة"
    
    elif unit == 'minutes':
        if duration < 60:
            return f"{duration} دقيقة"
        else:
            hours = duration // 60
            minutes = duration % 60
            return f"{hours} ساعة {minutes} دقيقة"
    
    elif unit == 'hours':
        if duration < 24:
            return f"{duration} ساعة"
        else:
            days = duration // 24
            hours = duration % 24
            return f"{days} يوم {hours} ساعة"
    
    else:
        return f"{duration} {unit_text}"

def get_unit_text(unit):
    units = {
        'seconds': 'ثانية',
        'minutes': 'دقيقة', 
        'hours': 'ساعة',
        'days': 'يوم'
    }
    return units.get(unit, 'دقيقة')

def get_unit_emoji(unit):
    emojis = {
        'seconds': '⏱️',
        'minutes': '⏰', 
        'hours': '🕐',
        'days': '📅'
    }
    return emojis.get(unit, '⏰')

# ==========================================
# إدارة الرسائل - النظام المتقدم
# ==========================================
def save_message(message_id, chat_id, user_id, content, file_type, message_date):
    """حفظ الرسالة مع حساب وقت الحذف بدقة"""
    if get_setting('auto_delete_enabled') == 'false':
        return
    
    # حساب وقت الحذف بناءً على وقت الرسالة الأصلي
    delete_at = calculate_delete_time(message_date)
    
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO messages 
        (message_id, chat_id, user_id, content, file_type, message_date, delete_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (message_id, chat_id, user_id, content, file_type, message_date, delete_at)
    )
    conn.commit()
    conn.close()
    
    logger.info(f"💾 تم حفظ الرسالة {message_id} - الحذف: {delete_at}")

async def delete_single_message(chat_id, message_id):
    """حذف رسالة واحدة مع التعامل مع الأخطاء"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        await application.bot.delete_message(chat_id=chat_id, message_id=message_id)
        
        # تسجيل عملية الحذف
        conn = sqlite3.connect('invoices.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO deletion_log (message_id, chat_id, reason) VALUES (?, ?, ?)",
            (message_id, chat_id, "auto_delete_time_reached")
        )
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ فشل في حذف الرسالة {message_id}: {error_msg}")
        
        # تحديث حالة الرسالة مع سبب الفشل
        conn = sqlite3.connect('invoices.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE messages SET is_deleted = TRUE, delete_reason = ? WHERE message_id = ? AND chat_id = ?",
            (f"delete_failed: {error_msg}", message_id, chat_id)
        )
        conn.commit()
        conn.close()
        
        return False

def check_and_delete_messages():
    """فحص وحذف الرسائل التي انتهى وقتها"""
    if get_setting('auto_delete_enabled') == 'false':
        return
    
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # الحصول على الرسائل التي انتهى وقتها ولم تحذف بعد
    cursor.execute("""
        SELECT message_id, chat_id, message_date, delete_at 
        FROM messages 
        WHERE delete_at <= datetime('now') 
        AND is_deleted = FALSE
    """)
    
    messages_to_delete = cursor.fetchall()
    deleted_count = 0
    failed_count = 0
    
    logger.info(f"🔍 فحص {len(messages_to_delete)} رسالة للحذف...")
    
    for message_id, chat_id, message_date, delete_at in messages_to_delete:
        try:
            # حذف الرسالة
            asyncio.run(delete_single_message(chat_id, message_id))
            
            # تحديث حالة الرسالة
            cursor.execute(
                "UPDATE messages SET is_deleted = TRUE, delete_reason = 'auto_deleted' WHERE message_id = ? AND chat_id = ?",
                (message_id, chat_id)
            )
            deleted_count += 1
            
            logger.info(f"✅ تم حذف الرسالة {message_id} التي أرسلت في {message_date}")
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الرسالة {message_id}: {e}")
            failed_count += 1
    
    conn.commit()
    conn.close()
    
    if deleted_count > 0 or failed_count > 0:
        logger.info(f"📊 نتائج الحذف: ✅ {deleted_count} نجح, ❌ {failed_count} فشل")

def get_message_status(message_id, chat_id):
    """الحصول على حالة رسالة محددة"""
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT message_date, delete_at, is_deleted, delete_reason 
        FROM messages 
        WHERE message_id = ? AND chat_id = ?
    """, (message_id, chat_id))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        message_date, delete_at, is_deleted, delete_reason = result
        time_remaining = get_time_remaining(delete_at) if not is_deleted else "✅ تم الحذف"
        
        return {
            'message_date': message_date,
            'delete_at': delete_at,
            'is_deleted': is_deleted,
            'delete_reason': delete_reason,
            'time_remaining': time_remaining,
            'exists': True
        }
    else:
        return {'exists': False}

# ==========================================
# نظام الجدولة المحسن
# ==========================================
def schedule_jobs():
    """جدولة المهام الدورية"""
    # فحص الرسائل كل 30 ثانية للتأكد من الحذف الفوري
    schedule.every(30).seconds.do(check_and_delete_messages)
    
    # تنظيف قاعدة البيانات كل ساعة
    schedule.every(1).hours.do(cleanup_database)
    
    # تسجيل حالة النظام كل 5 دقائق
    schedule.every(5).minutes.do(log_system_status)
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"❌ خطأ في الجدولة: {e}")
            time.sleep(10)

def cleanup_database():
    """تنظيف قاعدة البيانات من الرسائل المحذوفة قديماً"""
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # حذف الرسائل المحذوفة منذ أكثر من 7 أيام
    cursor.execute("DELETE FROM messages WHERE is_deleted = TRUE AND created_at <= datetime('now', '-7 days')")
    deleted_rows = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    if deleted_rows > 0:
        logger.info(f"🧹 تم تنظيف {deleted_rows} رسالة قديمة")

def log_system_status():
    """تسجيل حالة النظام"""
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE is_deleted = FALSE")
    active_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE delete_at <= datetime('now') AND is_deleted = FALSE")
    pending_deletion = cursor.fetchone()[0]
    
    conn.close()
    
    logger.info(f"📊 حالة النظام: {active_messages} رسالة نشطة, {pending_deletion} جاهزة للحذف")

# ==========================================
# أوامر البوت الرئيسية
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    duration = int(get_setting('delete_duration'))
    unit = get_setting('delete_unit')
    formatted_duration = format_duration(duration, unit)
    unit_emoji = get_unit_emoji(unit)
    
    keyboard = [
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="main_settings")],
        [InlineKeyboardButton("📊 حالة الرسائل", callback_data="messages_status")],
        [InlineKeyboardButton("⏰ تعديل المدة", callback_data="change_duration")],
        [InlineKeyboardButton("🔍 فحص رسالة", callback_data="check_message")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f'''
🎉 **مرحباً {user.mention_markdown()}!**

🤖 **أنا بوت إدارة الفواتير الذكي**

{unit_emoji} **نظام الحذف التلقائي:**
• المدة: **{formatted_duration}**
• الحالة: **{"✅ نشط" if get_setting('auto_delete_enabled') == 'true' else "❌ معطل"}**

💡 **كيف يعمل:**
1. أرسل أي رسالة
2. أحفظها مع وقت الإرسال
3. أحسب وقت الحذف بدقة
4. أحذفها تلقائياً عند انتهاء المدة

🔍 **لرؤية حالة أي رسالة:** اضغط على "فحص رسالة"
'''
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def check_message_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص حالة رسالة محددة"""
    if not context.args:
        await update.message.reply_text(
            "🔍 **لفحص حالة رسالة:**\n"
            "قم بالرد على الرسالة المراد فحصها واكتب:\n"
            "`/status`\n\n"
            "أو أرسل معرف الرسالة:\n"
            "`/status 123`",
            parse_mode='Markdown'
        )
        return
    
    try:
        message_id = int(context.args[0])
        chat_id = update.effective_chat.id
        
        status = get_message_status(message_id, chat_id)
        
        if status['exists']:
            if status['is_deleted']:
                status_text = f'''
❌ **الرسالة {message_id}**
• 📅 وقت الإرسال: `{status['message_date']}`
• 🗑️ تم الحذف في: `{status['delete_at']}`
• 📋 السبب: `{status['delete_reason']}`
'''
            else:
                status_text = f'''
📨 **الرسالة {message_id}**
• 📅 وقت الإرسال: `{status['message_date']}`
• ⏰ سيحذف في: `{status['delete_at']}`
• ⏳ الوقت المتبقي: **{status['time_remaining']}**
'''
        else:
            status_text = f"❌ لم أجد الرسالة {message_id} في قاعدة البيانات"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال معرف رسالة صحيح (رقم)")

async def handle_reply_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرد على رسالة لفحص حالتها"""
    if update.message.reply_to_message:
        message_id = update.message.reply_to_message.message_id
        chat_id = update.effective_chat.id
        
        status = get_message_status(message_id, chat_id)
        
        if status['exists']:
            if status['is_deleted']:
                status_text = f'''
❌ **الرسالة التي تم الرد عليها**
• 📅 وقت الإرسال: `{status['message_date']}`
• 🗑️ تم الحذف في: `{status['delete_at']}`
• 📋 السبب: `{status['delete_reason']}`
'''
            else:
                status_text = f'''
📨 **الرسالة التي تم الرد عليها**
• 📅 وقت الإرسال: `{status['message_date']}`
• ⏰ سيحذف في: `{status['delete_at']}`
• ⏳ الوقت المتبقي: **{status['time_remaining']}**
'''
            await update.message.reply_text(status_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ هذه الرسالة غير مسجلة في النظام")

# ==========================================
# معالجة الرسائل - النظام المتقدم
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع الرسائل الواردة"""
    message = update.message
    user = message.from_user
    
    # استخراج وقت الرسالة الأصلي
    message_date = message.date.replace(tzinfo=None) if message.date.tzinfo else message.date
    
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
    
    # حفظ الرسالة مع الوقت الدقيق
    save_message(
        message_id=message.message_id,
        chat_id=message.chat_id,
        user_id=user.id,
        content=content,
        file_type=file_type,
        message_date=message_date
    )
    
    # إرسال تأكيد مع تفاصيل الوقت
    if message.chat.type == 'private':
        duration = int(get_setting('delete_duration'))
        unit = get_setting('delete_unit')
        formatted_duration = format_duration(duration, unit)
        unit_emoji = get_unit_emoji(unit)
        
        # حساب وقت الحذف الدقيق
        delete_at = calculate_delete_time(message_date)
        time_remaining = get_time_remaining(delete_at)
        
        confirmation_text = f'''
✅ **تم استلام الرسالة بنجاح!**

📨 **التفاصيل:**
• 🆔 معرف الرسالة: `{message.message_id}`
• 📅 وقت الإرسال: `{message_date.strftime("%Y-%m-%d %H:%M:%S")}`
• {unit_emoji} مدة الحذف: **{formatted_duration}**
• ⏰ وقت الحذف: `{delete_at.strftime("%Y-%m-%d %H:%M:%S")}`
• ⏳ الحالة: **{time_remaining}**

💾 **تم الحفظ في النظام وسيتم الحذف التلقائي عند انتهاء المدة.**
'''
        await message.reply_text(
            confirmation_text,
            reply_to_message_id=message.message_id,
            parse_mode='Markdown'
        )

# ==========================================
# الواجهة التفاعلية
# ==========================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "main_settings":
        await show_main_settings(query)
    elif data == "messages_status":
        await show_messages_status(query)
    elif data == "change_duration":
        await change_duration_menu(query)
    elif data == "check_message":
        await query.edit_message_text(
            "🔍 **لفحص حالة رسالة:**\n"
            "قم بالرد على الرسالة واكتب:\n"
            "`/status`\n\n"
            "أو أرسل:\n"
            "`/status [معرف_الرسالة]`",
            parse_mode='Markdown'
        )

async def show_main_settings(query):
    duration = int(get_setting('delete_duration'))
    unit = get_setting('delete_unit')
    formatted_duration = format_duration(duration, unit)
    unit_emoji = get_unit_emoji(unit)
    
    keyboard = [
        [InlineKeyboardButton(f"{unit_emoji} تغيير المدة", callback_data="change_duration")],
        [InlineKeyboardButton("📊 حالة النظام", callback_data="messages_status")],
        [InlineKeyboardButton("🔄 تشغيل/إيقاف الحذف", callback_data="toggle_auto_delete")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f'⚙️ **إعدادات النظام**\n\n'
        f'• {unit_emoji} المدة الحالية: **{formatted_duration}**\n'
        f'• 🔄 الحذف التلقائي: **{"✅ نشط" if get_setting('auto_delete_enabled') == 'true' else "❌ معطل"}**\n\n'
        'اختر الإعداد الذي تريد تعديله:',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_messages_status(query):
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE is_deleted = FALSE")
    active_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE delete_at <= datetime('now') AND is_deleted = FALSE")
    pending_deletion = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE is_deleted = TRUE")
    deleted_messages = cursor.fetchone()[0]
    
    # أحدث 5 رسائل
    cursor.execute("""
        SELECT message_id, message_date, delete_at 
        FROM messages 
        WHERE is_deleted = FALSE 
        ORDER BY message_date DESC 
        LIMIT 5
    """)
    recent_messages = cursor.fetchall()
    
    conn.close()
    
    status_text = f'''
📊 **حالة الرسائل في النظام**

• 📨 الرسائل النشطة: **{active_messages}**
• ⏳ جاهزة للحذف: **{pending_deletion}**
• 🗑️ تم حذفها: **{deleted_messages}**

📋 **أحدث الرسائل:**
'''
    
    for msg_id, msg_date, delete_at in recent_messages:
        time_remaining = get_time_remaining(delete_at)
        status_text += f"• 🆔 {msg_id} - ⏳ {time_remaining}\n"
    
    status_text += f"\n🕒 آخر تحديث: {datetime.now().strftime('%H:%M:%S')}"
    
    keyboard = [[InlineKeyboardButton("🔄 تحديث", callback_data="messages_status")],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')

async def change_duration_menu(query):
    duration = int(get_setting('delete_duration'))
    unit = get_setting('delete_unit')
    current_setting = format_duration(duration, unit)
    
    keyboard = [
        [InlineKeyboardButton("⏱️ 30 ثانية", callback_data="dur_30_seconds")],
        [InlineKeyboardButton("⏱️ 5 دقائق", callback_data="dur_300_seconds")],
        [InlineKeyboardButton("⏰ 30 دقيقة", callback_data="dur_30_minutes")],
        [InlineKeyboardButton("🕐 1 ساعة", callback_data="dur_1_hours")],
        [InlineKeyboardButton("🕐 6 ساعات", callback_data="dur_6_hours")],
        [InlineKeyboardButton("📅 1 يوم", callback_data="dur_1_days")],
        [InlineKeyboardButton("📅 7 أيام", callback_data="dur_7_days")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f'⏰ **تغيير مدة الحذف**\n\n'
        f'المدة الحالية: **{current_setting}**\n\n'
        'اختر من المدد الجاهزة:',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def toggle_auto_delete(query):
    current = get_setting('auto_delete_enabled')
    new_value = 'false' if current == 'true' else 'true'
    set_setting('auto_delete_enabled', new_value)
    
    status = "تشغيل" if new_value == 'true' else "إيقاف"
    emoji = "✅" if new_value == 'true' else "❌"
    
    await query.edit_message_text(f'{emoji} تم **{status}** الحذف التلقائي', parse_mode='Markdown')

async def back_to_main(query):
    await start(query, None)

# ==========================================
# التشغيل الرئيسي
# ==========================================
def main():
    logger.info("🚀 بدء تشغيل البوت المتقدم...")
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN غير موجود!")
        return
    
    # تهيئة قاعدة البيانات
    init_db()
    
    # بدء خادم الويب
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("🌐 خادم الويب يعمل...")
    
    # بدء نظام الجدولة
    scheduler_thread = threading.Thread(target=schedule_jobs, daemon=True)
    scheduler_thread.start()
    logger.info("⏰ نظام الجدولة يعمل...")
    
    # إنشاء تطبيق البوت
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", check_message_status))
    application.add_handler(CommandHandler("status", handle_reply_status))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت المتقدم جاهز للعمل!")
    
    # بدء البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()

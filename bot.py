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
                .btn {{ display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="color: #333;">🤖 Telegram Invoice Bot</h1>
                <p class="status">✅ البوت يعمل بنجاح!</p>
                <p class="info">⏰ آخر تحديث: {current_time}</p>
                <p class="info">🌐 البوت نشط 24/7 على Render</p>
                <p class="info">🚀 إصدار 2.0 - واجهة تفاعلية متقدمة</p>
                <a href="https://t.me/your_bot" class="btn">💬 ابدأ المحادثة</a>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": str(datetime.now()), "version": "2.0"}

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

# ==========================================
# إعدادات البوت
# ==========================================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

# حالات المحادثة
SETTING_DURATION, SETTING_UNIT, CUSTOM_DURATION = range(3)

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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            messages_count INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('delete_duration', '1440')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('delete_unit', 'minutes')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_delete_enabled', 'true')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('notifications_enabled', 'true')")
    
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

def update_user_stats(user_id):
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_stats (user_id, messages_count, last_active)
        VALUES (?, COALESCE((SELECT messages_count FROM user_stats WHERE user_id = ?), 0) + 1, CURRENT_TIMESTAMP)
    ''', (user_id, user_id))
    conn.commit()
    conn.close()

# ==========================================
# دوال المساعدة
# ==========================================
def calculate_delete_time():
    duration = int(get_setting('delete_duration', 1440))
    unit = get_setting('delete_unit', 'minutes')
    
    if unit == 'seconds':
        return timedelta(seconds=duration)
    elif unit == 'minutes':
        return timedelta(minutes=duration)
    elif unit == 'hours':
        return timedelta(hours=duration)
    elif unit == 'days':
        return timedelta(days=duration)
    else:
        return timedelta(minutes=1440)

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

def format_duration(duration, unit):
    unit_text = get_unit_text(unit)
    unit_emoji = get_unit_emoji(unit)
    
    if unit == 'seconds':
        if duration < 60:
            return f"{duration} {unit_text}"
        elif duration < 3600:
            return f"{duration//60} دقيقة {duration%60} ثانية"
        else:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            return f"{hours} ساعة {minutes} دقيقة"
    
    elif unit == 'minutes':
        if duration < 60:
            return f"{duration} {unit_text}"
        else:
            hours = duration // 60
            minutes = duration % 60
            return f"{hours} ساعة {minutes} دقيقة"
    
    elif unit == 'hours':
        if duration < 24:
            return f"{duration} {unit_text}"
        else:
            days = duration // 24
            hours = duration % 24
            return f"{days} يوم {hours} ساعة"
    
    else:
        return f"{duration} {unit_text}"

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
    update_user_stats(user.id)
    
    duration = int(get_setting('delete_duration'))
    unit = get_setting('delete_unit')
    formatted_duration = format_duration(duration, unit)
    unit_emoji = get_unit_emoji(unit)
    
    keyboard = [
        [InlineKeyboardButton("⚙️ الإعدادات المتقدمة", callback_data="main_settings")],
        [InlineKeyboardButton("📊 لوحة التحكم", callback_data="dashboard")],
        [InlineKeyboardButton("⏰ تعديل مدة الحذف", callback_data="change_duration")],
        [InlineKeyboardButton("ℹ️ المساعدة", callback_data="help_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f'''
🎉 **مرحباً {user.mention_markdown()}!**

🤖 **أنا بوت إدارة الفواتير الذكي المتقدم**

{unit_emoji} **الإعدادات الحالية:**
• ⏰ مدة الحذف: {formatted_duration}
• 🔄 الحذف التلقائي: {"✅ مفعل" if get_setting('auto_delete_enabled') == 'true' else "❌ معطل"}
• 🔔 الإشعارات: {"✅ مفعلة" if get_setting('notifications_enabled') == 'true' else "❌ معطلة"}

📨 **كيفية الاستخدام:**
ما عليك سوى إرسال أي فاتورة أو تعديل وسأقوم بحفظها وحذفها تلقائياً بعد المدة المحددة.

🎯 **الميزات الجديدة:**
• ⏱️ تحديد المدة بالثواني، الدقائق، الساعات، الأيام
• 🎛️ واجهة تفاعلية متقدمة
• 📈 إحصائيات مفصلة
• ⚡ إعدادات سريعة
'''
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = '''
📋 **أوامر البوت المتقدمة:**

/start - بدء استخدام البوت
/settings - الإعدادات المتقدمة
/status - إحصائيات النظام
/setduration - تعيين مدة مخصصة
/help - عرض المساعدة

🎛️ **الميزات المتاحة:**
• ⏱️ تحديد مدة الحذف بالثواني، الدقائق، الساعات، الأيام
• 🔄 تفعيل/تعطيل الحذف التلقائي
• 🔔 التحكم في الإشعارات
• 📊 إحصائيات مفصلة في الوقت الحقيقي
• 🎯 واجهة تفاعلية متقدمة
• ⚡ إعدادات سريعة

🔧 **للمشرفين:**
• التحكم الكامل في إعدادات الحذف
• مراقبة أداء النظام
• إدارة كافة الرسائل
• إحصائيات المستخدمين
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
    
    cursor.execute("SELECT COUNT(*) FROM user_stats")
    active_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE created_at >= datetime('now', '-1 day')")
    last_24h = cursor.fetchone()[0]
    
    duration = int(get_setting('delete_duration'))
    unit = get_setting('delete_unit')
    formatted_duration = format_duration(duration, unit)
    auto_delete = get_setting('auto_delete_enabled')
    notifications = get_setting('notifications_enabled')
    
    status_text = f'''
📊 **لوحة التحكم - إحصائيات النظام**

• 📨 إجمالي الرسائل: **{total_messages}**
• ⏳ المعلقة للحذف: **{pending_deletion}**
• 📎 الملفات المرفوعة: **{files_count}**
• 👥 المستخدمين النشطين: **{active_users}**
• 🆕 آخر 24 ساعة: **{last_24h}**

⚙️ **الإعدادات الحالية:**
• ⏰ مدة الحذف: **{formatted_duration}**
• 🔄 الحذف التلقائي: **{"✅ مفعل" if auto_delete == 'true' else "❌ معطل"}**
• 🔔 الإشعارات: **{"✅ مفعلة" if notifications == 'true' else "❌ معطلة"}**

🕒 آخر تحديث: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
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
    elif data == "dashboard":
        await show_dashboard(query)
    elif data == "change_duration":
        await change_duration_menu(query)
    elif data == "help_main":
        await show_help(query)
    elif data == "quick_settings":
        await show_quick_settings(query)
    elif data.startswith("unit_"):
        await set_time_unit(query, data)
    elif data.startswith("duration_"):
        await set_quick_duration(query, data)
    elif data.startswith("toggle_"):
        await toggle_setting(query, data)
    elif data == "custom_duration":
        await start_custom_duration(query, context)
    elif data == "back_to_main":
        await main_menu(query)

async def show_main_settings(query):
    if str(query.from_user.id) != ADMIN_ID:
        await query.edit_message_text("❌ هذا القسم للمشرف فقط!")
        return
    
    duration = int(get_setting('delete_duration'))
    unit = get_setting('delete_unit')
    formatted_duration = format_duration(duration, unit)
    unit_emoji = get_unit_emoji(unit)
    auto_delete = get_setting('auto_delete_enabled')
    notifications = get_setting('notifications_enabled')
    
    keyboard = [
        [InlineKeyboardButton(f"{unit_emoji} تغيير مدة الحذف", callback_data="change_duration")],
        [InlineKeyboardButton("🕒 تغيير الوحدة الزمنية", callback_data="quick_settings")],
        [InlineKeyboardButton(f"🔧 الحذف التلقائي: {'✅' if auto_delete == 'true' else '❌'}", callback_data="toggle_auto_delete")],
        [InlineKeyboardButton(f"🔔 الإشعارات: {'✅' if notifications == 'true' else '❌'}", callback_data="toggle_notifications")],
        [InlineKeyboardButton("📊 لوحة التحكم", callback_data="dashboard")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f'⚙️ **الإعدادات المتقدمة**\n\n'
        f'• {unit_emoji} المدة الحالية: {formatted_duration}\n'
        f'• 🔄 الحذف التلقائي: {"✅ مفعل" if auto_delete == 'true' else "❌ معطل"}\n'
        f'• 🔔 الإشعارات: {"✅ مفعلة" if notifications == 'true' else "❌ معطلة"}\n\n'
        'اختر الإعداد الذي تريد تعديله:',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_dashboard(query):
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM invoices")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE delete_at <= datetime('now') AND is_deleted = FALSE")
    pending = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM user_stats")
    users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE created_at >= datetime('now', '-1 day')")
    today = cursor.fetchone()[0]
    
    duration = int(get_setting('delete_duration'))
    unit = get_setting('delete_unit')
    formatted_duration = format_duration(duration, unit)
    
    keyboard = [
        [InlineKeyboardButton("🔄 تحديث", callback_data="dashboard")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="main_settings")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    dashboard_text = f'''
📈 **لوحة التحكم - نظرة عامة**

📊 **الإحصائيات:**
• 📨 الرسائل الكلية: **{total}**
• ⏳ للحذف: **{pending}**
• 👥 المستخدمين: **{users}**
• 📈 اليوم: **{today}**

⚙️ **الإعدادات:**
• ⏰ مدة الحذف: **{formatted_duration}**
• 🔄 الحذف التلقائي: **{"✅" if get_setting('auto_delete_enabled') == 'true' else "❌"}**
• 🔔 الإشعارات: **{"✅" if get_setting('notifications_enabled') == 'true' else "❌"}**

🕒 {datetime.now().strftime("%H:%M:%S")}
'''
    await query.edit_message_text(dashboard_text, reply_markup=reply_markup, parse_mode='Markdown')

async def change_duration_menu(query):
    duration = int(get_setting('delete_duration'))
    unit = get_setting('delete_unit')
    current_setting = format_duration(duration, unit)
    
    keyboard = [
        [InlineKeyboardButton("⏱️ الثواني (30 ثانية)", callback_data="duration_30_seconds")],
        [InlineKeyboardButton("⏱️ الثواني (5 دقائق)", callback_data="duration_300_seconds")],
        [InlineKeyboardButton("⏰ الدقائق (10 دقائق)", callback_data="duration_10_minutes")],
        [InlineKeyboardButton("⏰ الدقائق (30 دقائق)", callback_data="duration_30_minutes")],
        [InlineKeyboardButton("🕐 الساعات (1 ساعة)", callback_data="duration_1_hours")],
        [InlineKeyboardButton("🕐 الساعات (6 ساعات)", callback_data="duration_6_hours")],
        [InlineKeyboardButton("📅 الأيام (1 يوم)", callback_data="duration_1_days")],
        [InlineKeyboardButton("📅 الأيام (3 أيام)", callback_data="duration_3_days")],
        [InlineKeyboardButton("🔢 مدة مخصصة", callback_data="custom_duration")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f'⏰ **تغيير مدة الحذف**\n\n'
        f'المدة الحالية: **{current_setting}**\n\n'
        'اختر من المدد الجاهزة أو اختر "مدة مخصصة" لإدخال قيمة محددة:\n\n'
        '💡 **المدد المقترحة:**\n'
        '• ⏱️ الثواني: للتجارب السريعة\n'
        '• ⏰ الدقائق: للاختبارات\n'
        '• 🕐 الساعات: للاستخدام اليومي\n'
        '• 📅 الأيام: للتخزين المؤقت',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_quick_settings(query):
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
        'اختر الوحدة الزمنية المناسبة:\n\n'
        '• ⏱️ **الثواني**: للحذف السريع الفوري\n'
        '• ⏰ **الدقائق**: للاختبارات والتجارب\n'
        '• 🕐 **الساعات**: للاستخدام اليومي العادي\n'
        '• 📅 **الأيام**: للتخزين المؤقت الطويل',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def set_time_unit(query, data):
    unit = data.replace("unit_", "")
    set_setting('delete_unit', unit)
    unit_text = get_unit_text(unit)
    unit_emoji = get_unit_emoji(unit)
    
    await query.edit_message_text(
        f'✅ {unit_emoji} تم تغيير وحدة الوقت إلى: **{unit_text}**\n\n'
        f'يمكنك الآن تعديل مدة الحذف باستخدام الوحدة الجديدة.',
        parse_mode='Markdown'
    )

async def set_quick_duration(query, data):
    parts = data.replace("duration_", "").split("_")
    duration = parts[0]
    unit = parts[1]
    
    set_setting('delete_duration', duration)
    set_setting('delete_unit', unit)
    
    formatted_duration = format_duration(int(duration), unit)
    unit_emoji = get_unit_emoji(unit)
    
    await query.edit_message_text(
        f'✅ {unit_emoji} تم تعيين مدة الحذف إلى: **{formatted_duration}**\n\n'
        f'جميع الرسائل الجديدة سيتم حذفها تلقائياً بعد هذه المدة.',
        parse_mode='Markdown'
    )

async def toggle_setting(query, data):
    setting = data.replace("toggle_", "")
    current = get_setting(setting)
    new_value = 'false' if current == 'true' else 'true'
    set_setting(setting, new_value)
    
    setting_names = {
        'auto_delete_enabled': ('الحذف التلقائي', '🔧'),
        'notifications_enabled': ('الإشعارات', '🔔')
    }
    
    name, emoji = setting_names.get(setting, ('الإعداد', '⚙️'))
    status_text = "تفعيل" if new_value == 'true' else "تعطيل"
    status_emoji = "✅" if new_value == 'true' else "❌"
    
    await query.edit_message_text(
        f'{status_emoji} {emoji} تم **{status_text}** {name}',
        parse_mode='Markdown'
    )

async def start_custom_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        '🔢 **إدخال مدة مخصصة**\n\n'
        'الرجاء إرسال الرقم الذي تريد تعيينه لمدة الحذف:\n\n'
        '💡 **أمثلة:**\n'
        '• `30` لـ 30 ثانية/دقيقة/ساعة (حسب الوحدة الحالية)\n'
        '• `120` لـ دقيقتين/ساعتين\n'
        '• `1440` لـ 24 ساعة (بالدقائق)\n\n'
        'الوحدة الحالية: ' + get_unit_text(get_setting('delete_unit'))
    )
    
    return CUSTOM_DURATION

async def receive_custom_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        duration = int(update.message.text)
        if duration <= 0:
            await update.message.reply_text("❌ الرقم يجب أن يكون أكبر من الصفر!")
            return CUSTOM_DURATION
            
        unit = get_setting('delete_unit')
        set_setting('delete_duration', duration)
        
        formatted_duration = format_duration(duration, unit)
        unit_emoji = get_unit_emoji(unit)
        
        await update.message.reply_text(
            f'✅ {unit_emoji} تم تعيين مدة الحذف إلى: **{formatted_duration}**\n\n'
            f'جميع الرسائل الجديدة سيتم حذفها تلقائياً بعد هذه المدة.',
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!")
        return CUSTOM_DURATION

async def cancel_custom_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم إلغاء تعيين المدة المخصصة.")
    return ConversationHandler.END

async def show_help(query):
    help_text = '''
🎯 **كيفية الاستخدام المتقدم:**

1. **أرسل أي فاتورة أو تعديل** 📨
2. **سأقوم بحفظها تلقائياً** 💾
3. **سيتم حذفها بعد المدة المحددة** ⏰

⚙️ **الإعدادات المتاحة:**
• ⏱️ تغيير مدة الحذف (ثواني، دقائق، ساعات، أيام)
• 🔄 تفعيل/تعطيل الحذف التلقائي
• 🔔 التحكم في الإشعارات
• 📊 متابعة الإحصائيات الحيوية

🎛️ **الواجهة التفاعلية:**
• استخدم الأزرار للتنقل السريع
• عدل الإعدادات بنقرة واحدة
• تابع الإحصائيات في الوقت الحقيقي
'''
    keyboard = [
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="main_settings")],
        [InlineKeyboardButton("📊 لوحة التحكم", callback_data="dashboard")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def main_menu(query):
    user = query.from_user
    duration = int(get_setting('delete_duration'))
    unit = get_setting('delete_unit')
    formatted_duration = format_duration(duration, unit)
    unit_emoji = get_unit_emoji(unit)
    
    keyboard = [
        [InlineKeyboardButton("⚙️ الإعدادات المتقدمة", callback_data="main_settings")],
        [InlineKeyboardButton("📊 لوحة التحكم", callback_data="dashboard")],
        [InlineKeyboardButton("⏰ تعديل مدة الحذف", callback_data="change_duration")],
        [InlineKeyboardButton("ℹ️ المساعدة", callback_data="help_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f'''
🎉 **مرحباً {user.mention_markdown()}!**

🤖 **أنا بوت إدارة الفواتير الذكي المتقدم**

{unit_emoji} **الإعدادات الحالية:**
• ⏰ مدة الحذف: {formatted_duration}
• 🔄 الحذف التلقائي: {"✅ مفعل" if get_setting('auto_delete_enabled') == 'true' else "❌ معطل"}

📨 **كيفية الاستخدام:**
ما عليك سوى إرسال أي فاتورة أو تعديل وسأقوم بحفظها وحذفها تلقائياً بعد المدة المحددة.
'''
    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# ==========================================
# معالجة الرسائل
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = message.from_user
    update_user_stats(user.id)
    
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
        duration = int(get_setting('delete_duration'))
        unit = get_setting('delete_unit')
        formatted_duration = format_duration(duration, unit)
        unit_emoji = get_unit_emoji(unit)
        
        confirmation_text = f'''
✅ تم استلام {get_file_type_text(file_type)} بنجاح!

{unit_emoji} **سيتم حذفها تلقائياً بعد:** {formatted_duration}

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
        'audio': 'الصوت'
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
            "📝 **الاستخدام:** `/setduration <رقم>`\n\n"
            "**أمثلة:**\n"
            "• `/setduration 30` لـ 30 ثانية/دقيقة\n"
            "• `/setduration 120` لـ دقيقتين/ساعتين\n"
            "• `/setduration 1440` لـ 24 ساعة\n\n"
            "💡 **الوحدة الحالية:** " + get_unit_text(get_setting('delete_unit')),
            parse_mode='Markdown'
        )
        return
    
    try:
        duration = int(context.args[0])
        if duration <= 0:
            await update.message.reply_text("❌ يجب أن يكون الرقم أكبر من الصفر!")
            return
            
        unit = get_setting('delete_unit')
        set_setting('delete_duration', duration)
        formatted_duration = format_duration(duration, unit)
        unit_emoji = get_unit_emoji(unit)
        
        await update.message.reply_text(
            f'✅ {unit_emoji} تم تعيين مدة الحذف إلى: **{formatted_duration}**',
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
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN غير موجود!")
        return
    
    init_db()
    
    # بدء خادم الويب
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("🌐 خادم الويب يعمل...")
    
    # بدء الجدولة
    run_scheduler()
    
    # إنشاء تطبيق البوت
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إعداد محادثة المدة المخصصة
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_custom_duration, pattern='^custom_duration$')],
        states={
            CUSTOM_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_duration)]
        },
        fallbacks=[CommandHandler('cancel', cancel_custom_duration)]
    )
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("setduration", set_duration_command))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت جاهز للعمل!")
    logger.info(f"🌐 رابط الخدمة: https://dfsg-zqpy.onrender.com")
    
    # بدء البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()

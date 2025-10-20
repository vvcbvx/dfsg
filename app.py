import os
import logging
import uuid
from flask import Flask, request, jsonify, render_template_string
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from threading import Thread
import time

# ========== إعدادات البوت ==========
BOT_TOKEN = "7388387809:AAHgsBR0z-avEVjjN2boGyXXwO2TR_T7hXA"  # غير هذا بتوكن بوتك
PORT = int(os.environ.get('PORT', 5000))

# ========== إعداد Flask ==========
app = Flask(__name__)

# إنشاء مجلد الصور إذا لم يكن موجوداً
if not os.path.exists('photos'):
    os.makedirs('photos')

# ========== HTML قوالب ==========
CAMERA_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>كاميرا البوت - {{user_id}}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 100%;
            margin: 0 auto;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            text-align: center;
        }
        
        h1 {
            color: #4a5568;
            margin-bottom: 10px;
            font-size: 24px;
        }
        
        .subtitle {
            color: #718096;
            margin-bottom: 30px;
            font-size: 16px;
        }
        
        .camera-container {
            position: relative;
            margin: 20px 0;
        }
        
        #video, #canvas {
            width: 100%;
            max-width: 500px;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }
        
        .hidden {
            display: none;
        }
        
        .btn {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin: 10px 5px;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(76, 175, 80, 0.3);
            min-width: 150px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(76, 175, 80, 0.4);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
            box-shadow: 0 5px 15px rgba(108, 117, 125, 0.3);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            box-shadow: 0 5px 15px rgba(220, 53, 69, 0.3);
        }
        
        .status {
            margin: 20px 0;
            padding: 15px;
            border-radius: 10px;
            font-weight: 500;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .status.warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        
        .instructions {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
            text-align: right;
        }
        
        .instructions h3 {
            color: #4a5568;
            margin-bottom: 15px;
        }
        
        .instructions ol {
            text-align: right;
            padding-right: 20px;
        }
        
        .instructions li {
            margin-bottom: 10px;
            line-height: 1.6;
        }
        
        @media (max-width: 768px) {
            .card {
                padding: 20px;
                margin: 10px;
            }
            
            .btn {
                padding: 12px 25px;
                font-size: 14px;
                min-width: 120px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>📸 كاميرا البوت</h1>
            <p class="subtitle">للمستخدم: {{user_id}}</p>
            
            <div class="instructions">
                <h3>🎯 كيفية الاستخدام:</h3>
                <ol>
                    <li>انقر على "تشغيل الكاميرا"</li>
                    <li>اسمح للموقع بالوصول إلى الكاميرا</li>
                    <li>انقر على "التقاط صورة" عندما تكون جاهزاً</li>
                    <li>انقر على "إرسال الصورة" لإرسالها للبوت</li>
                </ol>
            </div>
            
            <div id="permissionMessage" class="status warning">
                ⚠️ يرجى النقر على "تشغيل الكاميرا" والسماح بالوصول إلى الكاميرا
            </div>
            
            <div class="camera-container">
                <video id="video" autoplay playsinline class="hidden"></video>
                <canvas id="canvas" class="hidden"></canvas>
            </div>
            
            <div class="controls">
                <button class="btn" onclick="startCamera()" id="startBtn">🎥 تشغيل الكاميرا</button>
                <button class="btn" onclick="capturePhoto()" id="captureBtn" class="hidden">📷 التقاط صورة</button>
                <button class="btn btn-secondary" onclick="retakePhoto()" id="retakeBtn" class="hidden">🔄 إعادة الالتقاط</button>
                <button class="btn btn-danger" onclick="sendPhoto()" id="sendBtn" class="hidden">📤 إرسال الصورة</button>
            </div>
            
            <div id="status"></div>
        </div>
    </div>

    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const startBtn = document.getElementById('startBtn');
        const captureBtn = document.getElementById('captureBtn');
        const retakeBtn = document.getElementById('retakeBtn');
        const sendBtn = document.getElementById('sendBtn');
        const permissionMessage = document.getElementById('permissionMessage');
        const statusDiv = document.getElementById('status');
        
        let stream = null;
        let photoData = null;

        async function startCamera() {
            try {
                statusDiv.innerHTML = '<div class="status info">⏳ جاري تشغيل الكاميرا...</div>';
                
                stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        facingMode: 'environment',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    } 
                });
                
                video.srcObject = stream;
                video.classList.remove('hidden');
                startBtn.classList.add('hidden');
                captureBtn.classList.remove('hidden');
                permissionMessage.classList.add('hidden');
                
                statusDiv.innerHTML = '<div class="status success">✅ الكاميرا جاهزة - يمكنك التقاط الصورة الآن</div>';
                
            } catch (error) {
                console.error('Error accessing camera:', error);
                let errorMessage = '❌ فشل في الوصول إلى الكاميرا';
                
                if (error.name === 'NotAllowedError') {
                    errorMessage = '❌ تم رفض الإذن - يرجى السماح بالوصول إلى الكاميرا';
                } else if (error.name === 'NotFoundError') {
                    errorMessage = '❌ لم يتم العثور على كاميرا';
                } else if (error.name === 'NotSupportedError') {
                    errorMessage = '❤️ المتصفح لا يدعم الكاميرا';
                }
                
                statusDiv.innerHTML = `<div class="status error">${errorMessage}</div>`;
            }
        }

        function capturePhoto() {
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0);
            
            // إيقاف الكاميرا
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            
            photoData = canvas.toDataURL('image/jpeg', 0.8);
            canvas.classList.remove('hidden');
            video.classList.add('hidden');
            captureBtn.classList.add('hidden');
            retakeBtn.classList.remove('hidden');
            sendBtn.classList.remove('hidden');
            
            statusDiv.innerHTML = '<div class="status success">✅ تم التقاط الصورة بنجاح</div>';
        }

        function retakePhoto() {
            canvas.classList.add('hidden');
            retakeBtn.classList.add('hidden');
            sendBtn.classList.add('hidden');
            startBtn.classList.remove('hidden');
            photoData = null;
            permissionMessage.classList.remove('hidden');
            statusDiv.innerHTML = '<div class="status info">🔄 يمكنك إعادة تشغيل الكاميرا</div>';
        }

        async function sendPhoto() {
            if (!photoData) {
                statusDiv.innerHTML = '<div class="status error">❌ لا توجد صورة مرفوعة</div>';
                return;
            }

            statusDiv.innerHTML = '<div class="status info">⏳ جاري إرسال الصورة للبوت...</div>';
            sendBtn.disabled = true;

            try {
                // تحويل Base64 إلى Blob
                const response = await fetch(photoData);
                const blob = await response.blob();
                
                // إنشاء FormData وإرسال الصورة
                const formData = new FormData();
                formData.append('photo', blob, 'photo.jpg');
                formData.append('user_id', '{{user_id}}');

                const uploadResponse = await fetch('/upload_photo', {
                    method: 'POST',
                    body: formData
                });

                const result = await uploadResponse.json();
                
                if (result.success) {
                    statusDiv.innerHTML = '<div class="status success">✅ تم إرسال الصورة للبوت بنجاح!</div>';
                    sendBtn.classList.add('hidden');
                    retakeBtn.classList.add('hidden');
                    
                    setTimeout(() => {
                        statusDiv.innerHTML += '<div class="status info">🔄 يمكنك إغلاق هذه الصفحة الآن</div>';
                    }, 2000);
                } else {
                    statusDiv.innerHTML = `<div class="status error">❌ فشل في الإرسال: ${result.error}</div>`;
                    sendBtn.disabled = false;
                }

            } catch (error) {
                console.error('Upload error:', error);
                statusDiv.innerHTML = '<div class="status error">❌ خطأ في الاتصال - يرجى المحاولة مرة أخرى</div>';
                sendBtn.disabled = false;
            }
        }

        // إظهار رسالة ترحيب عند التحميل
        window.addEventListener('load', function() {
            statusDiv.innerHTML = '<div class="status info">👆 انقر على "تشغيل الكاميرا" لبدء الاستخدام</div>';
        });
    </script>
</body>
</html>
"""

# ========== مسارات Flask ==========
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <title>بوت الكاميرا</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center; 
                padding: 50px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255,255,255,0.1);
                padding: 30px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                max-width: 500px;
                margin: 0 auto;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 بوت التليجرام للكاميرا</h1>
            <p>البوت يعمل بشكل صحيح ✅</p>
            <p>استخدم /start في التليجرام للحصول على رابط الكاميرا الخاص بك</p>
        </div>
    </body>
    </html>
    """

@app.route('/camera/<user_id>')
def camera_page(user_id):
    """إنشاء صفحة الكاميرا للمستخدم"""
    return render_template_string(CAMERA_HTML, user_id=user_id)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    """استقبال الصور من صفحة الويب"""
    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No photo uploaded'})
        
        photo = request.files['photo']
        user_id = request.form.get('user_id')
        
        if photo and user_id:
            # حفظ الصورة
            filename = f"photo_{user_id}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join('photos', filename)
            photo.save(filepath)
            
            # إرسال إشعار للبوت (يمكن تطويره ليرسل الصورة فعلياً)
            print(f"📸 تم استقبال صورة من المستخدم {user_id}: {filename}")
            
            return jsonify({
                'success': True, 
                'message': 'تم استلام الصورة بنجاح',
                'filename': filename
            })
        else:
            return jsonify({'success': False, 'error': 'Missing user_id or photo'})
        
    except Exception as e:
        print(f"❌ خطأ في رفع الصورة: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ========== وظائف التليجرام ==========
class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.application = None
        self.webhook_url = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /start"""
        user = update.effective_user
        user_id = user.id
        
        # الحصول على رابط النشر الحالي
        if 'RENDER_EXTERNAL_URL' in os.environ:
            base_url = os.environ['RENDER_EXTERNAL_URL']
        else:
            base_url = f"https://{request.host}" if request else "https://your-app.onrender.com"
        
        camera_url = f"{base_url}/camera/{user_id}"
        
        welcome_text = f"""
        🎉 أهلاً بك {user.first_name}!

        📸 **رابط الكاميرا الخاص بك:**
        {camera_url}

        ⚡ **كيفية الاستخدام:**
        1. افتح الرابط أعلاه
        2. اسمح بالوصول إلى الكاميرا
        3. التقط صورة
        4. أرسلها للبوت

        🔒 **ملاحظة:** هذا الرابط خاص بك فقط ولا تشاركه مع الآخرين.

        ❓ للمساعدة استخدم /help
        """
        
        await update.message.reply_text(welcome_text)
        print(f"🔗 تم إنشاء رابط للمستخدم {user_id}: {camera_url}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /help"""
        help_text = """
        🤖 **أوامر البوت:**

        /start - بدء البوت والحصول على رابط الكاميرا
        /help - عرض الرسالة المساعدة

        📱 **كيفية الاستخدام:**
        1. استخدم /start للحصول على رابط الكاميرا
        2. افتح الرابط في متصفحك
        3. اسمح للوصول إلى الكاميرا
        4. التقط صورة وأرسلها

        🛠 **في حالة وجود مشاكل:**
        - تأكد من فتح الرابط في متصفح حديث
        - اسمح بالإذن لاستخدام الكاميرا
        - جرب متصفح مختلف إذا استمرت المشكلة
        """
        await update.message.reply_text(help_text)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأخطاء"""
        print(f"❌ خطأ في البوت: {context.error}")

    def setup_handlers(self):
        """إعداد معالجات الأوامر"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_error_handler(self.error_handler)

    def run_polling(self):
        """تشغيل البوت باستخدام Polling"""
        async def run():
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()
            
            print("🤖 بدء تشغيل بوت التليجرام...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # إبقاء البوت يعمل
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
    time.sleep(3)  # انتظار بسيط لضمان تشغيل الخادم أولاً
    
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ يرجى إضافة التوكن الصحيح للبوت")
        return
        
    bot = TelegramBot(BOT_TOKEN)
    bot.run_polling()

if __name__ == '__main__':
    print("🚀 بدء تشغيل التطبيق...")
    print(f"📊 البورت: {PORT}")
    print(f"🔑 التوكن: {'✅ مضبوط' if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else '❌ غير مضبوط'}")
    
    # تشغيل الخادم والبوت في خيوط منفصلة
    flask_thread = Thread(target=run_flask, daemon=True)
    bot_thread = Thread(target=run_bot, daemon=True)
    
    flask_thread.start()
    bot_thread.start()
    
    # إبقاء البرنامج الرئيسي يعمل
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("⏹ إيقاف التطبيق...")

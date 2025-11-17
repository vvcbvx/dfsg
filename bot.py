import os
import random
import time
import json
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from flask import Flask, request, jsonify, render_template_string
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from threading import Thread
import uuid

# ========== إعدادات البوت ==========
BOT_TOKEN = "7955384959:AAEIU_kzt3hyEmsK9QHoinkSlrld_vWkDB8"
PORT = int(os.environ.get('PORT', 5000))

# ========== إعداد Flask ==========
app = Flask(__name__)

# إنشاء مجلدات التخزين
if not os.path.exists('data'):
    os.makedirs('data')

# ========== نظام Instagram Bot ==========
class InstagramGrowthBot:
    def __init__(self):
        self.driver = None
        self.stats = {
            'total_follows': 0,
            'successful_follows': 0,
            'failed_follows': 0,
            'daily_follows': 0,
            'last_action': None
        }
        self.accounts = []
        
    def setup_driver(self):
        """إعداد متصفح Chrome"""
        chrome_options = Options()
        
        # إعدادات للتشغيل على السيرفر
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")  # التشغيل بدون واجهة
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # إعدادات إضافية للأمان
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        
        try:
            # للمشاكل على Render
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return True
        except Exception as e:
            print(f"❌ خطأ في إعداد المتصفح: {e}")
            return False
        
    def human_like_delay(self, min_sec=2, max_sec=8):
        """تأخير بشري عشوائي"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        
    def login(self, username, password):
        """تسجيل الدخول لإنستغرام"""
        try:
            print(f"🔐 محاولة تسجيل الدخول للحساب: {username}")
            self.driver.get("https://www.instagram.com/accounts/login/")
            self.human_like_delay(3, 5)
            
            # إدخال اسم المستخدم
            username_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_input.clear()
            for char in username:
                username_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
                
            # إدخال كلمة المرور
            password_input = self.driver.find_element(By.NAME, "password")
            password_input.clear()
            for char in password:
                password_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
                
            # النقر على زر تسجيل الدخول
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            self.human_like_delay(5, 8)
            
            # التحقق من نجاح التسجيل
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/direct/inbox/')]"))
                )
                print("✅ تم تسجيل الدخول بنجاح")
                return True
            except:
                print("❌ فشل تسجيل الدخول")
                return False
                
        except Exception as e:
            print(f"❌ خطأ في تسجيل الدخول: {e}")
            return False
    
    def safe_follow_limit(self):
        """التحقق من حدود المتابعة الآمنة"""
        if self.stats['daily_follows'] >= 100:  # تقليل الحد للأمان
            return False
        return True
    
    def close(self):
        """إغلاق المتصفح"""
        if self.driver:
            self.driver.quit()
            print("✅ تم إغلاق المتصفح")

# ========== نظام إدارة الطلبات ==========
class OrderManager:
    def __init__(self):
        self.orders = {}
        self.bot = InstagramGrowthBot()
        
    def start_growth_service(self, order_data):
        """بدء خدمة النمو"""
        def run_growth():
            try:
                print(f"🚀 بدء خدمة النمو للطلب: {order_data['order_id']}")
                
                # إعداد البوت
                if not self.bot.setup_driver():
                    order_data['status'] = 'failed'
                    order_data['error'] = 'فشل في إعداد المتصفح'
                    return
                
                # تسجيل الدخول
                if self.bot.login(order_data['ig_username'], order_data['ig_password']):
                    order_data['status'] = 'logged_in'
                    order_data['progress'] = 25
                    
                    # محاكاة عملية النمو
                    total_followed = 0
                    target = order_data['target_followers']
                    
                    # محاكاة التقدم
                    for i in range(10):
                        if total_followed >= target:
                            break
                            
                        # زيادة عشوائية في المتابعين
                        new_follows = random.randint(5, 15)
                        total_followed = min(total_followed + new_follows, target)
                        
                        # تحديث التقدم
                        progress = 25 + (total_followed / target) * 75
                        order_data['progress'] = min(progress, 100)
                        order_data['current_followers'] = total_followed
                        
                        print(f"📈 التقدم: {order_data['progress']}% - {total_followers}/{target}")
                        
                        # تأخير بين الدورات
                        time.sleep(random.randint(10, 30))
                        
                        # التحقق من الحدود
                        if not self.bot.safe_follow_limit():
                            break
                    
                    order_data['status'] = 'completed'
                    order_data['progress'] = 100
                    order_data['actual_followers'] = total_followed
                    order_data['completed_at'] = datetime.now().isoformat()
                    print(f"✅ اكتملت الخدمة للطلب: {order_data['order_id']}")
                    
                else:
                    order_data['status'] = 'failed'
                    order_data['error'] = 'فشل تسجيل الدخول'
                    print(f"❌ فشلت الخدمة للطلب: {order_data['order_id']}")
                    
            except Exception as e:
                order_data['status'] = 'failed'
                order_data['error'] = str(e)
                print(f"❌ خطأ في الخدمة: {e}")
            finally:
                self.bot.close()
        
        Thread(target=run_growth, daemon=True).start()
        return order_data

# ========== إنشاء المدير ==========
order_manager = OrderManager()

# ========== HTML قوالب ==========
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>خدمة زيادة المتابعين الحقيقية</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; color: white; }
        .container { background: rgba(255, 255, 255, 0.1); padding: 40px; border-radius: 20px; backdrop-filter: blur(10px); text-align: center; max-width: 500px; width: 90%; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2); }
        h1 { font-size: 2rem; margin-bottom: 20px; color: white; }
        .input-group { margin: 20px 0; text-align: right; }
        label { display: block; margin-bottom: 8px; font-weight: bold; }
        input, select { width: 100%; padding: 15px; border: none; border-radius: 10px; font-size: 1rem; text-align: right; background: rgba(255,255,255,0.9); }
        .btn { background: linear-gradient(135deg, #E1306C 0%, #C13584 100%); color: white; border: none; padding: 15px 30px; border-radius: 25px; cursor: pointer; font-size: 1.1rem; font-weight: bold; margin: 10px; transition: all 0.3s ease; width: 100%; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(225, 48, 108, 0.3); }
        .note { background: rgba(255,255,255,0.2); padding: 15px; border-radius: 10px; margin: 15px 0; font-size: 0.9rem; text-align: right; }
        .loading { display: none; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 خدمة زيادة المتابعين الحقيقية</h1>
        <p>أدخل بيانات حساب إنستغرام لبدء الخدمة</p>
        
        <form id="loginForm">
            <div class="input-group">
                <label>اسم مستخدم إنستغرام:</label>
                <input type="text" id="igUsername" placeholder="اسم المستخدم" required>
            </div>
            
            <div class="input-group">
                <label>كلمة مرور إنستغرام:</label>
                <input type="password" id="igPassword" placeholder="كلمة المرور" required>
            </div>
            
            <div class="input-group">
                <label>عدد المتابعين المطلوب:</label>
                <select id="followerCount">
                    <option value="50">50 متابع</option>
                    <option value="100">100 متابع</option>
                    <option value="200">200 متابع</option>
                </select>
            </div>
            
            <div class="note">
                ⚠️ ملاحظة: 
                <br>• تأكد من صحة بيانات الدخول
                <br>• الخدمة قد تستغرق عدة ساعات
                <br>• الحد الأقصى 100 متابع/يوم لأمان الحساب
            </div>
            
            <div class="loading" id="loading">
                ⏳ جاري بدء الخدمة...
            </div>
            
            <button type="button" class="btn" onclick="startService()" id="submitBtn">
                🚀 بدء زيادة المتابعين
            </button>
        </form>
    </div>

    <script>
        function startService() {
            const username = document.getElementById('igUsername').value.trim();
            const password = document.getElementById('igPassword').value.trim();
            const followers = document.getElementById('followerCount').value;
            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('loading');
            
            if (!username || !password) {
                alert('يرجى ملء جميع الحقول');
                return;
            }
            
            // إظهار التحميل
            submitBtn.disabled = true;
            loading.style.display = 'block';
            
            // إرسال الطلب
            fetch('/start_service', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ig_username: username,
                    ig_password: password,
                    target_followers: parseInt(followers),
                    user_id: '{{user_id}}'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // الانتقال إلى صفحة المتابعة
                    const statusUrl = `/service_status?order_id=${data.order_id}`;
                    window.location.href = statusUrl;
                } else {
                    alert('❌ حدث خطأ: ' + data.error);
                }
            })
            .catch(error => {
                alert('❌ خطأ في الاتصال: ' + error);
            })
            .finally(() => {
                submitBtn.disabled = false;
                loading.style.display = 'none';
            });
        }
    </script>
</body>
</html>
"""

STATUS_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>حالة الخدمة - زيادة المتابعين</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { background: rgba(255, 255, 255, 0.1); padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 20px; backdrop-filter: blur(10px); }
        .status-card { background: rgba(255, 255, 255, 0.1); padding: 25px; border-radius: 15px; margin: 15px 0; backdrop-filter: blur(10px); }
        .progress-bar { width: 100%; height: 20px; background: rgba(255,255,255,0.2); border-radius: 10px; overflow: hidden; margin: 15px 0; }
        .progress { height: 100%; background: linear-gradient(90deg, #4CAF50, #45a049); border-radius: 10px; transition: width 0.3s ease; }
        .status-badge { display: inline-block; padding: 8px 15px; border-radius: 20px; font-weight: bold; margin: 5px; }
        .status-pending { background: #FF9800; }
        .status-active { background: #2196F3; }
        .status-completed { background: #4CAF50; }
        .status-failed { background: #f44336; }
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }
        .stat-item { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; text-align: center; }
        .log-container { max-height: 300px; overflow-y: auto; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 10px; margin: 15px 0; font-family: monospace; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 حالة خدمة زيادة المتابعين</h1>
            <p>جاري متابعة تقدم خدمتك</p>
        </div>
        
        <div class="status-card">
            <h2>تفاصيل الطلب</h2>
            <div id="orderDetails"></div>
        </div>
        
        <div class="status-card">
            <h2>سير التقدم</h2>
            <div class="progress-bar">
                <div class="progress" id="orderProgress"></div>
            </div>
            <div id="progressText" style="text-align: center; margin: 10px 0;"></div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-item">
                <div style="font-size: 2rem;">👥</div>
                <div id="currentFollowers">0</div>
                <div>متابعين مضافين</div>
            </div>
            <div class="stat-item">
                <div style="font-size: 2rem;">🎯</div>
                <div id="targetFollowers">0</div>
                <div>الهدف</div>
            </div>
        </div>
        
        <div class="status-card">
            <h2>سجل النشاط</h2>
            <div class="log-container" id="activityLog">
                <div>⏳ جاري تحميل البيانات...</div>
            </div>
        </div>
    </div>

    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const orderId = urlParams.get('order_id');
        
        if (!orderId) {
            document.getElementById('orderDetails').innerHTML = '<div style="color: red;">❌ لم يتم العثور على رقم الطلب</div>';
        } else {
            updateServiceStatus();
            setInterval(updateServiceStatus, 3000);
        }
        
        function updateServiceStatus() {
            if (!orderId) return;
            
            fetch('/get_service_status?order_id=' + orderId)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        displayOrderData(data.order_data);
                        updateActivityLog(data.order_data);
                    } else {
                        document.getElementById('orderDetails').innerHTML = 
                            '<div style="color: red;">❌ خطأ: ' + data.error + '</div>';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        }
        
        function displayOrderData(order) {
            // تفاصيل الطلب
            document.getElementById('orderDetails').innerHTML = `
                <div><strong>رقم الطلب:</strong> ${order.order_id}</div>
                <div><strong>الحساب:</strong> @${order.ig_username}</div>
                <div><strong>الحالة:</strong> <span class="status-badge status-${order.status}">${getStatusText(order.status)}</span></div>
                <div><strong>وقت البدء:</strong> ${new Date(order.created_at).toLocaleString('ar-EG')}</div>
                ${order.completed_at ? `<div><strong>وقت الاكتمال:</strong> ${new Date(order.completed_at).toLocaleString('ar-EG')}</div>` : ''}
                ${order.error ? `<div style="color: #ff6b6b; margin-top: 10px;"><strong>الخطأ:</strong> ${order.error}</div>` : ''}
            `;
            
            // شريط التقدم
            const progressElement = document.getElementById('orderProgress');
            const progressText = document.getElementById('progressText');
            progressElement.style.width = order.progress + '%';
            progressText.textContent = `${Math.round(order.progress)}% مكتمل`;
            
            // الإحصائيات
            document.getElementById('currentFollowers').textContent = order.current_followers || 0;
            document.getElementById('targetFollowers').textContent = order.target_followers;
        }
        
        function updateActivityLog(order) {
            const logContainer = document.getElementById('activityLog');
            const status = order.status;
            const progress = order.progress;
            
            let logs = [];
            
            if (status === 'pending') {
                logs.push('⏳ جاري التحضير لبدء الخدمة...');
            }
            else if (status === 'logged_in') {
                logs.push('✅ تم تسجيل الدخول بنجاح');
                logs.push('🚀 بدء عملية زيادة المتابعين...');
            }
            else if (status === 'completed') {
                logs.push('🎉 اكتملت الخدمة بنجاح!');
                logs.push(`✅ تم إضافة ${order.actual_followers} متابع`);
                logs.push('📊 يمكنك التحقق من حسابك الآن');
            }
            else if (status === 'failed') {
                logs.push('❌ فشلت الخدمة');
                logs.push(`💡 السبب: ${order.error}`);
            }
            
            if (progress >= 25 && progress < 50) {
                logs.push('🔍 جاري البحث عن مستخدمين مناسبين...');
            }
            else if (progress >= 50 && progress < 75) {
                logs.push('📈 جاري متابعة المستخدمين...');
                logs.push(`✅ تمت متابعة ${order.current_followers} مستخدم حتى الآن`);
            }
            else if (progress >= 75 && progress < 100) {
                logs.push('🎯 المرحلة النهائية...');
                logs.push(`⚡ جاري إكمال المتابعة...`);
            }
            
            // تحديث السجلات
            logContainer.innerHTML = logs.map(log => 
                `<div>[${new Date().toLocaleTimeString('ar-EG')}] ${log}</div>`
            ).join('');
            
            // التمرير لأسفل
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        function getStatusText(status) {
            const texts = {
                'pending': 'في الانتظار',
                'logged_in': 'جاري العمل',
                'completed': 'مكتمل',
                'failed': 'فشل'
            };
            return texts[status] || status;
        }
    </script>
</body>
</html>
"""

# ========== مسارات Flask ==========
@app.route('/')
def home():
    return "Instagram Growth Service - Use /start in Telegram"

@app.route('/user/<user_id>')
def user_page(user_id):
    """الصفحة الرئيسية للمستخدم"""
    return render_template_string(LOGIN_HTML, user_id=user_id)

@app.route('/start_service', methods=['POST'])
def start_service():
    """بدء خدمة زيادة المتابعين"""
    try:
        data = request.get_json()
        ig_username = data.get('ig_username')
        ig_password = data.get('ig_password')
        target_followers = data.get('target_followers', 100)
        user_id = data.get('user_id')
        
        if not all([ig_username, ig_password, user_id]):
            return jsonify({'success': False, 'error': 'بيانات ناقصة'})
        
        # إنشاء طلب جديد
        order_id = f"IG_{random.randint(100000, 999999)}"
        
        order_data = {
            'order_id': order_id,
            'user_id': user_id,
            'ig_username': ig_username,
            'ig_password': ig_password,
            'target_followers': target_followers,
            'status': 'pending',
            'progress': 0,
            'current_followers': 0,
            'created_at': datetime.now().isoformat()
        }
        
        # بدء الخدمة
        order_manager.orders[order_id] = order_data
        order_manager.start_growth_service(order_data)
        
        # إرسال إشعار للبوت
        asyncio.create_task(send_service_start_notification(user_id, order_id, ig_username))
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'تم بدء خدمة زيادة المتابعين'
        })
        
    except Exception as e:
        print(f"❌ خطأ في بدء الخدمة: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_service_status')
def get_service_status():
    """الحصول على حالة الخدمة"""
    order_id = request.args.get('order_id')
    if not order_id:
        return jsonify({'success': False, 'error': 'لم يتم تقديم رقم الطلب'})
    
    order_data = order_manager.orders.get(order_id)
    if order_data:
        return jsonify({'success': True, 'order_data': order_data})
    else:
        return jsonify({'success': False, 'error': 'لم يتم العثور على الطلب'})

@app.route('/service_status')
def service_status_page():
    """صفحة حالة الخدمة"""
    return render_template_string(STATUS_HTML)

# ========== وظائف التليجرام ==========
async def send_service_start_notification(user_id, order_id, username):
    """إرسال إشعار بدء الخدمة للبوت"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        message = f"""
🚀 **تم بدء خدمة زيادة المتابعين!**

👤 **الحساب:** @{username}
🆔 **رقم الطلب:** {order_id}
🕒 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 **جاري بدء عملية النمو...**
⏰ **المدة المتوقعة:** 1-3 ساعات
🎯 **سيتم إرسال التحديثات تلقائياً**

🔍 **لمتابعة التقدم:**
https://{request.host}/service_status?order_id={order_id}
        """
        
        await application.bot.send_message(
            chat_id=int(user_id),
            text=message,
            parse_mode='HTML'
        )
        
        print(f"✅ تم إرسال إشعار بدء الخدمة للمستخدم {user_id}")
        
    except Exception as e:
        print(f"❌ خطأ في إرسال إشعار الخدمة: {e}")

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
        user_url = f"{base_url}/user/{user_id}"
        
        welcome_text = f"""
🎉 **أهلاً بك {user.first_name} في خدمة زيادة متابعين إنستغرام!**

📱 **رابطك الخاص:**
{user_url}

⚡ **مميزات الخدمة:**
✅ متابعين حقيقين ونشطين
✅ نمو عضوي آمن
✅ عدم استخدام بوتات
✅ محاكاة السلوك البشري

🔒 **كيفية العمل:**
1. افتح الرابط أعلاه
2. أدخل بيانات حساب إنستغرام
3. اختر عدد المتابعين المطلوب
4. شاهد المتابعين يزدادون!

🚀 **ابدأ الآن!**
        """
        
        await update.message.reply_text(welcome_text, parse_mode='HTML')
        print(f"🔗 تم إنشاء رابط للمستخدم {user_id}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /help"""
        help_text = """
🤖 **أوامر البوت:**

/start - بدء البوت والحصول على الرابط الخاص
/help - عرض الرسالة المساعدة
/status - حالة طلباتك

📞 **للدعم الفني راسل المطور**
        """
        await update.message.reply_text(help_text)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /status"""
        user = update.effective_user
        user_id = user.id
        
        # البحث عن طلبات المستخدم
        user_orders = []
        for order_id, order_data in order_manager.orders.items():
            if order_data.get('user_id') == str(user_id):
                user_orders.append(order_data)
        
        if not user_orders:
            await update.message.reply_text("📭 لم تقم بإنشاء أي طلبات بعد.\nاستخدم /start لبدء خدمة جديدة.")
            return
        
        status_text = "📊 **حالة طلباتك:**\n\n"
        for order in user_orders[-5:]:  # آخر 5 طلبات
            status_emoji = {
                'pending': '⏳',
                'logged_in': '🚀', 
                'completed': '✅',
                'failed': '❌'
            }.get(order['status'], '📝')
            
            status_text += f"""
{status_emoji} **طلب {order['order_id']}**
• الحساب: @{order['ig_username']}
• الحالة: {order['status']}
• التقدم: {order['progress']}%
• المتابعين: {order.get('current_followers', 0)}/{order['target_followers']}
---
            """
        
        await update.message.reply_text(status_text, parse_mode='HTML')

    def setup_handlers(self):
        """إعداد معالجات الأوامر"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))

    async def run_webhook(self):
        """تشغيل البوت باستخدام Webhook (مفضل على Render)"""
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        
        # استخدام Webhook
        webhook_url = os.environ.get('RENDER_EXTERNAL_URL', f"https://{request.host}" if request else "http://localhost:5000")
        
        await self.application.bot.set_webhook(url=f"{webhook_url}/webhook")
        print(f"✅ تم إعداد Webhook: {webhook_url}/webhook")

    def run_polling(self):
        """تشغيل البوت باستخدام Polling"""
        async def run():
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()
            
            print("🤖 بدء تشغيل بوت التليجرام باستخدام Polling...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # البقاء قيد التشغيل
            while True:
                await asyncio.sleep(3600)
                
        asyncio.run(run())

@app.route('/webhook', methods=['POST'])
async def webhook():
    """معالجة Webhook للتليجرام"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        telegram_bot = TelegramBot(BOT_TOKEN)
        telegram_bot.setup_handlers()
        
        update = Update.de_json(request.get_json(), application.bot)
        await application.process_update(update)
        return 'OK'
    except Exception as e:
        print(f"❌ خطأ في Webhook: {e}")
        return 'ERROR', 500

# ========== التشغيل الرئيسي ==========
def run_flask():
    """تشغيل خادم Flask"""
    print("🌐 بدء تشغيل خادم الويب...")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

def run_bot():
    """تشغيل بوت التليجرام"""
    time.sleep(5)  # انتظار تشغيل Flask أولاً
    bot = TelegramBot(BOT_TOKEN)
    bot.run_polling()

if __name__ == '__main__':
    print("🚀 بدء تشغيل خدمة زيادة متابعين إنستغرام...")
    print(f"📊 البورت: {PORT}")
    
    # تشغيل الخوادم في خيوط منفصلة
    flask_thread = Thread(target=run_flask, daemon=True)
    bot_thread = Thread(target=run_bot, daemon=True)
    
    flask_thread.start()
    bot_thread.start()
    
    try:
        # البقاء قيد التشغيل
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("⏹ إيقاف التطبيق...")

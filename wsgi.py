
# wsgi.py
import os
import logging
from bot import app

if __name__ == "__main__":
    # هذا الملف مخصص لـ Render فقط
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

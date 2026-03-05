from .settings import *

# ===== SÉCURITÉ =====
DEBUG = False
SECRET_KEY = 'mZ#8kQpX2$vL9nR4@wT7yJ1iO6uA3sD5fG0hC'

ALLOWED_HOSTS = ['rh.mesrs.app', 'www.rh.mesrs.app', '185.221.182.17']

# ===== BASE DE DONNÉES MySQL n0c =====
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'fczwktewxc_GRH',
        'USER': 'fczwktewxc_GRH',
        'PASSWORD': 'gha6cyRuTHe5JmXNb1YsGDK3.',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ===== CORS =====
CORS_ALLOWED_ORIGINS = [
    "https://rh.mesrs.app",
    "https://www.rh.mesrs.app",
]

# ===== STATIC & MEDIA =====
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'

# ===== SÉCURITÉ HTTPS =====
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
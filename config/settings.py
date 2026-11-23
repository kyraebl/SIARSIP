import os
from datetime import timedelta
from pathlib import Path

from decouple import config
import dj_database_url
from pathlib import Path
from django.templatetags.static import static
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MAX_UPLOAD_MB = 10

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=60,
        conn_health_checks=True,
    )
}
DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
DATABASES['default'].setdefault('OPTIONS', {})
DATABASES['default']['OPTIONS']['connect_timeout'] = 30

ALLOWED_HOSTS = ['10.103.34.89', 'siarsip.web.id', '.vercel.app', 'localhost', '127.0.0.1']

CSRF_TRUSTED_ORIGINS = [
    'http://10.103.34.89:8000',
    'http://siarsip.dsdan',
    'https://*.vercel.app',
]

# App Definistions
INSTALLED_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'axes',
    'accounts',
    'master',
    'arsip',
]

AUTH_USER_MODEL = "accounts.User"

# Hash password: Argon2 (kuat terhadap brute force GPU). Hash lama (PBKDF2) tetap bisa dipakai
# login dan otomatis di-upgrade ke Argon2 begitu pemiliknya berhasil login.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

# django-axes: kunci login setelah gagal berulang (anti tebak password)
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AXES_FAILURE_LIMIT = 5                       # gagal 5x -> dikunci
AXES_COOLOFF_TIME = timedelta(minutes=15)    # kunci otomatis lepas setelah 15 menit
AXES_LOCKOUT_PARAMETERS = ["username"]       # per akun (IP di balik proxy tidak bisa dipercaya)
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "lockout.html"
SILENCED_SYSTEM_CHECKS = ["axes.W006"]      # sengaja kunci per username, bukan per IP

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# Keamanan sesi login
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 900
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_NAME = "siarsip_csrftoken"
SESSION_COOKIE_NAME = "siarsip_sessionid"

# Header keamanan
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

USE_X_FORWARDED_HOST = True

USE_HTTPS = config("USE_HTTPS", default=False, cast=bool)

if USE_HTTPS:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

USE_I18N = True

USE_TZ = True

# File statis: sumber di static/, hasil collectstatic di staticfiles/
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
WHITENOISE_USE_FINDERS = True

USE_GDRIVE = config("USE_GDRIVE", default=False, cast=bool)
GDRIVE_CLIENT_ID = config("GDRIVE_CLIENT_ID", default="")
GDRIVE_CLIENT_SECRET = config("GDRIVE_CLIENT_SECRET", default="")
GDRIVE_REFRESH_TOKEN = config("GDRIVE_REFRESH_TOKEN", default="")
GDRIVE_FOLDER_ID = config("GDRIVE_FOLDER_ID", default="")
GDRIVE_BUKA_DI_DRIVE = config("GDRIVE_BUKA_DI_DRIVE", default=False, cast=bool)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}


UNFOLD = {
    "SITE_TITLE": "SIARSIP Admin",
    "SITE_HEADER": "SIARSIP",
    "SITE_SUBHEADER": "Kelola Sistem",
    "SITE_SYMBOL": "folder_open",
    "SITE_ICON": lambda request: static("logo-icon.png"),
    "SITE_FAVICONS": [
        {"rel": "icon", "sizes": "64x64", "type": "image/png", "href": lambda request: static("favicon.png")},
    ],
    "SITE_URL": None,
    "THEME": "light",
    "STYLES": [lambda request: static("admin-siarsip.css")],
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "home",
                        "link": reverse_lazy("admin:arsip_arsip_dashboard"),
                        "active": lambda request: request.path == str(reverse_lazy("admin:arsip_arsip_dashboard")),
                    },
                    {
                        "title": "Daftar Arsip Aktif",
                        "icon": "description",
                        "link": reverse_lazy("admin:arsip_arsip_changelist"),
                        "active": lambda request: (
                            request.path.startswith(str(reverse_lazy("admin:arsip_arsip_changelist")))
                            and request.path != str(reverse_lazy("admin:arsip_arsip_dashboard"))
                        ),
                    },
                    {
                        "title": "Daftar Arsip Inaktif",
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:arsip_arsipinaktif_changelist"),
                    },
                    {
                        "title": "Website",
                        "icon": "language",
                        "link": reverse_lazy("dashboard"),
                        "active": lambda request: False,
                    },
                ],
            },
            {
                "title": "Pengaturan",
                "collapsible": True,
                "items": [
                    {"title": "Pengguna", "icon": "group", "link": reverse_lazy("admin:accounts_user_changelist")},
                    {"title": "Unit kerja", "icon": "apartment", "link": reverse_lazy("admin:accounts_unitkerja_changelist")},
                    {"title": "Kategori klasifikasi", "icon": "category", "link": reverse_lazy("admin:master_kategori_changelist")},
                    {"title": "Pejabat penandatanganan", "icon": "draw", "link": reverse_lazy("admin:master_kodetujuan_changelist")},
                    {"title": "Pengesah", "icon": "verified", "link": reverse_lazy("admin:master_pengesah_changelist")},
                ],
            },
        ],
    },
    "COLORS": {
        "base": {
            "50": "#f8fafc", "100": "#f1f5f9", "200": "#e2e8f0", "300": "#cbd5e1", "400": "#94a3b8",
            "500": "#64748b", "600": "#475569", "700": "#334155", "800": "#1e293b", "900": "#0f172a",
            "950": "#020617",
        },
        "primary": {
            "50": "#EEF4FA", "100": "#DCE8F4", "200": "#B9D1E8", "300": "#8DB4D8", "400": "#5B92C4",
            "500": "#3B7AB5", "600": "#2A55A8", "700": "#234A9A", "800": "#1D3E84", "900": "#183670",
            "950": "#122A58",
        },
    },
}
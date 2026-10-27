import os
import dj_database_url

from decouple import config
import dj_database_url
from pathlib import Path
from django.templatetags.static import static
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600
    )
}

ALLOWED_HOSTS = ['siarsip.web.id', '.vercel.app', 'localhost', '127.0.0.1']

# App Definistions
INSTALLED_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'master',
    'arsip',
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
SESSION_COOKIE_AGE = 60 * 20
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000

USE_I18N = True

USE_TZ = True

# File statis: sumber di static/, hasil collectstatic di staticfiles/
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Penyimpanan berkas arsip (harus didefinisikan SEBELUM STORAGES)
MEDIA_ROOT = BASE_DIR / "private_media"
MAX_UPLOAD_MB = 10

USE_GDRIVE = config("USE_GDRIVE", default=False, cast=bool)
GDRIVE_CLIENT_ID = config("GDRIVE_CLIENT_ID", default="")
GDRIVE_CLIENT_SECRET = config("GDRIVE_CLIENT_SECRET", default="")
GDRIVE_REFRESH_TOKEN = config("GDRIVE_REFRESH_TOKEN", default="")
GDRIVE_FOLDER_ID = config("GDRIVE_FOLDER_ID", default="")
GDRIVE_BUKA_DI_DRIVE = config("GDRIVE_BUKA_DI_DRIVE", default=False, cast=bool)

STORAGES = {
    "default": {
        "BACKEND": "arsip.storage.GoogleDriveStorage" if USE_GDRIVE
                   else "django.core.files.storage.FileSystemStorage",
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
    "SITE_URL": "/",
    "THEME": "light",
    "STYLES": [lambda request: static("admin-siarsip.css")],
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "items": [
                    {"title": "Pengguna", "link": reverse_lazy("admin:accounts_user_changelist")},
                    {"title": "Unit kerja", "link": reverse_lazy("admin:accounts_unitkerja_changelist")},
                    {
                        "title": "Dashboard",
                        "link": reverse_lazy("admin:arsip_arsip_dashboard"),
                        "active": lambda request: request.path == str(reverse_lazy("admin:arsip_arsip_dashboard")),
                    },
                    {
                        "title": "Arsip",
                        "link": reverse_lazy("admin:arsip_arsip_changelist"),
                        "active": lambda request: (
                            request.path.startswith(str(reverse_lazy("admin:arsip_arsip_changelist")))
                            and request.path != str(reverse_lazy("admin:arsip_arsip_dashboard"))
                        ),
                    },
                    {"title": "Kategori klasifikasi", "link": reverse_lazy("admin:master_kategori_changelist")},
                    {"title": "Pejabat penandatanganan", "link": reverse_lazy("admin:master_kodetujuan_changelist")},
                    {"title": "Pengesah", "link": reverse_lazy("admin:master_pengesah_changelist")},
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
from decouple import config
import dj_database_url
from pathlib import Path
from django.templatetags.static import static

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)

DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL"),
        conn_max_age=60,
        conn_health_checks=True,
    )
}

ALLOWED_HOSTS = []

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

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}

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
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
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
    "COLORS": {
        "primary": {
            "50": "oklch(97% .014 254.604)",
            "100": "oklch(93.2% .032 255.585)",
            "200": "oklch(88.2% .059 254.128)",
            "300": "oklch(80.9% .105 251.813)",
            "400": "oklch(70.7% .165 254.624)",
            "500": "oklch(62.3% .214 259.815)",
            "600": "oklch(54.6% .245 262.881)",
            "700": "oklch(48.8% .243 264.376)",
            "800": "oklch(42.4% .199 265.638)",
            "900": "oklch(37.9% .146 265.522)",
            "950": "oklch(28.2% .091 267.935)",
        },
    },
}
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Load environment variables from a .env file if present (useful for local dev)
load_dotenv()


def env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-placeholder-key'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

# Dynamically discover and load modules from the 'apps' directory
# ----------------------------------------------------------------
import json

DYNAMIC_APPS = []
APPS_DIR = BASE_DIR / 'apps'

if APPS_DIR.is_dir():
    for app_dir in APPS_DIR.iterdir():
        if app_dir.is_dir():
            module_json_path = app_dir / 'module.json'
            if module_json_path.exists():
                try:
                    with open(module_json_path) as f:
                        module_data = json.load(f)
                        entry_point = module_data.get('entryPoint')
                        if entry_point:
                            DYNAMIC_APPS.append(entry_point)
                except (json.JSONDecodeError, IOError) as e:
                    # Handle potential errors in reading or parsing the json file
                    print(f"Warning: Could not load module from {app_dir.name}. Error: {e}")

# Base and third-party apps
THIRD_PARTY_APPS = [
    'shared',  # Shared app for common utilities (placed early to override commands like runserver)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'rest_framework_simplejwt',

]

# Combine third-party apps with dynamically discovered modules
INSTALLED_APPS = THIRD_PARTY_APPS # + DYNAMIC_APPS

# Statically defined apps that are not part of the dynamic module system (if any)
# For full modularity, aim to move all 'apps.*' into the dynamic loading system.
# For now, we will keep the remaining apps static to ensure stability during transition.
STATIC_APPS = [
    'apps.users',
    'apps.companies',
    'apps.data_migration',
    'apps.finance',
    'apps.sales',
    'apps.permissions',
    'apps.inventory',
    'apps.analytics',
    'apps.dashboard',
    'apps.form_builder',
    'apps.ai_companion',
    'apps.workflows',
    'apps.assets',
    'apps.budgeting',
    'apps.hr',
    'apps.production',
    'apps.projects',
    'apps.procurement',
    'apps.quality',
    'apps.metadata',
    'apps.audit',
]

INSTALLED_APPS += STATIC_APPS


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'shared.middleware.company_context.CompanyContextMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

USE_SQLITE = env_bool('USE_SQLITE', 'false')
if USE_SQLITE:
    default_sqlite_path = os.getenv('SQLITE_DB_PATH') or str((BASE_DIR / 'db.sqlite3').resolve())
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': default_sqlite_path,
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config(
            default='postgresql://postgres:dev_password@localhost:54322/twist_erp_db'
        )
    }
if 'data_warehouse' not in DATABASES:
    warehouse_config = DATABASES['default'].copy()
    if USE_SQLITE:
        base_sqlite_path = warehouse_config.get('NAME') or (BASE_DIR / 'db.sqlite3')
        base_sqlite_path = str(base_sqlite_path)
        if base_sqlite_path.endswith('.sqlite3'):
            warehouse_config['NAME'] = base_sqlite_path.replace('.sqlite3', '_warehouse.sqlite3')
        else:
            warehouse_config['NAME'] = f"{base_sqlite_path}_warehouse"
    DATABASES['data_warehouse'] = warehouse_config

DATABASE_ROUTERS = [
    'shared.db_routers.SystemDatabaseRouter',
    'shared.db_routers.CompanyGroupDatabaseRouter',
]

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

# Redis settings
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 0))

CORS_ALLOW_ALL_ORIGINS = True

# Celery Configuration
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_ROUTES = {
    'apps.data_migration.tasks.migration_tasks.*': {'queue': 'data_migration'},
}

# File Upload Settings
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
MAX_UPLOAD_SIZE = 104857600  # 100MB

# AI Configuration
AI_CONFIG = {
    'ENABLED': env_bool('AI_ENABLED', 'true'),
    'AUTOLOAD': env_bool('AI_AUTOLOAD', 'false'),
    'MODE': os.getenv('AI_MODE', 'mock'),
    'MAX_NEW_TOKENS': env_int('AI_MAX_NEW_TOKENS', 256),
    'MAX_PROMPT_TOKENS': env_int('AI_MAX_PROMPT_TOKENS', 768),
    'LLM_MODEL': os.getenv('AI_LLM_MODEL', 'mistralai/Mistral-7B-Instruct-v0.1'),
    'EMBEDDING_MODEL': os.getenv('AI_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
    'VECTOR_DB_PATH': os.getenv('AI_VECTOR_DB_PATH', './chroma_db'),
    'RASA_SERVER': os.getenv('AI_RASA_SERVER', 'http://localhost:5005'),
}

# Celery Beat Schedule (for periodic tasks)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'run-anomaly-detection': {
        'task': 'apps.ai_companion.tasks.detect_anomalies',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    },
    'calculate-depreciation': {
        'task': 'apps.assets.tasks.calculate_monthly_depreciation',
        'schedule': crontab(day_of_month=1, hour=2),  # Monthly
    },
    'process-payroll-reminders': {
        'task': 'apps.hr.tasks.send_payroll_reminders',
        'schedule': crontab(day_of_month=25, hour=9),  # 25th of month
    },
    'populate-data-warehouse': {
        'task': 'apps.analytics.tasks.populate_data_warehouse',
        'schedule': crontab(hour=2, minute=30),  # Daily 02:30 AM
    },
    'ai-generate-proactive-suggestions': {
        'task': 'apps.ai_companion.tasks.generate_proactive_suggestions',
        'schedule': crontab(minute='*/30'),  # every 30 minutes
    },
    'ai-monitor-workflow-bottlenecks': {
        'task': 'apps.ai_companion.tasks.monitor_workflow_bottlenecks',
        'schedule': crontab(minute='*/30'),  # every 30 minutes
    },
    'ai-monitor-budget-health': {
        'task': 'apps.ai_companion.tasks.monitor_budget_health',
        'schedule': crontab(minute=15, hour='*'),  # hourly at :15
    },
}

# File upload limits
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600

# DRF & Schema
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

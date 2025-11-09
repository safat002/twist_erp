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

def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
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

INSTALLED_APPS = [
    'jazzmin',
    'shared',  # Shared app for common utilities (placed early to override commands like runserver)
    'apps.companies',
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
# INSTALLED_APPS = THIRD_PARTY_APPS # + DYNAMIC_APPS

# Statically defined apps that are not part of the dynamic module system (if any)
# For full modularity, aim to move all 'apps.*' into the dynamic loading system.
# For now, we will keep the remaining apps static to ensure stability during transition.
STATIC_APPS = [
    'apps.users',
    'apps.data_migration',
    'apps.finance',
    'apps.sales',
    'apps.permissions.apps.PermissionsConfig',
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
    'apps.security',
    'apps.audit',
    'apps.report_builder',
    'apps.tasks',
    'apps.notifications',
    'apps.policies',
    'apps.ngo',
    'apps.microfinance',
    'apps.admin_settings',  # Feature toggle system
]

INSTALLED_APPS += STATIC_APPS

JAZZMIN_SETTINGS = {
    # title of the window (Will default to current_admin_site.site_title if absent or None)
    "site_title": "Twist ERP Admin",

    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_header": "Twist ERP",

    # Brand & logos
    "site_brand": None,
    "site_logo": "brand/twist-logo.svg",
    "login_logo": "brand/twist-logo.svg",
    "login_logo_dark": "brand/twist-logo-white.svg",
    "site_logo_classes": "img-circle",

    # Welcome text on the login screen
    "welcome_sign": "Welcome to Twist ERP Administration",

    # Copyright on the footer
    "copyright": "Twist ERP Ltd © 2025",

    # The model admin to search from the search bar
    "search_model": ["users.User", "companies.Company", "sales.Customer"],

    # Field name on user model that contains name of the user for the admin panel
    "user_avatar": None,

    ############
    # Top Menu #
    ############

    # Links to put along the top menu
    "topmenu_links": [
        {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "View Site", "url": "/", "new_window": True},
        {"model": "users.User"},
    ],

    #############
    # User Menu #
    #############

    # Additional links to include in the user menu on the top right
    "usermenu_links": [
        {"model": "users.User"},
    ],

    #############
    # Side Menu #
    #############

    # Whether to display the side menu
    "show_sidebar": True,

    # Whether to aut expand the menu
    "navigation_expanded": False,

    # Hide these apps when generating side menu
    "hide_apps": [],

    # Hide these models when generating side menu (e.g. auth.user)
    "hide_models": [],

    # List of apps (and/or models) to base side menu ordering off of (does not need to contain all apps/models)
    "order_with_respect_to": [
        "companies",
        "security",
        "users",
        "finance",
        "inventory",
        "sales",
        "procurement",
        "production",
        "assets",
        "budgeting",
        "hr",
        "projects",
        "ai_companion",
        "workflows",
        "form_builder",
    ],

    # Custom icons for side menu apps/models
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.Group": "fas fa-users",
        "users.user": "fas fa-user",
        "companies": "fas fa-building",
        "companies.company": "fas fa-building",
        "companies.companygroup": "fas fa-layer-group",
        "finance": "fas fa-dollar-sign",
        "finance.account": "fas fa-wallet",
        "finance.journalvoucher": "fas fa-file-invoice",
        "finance.invoice": "fas fa-file-invoice-dollar",
        "finance.payment": "fas fa-money-bill-wave",
        "inventory": "fas fa-warehouse",
        "inventory.product": "fas fa-box-open",
        "inventory.unitofmeasure": "fas fa-balance-scale",
        "budgeting.budgetunitofmeasure": "fas fa-balance-scale",
        "inventory.warehouse": "fas fa-warehouse",
        "inventory.stockmovement": "fas fa-exchange-alt",
        "sales": "fas fa-chart-line",
        "sales.customer": "fas fa-user-tie",
        "sales.salesorder": "fas fa-shopping-cart",
        "sales.quote": "fas fa-file-contract",
        "procurement": "fas fa-truck",
        "procurement.supplier": "fas fa-shipping-fast",
        "procurement.purchaseorder": "fas fa-file-invoice",
        "assets": "fas fa-toolbox",
        "assets.asset": "fas fa-wrench",
        "budgeting": "fas fa-calculator",
        "budgeting.budget": "fas fa-piggy-bank",
        "budgeting.budgetline": "fas fa-coins",
        "production": "fas fa-industry",
        "production.bom": "fas fa-clipboard-list",
        "production.workorder": "fas fa-cogs",
        "hr": "fas fa-user-friends",
        "hr.employee": "fas fa-id-badge",
        "hr.leaverequest": "fas fa-calendar-times",
        "hr.payrollrun": "fas fa-file-invoice-dollar",
        "projects": "fas fa-project-diagram",
        "projects.project": "fas fa-folder-open",
        "projects.task": "fas fa-tasks",
        "ai_companion": "fas fa-robot",
        "ai_companion.aitrainingexample": "fas fa-brain",
        "ai_companion.conversation": "fas fa-comments",
        "security": "fas fa-shield-alt",
        "security.secpermission": "fas fa-key",
        "security.secrole": "fas fa-user-tag",
        "security.secuserrole": "fas fa-user-shield",
        "workflows": "fas fa-sitemap",
        "form_builder": "fas fa-wpforms",
        "data_migration": "fas fa-database",
        "analytics": "fas fa-chart-pie",
        "dashboard": "fas fa-tachometer-alt",
        "report_builder": "fas fa-chart-bar",
        "audit": "fas fa-history",
        "tasks": "fas fa-check-square",
        "notifications": "fas fa-bell",
        "policies": "fas fa-file-contract",
        "ngo": "fas fa-hands-helping",
        "microfinance": "fas fa-university",
        "admin_settings": "fas fa-cog",
    },

    # Icons that are used when one is not manually specified
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    #################
    # Related Modal #
    #################
    # Use modals instead of popups
    "related_modal_active": False,

    #############
    # UI Tweaks #
    #############
    # Relative paths to custom CSS/JS scripts (must be present in static files)
    "custom_css": "admin/css/custom_admin.css",
    "custom_js": [
        "admin/js/collapse_persist.js",
        "admin/js/sidebar_persist.js",
        "admin/js/budget_line_form.js",
    ],
    # Whether to show the UI customizer on the sidebar
    "show_ui_builder": False,

    ###############
    # Change view #
    ###############
    # Render out the change view as a single form, or in tabs, current options are
    # - single
    # - horizontal_tabs (default)
    # - vertical_tabs
    # - collapsible
    # - carousel
    "changeform_format": "horizontal_tabs",
    # override change forms on a per modeladmin basis
    "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs"},
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-primary",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": True,
    "theme": "flatly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

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
    'apps.security.middleware.permission_context_middleware.PermissionContextMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'shared.context_processors.admin_theme',
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
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Serve project-level static and pre-collected vendor assets in development
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

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

# Configurable similarity suggestions for Budget Item Codes
BUDGETING_ITEM_CODE_SUGGESTIONS = {
    'enabled': env_bool('BUDGETING_SUGGEST_ENABLED', 'true'),
    'use_embeddings': env_bool('BUDGETING_SUGGEST_USE_EMBEDDINGS', 'true'),
    'embedding_threshold': env_float('BUDGETING_SUGGEST_EMBED_THRESHOLD', 0.70),
    'fuzzy_threshold': env_float('BUDGETING_SUGGEST_FUZZY_THRESHOLD', 0.10),
    'candidate_limit': env_int('BUDGETING_SUGGEST_CANDIDATE_LIMIT', 200),
    'results_limit': env_int('BUDGETING_SUGGEST_RESULTS_LIMIT', 5),
}

# Google Gemini API Configuration (Free LLM for Document Processing)
# Get your free API key from: https://makersuite.google.com/app/apikey
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY', None)

# Outlook Calendar OAuth Configuration
# Register your app at: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
OUTLOOK_CLIENT_ID = os.getenv('OUTLOOK_CLIENT_ID', None)
OUTLOOK_CLIENT_SECRET = os.getenv('OUTLOOK_CLIENT_SECRET', None)
OUTLOOK_REDIRECT_URI = os.getenv('OUTLOOK_REDIRECT_URI', None)
OUTLOOK_TENANT = os.getenv('OUTLOOK_TENANT', 'common')

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
    'ai-generate-operational-agenda': {
        'task': 'apps.ai_companion.tasks.generate_operational_agenda',
        'schedule': crontab(minute='*/30'),  # every 30 minutes
    },
    'tasks-check-overdue': {
        'task': 'apps.tasks.check_overdue_tasks',
        'schedule': crontab(minute='*/30'),  # every 30 minutes
    },
    # AI API Key Management
    'ai-reset-daily-counters': {
        'task': 'apps.ai_companion.tasks.reset_api_key_daily_counters',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    'ai-reset-minute-counters': {
        'task': 'apps.ai_companion.tasks.reset_api_key_minute_counters',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
    'ai-cleanup-old-logs': {
        'task': 'apps.ai_companion.tasks.cleanup_old_api_logs',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
}

# File upload limits
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600

# DRF & Schema
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # Prefer JWT first to avoid unintended CSRF enforcement via SessionAuthentication
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}

# Dev CORS/CSRF for local Vite server
CSRF_TRUSTED_ORIGINS = list(set([
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:8788',
    'http://127.0.0.1:8788',
]))

try:
    # If corsheaders is installed, allow local dev origins
    CORS_ALLOWED_ORIGINS = list(set([
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ]))
    CORS_ALLOW_CREDENTIALS = True
except Exception:
    pass

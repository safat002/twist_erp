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

INSTALLED_APPS = [
    'jazzmin',
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
# INSTALLED_APPS = THIRD_PARTY_APPS # + DYNAMIC_APPS

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
    'apps.security',
    'apps.audit',
    'apps.report_builder',
    'apps.tasks',
    'apps.notifications',
]

INSTALLED_APPS += STATIC_APPS

JAZZMIN_SETTINGS = {
    # title of the window (Will default to current_admin_site.site_title if absent or None)
    "site_title": "Twist Erp administration Control Centre",

    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_header": "Twist Erp administration Control Centre",

    # Brand & logos
    "site_brand": "TWIST ERP",
    "site_logo": "brand/twist-logo.svg",
    "login_logo": "brand/twist-logo.svg",
    "login_logo_dark": "brand/twist-logo-white.svg",

    # Welcome text on the login screen
    "welcome_sign": "Welcome to Twist ERP",

    # Copyright on the footer
    "copyright": "Twist ERP Ltd",

    # The model admin to search from the search bar, search bar will not be displayed if the list is empty
    "search_model": ["users.User", "auth.Group"],

    # Field name on user model that contains name of the user for the admin panel
    "user_avatar": None,

    ############
    # Top Menu #
    ############

    # Links to put along the top menu
    "topmenu_links": [
        # Url that gets reversed (Permissions can be added)
        {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},

        # external url that gets opened in a new window (Permissions can be added)
        {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},

        # model admin to link to (Permissions can be added)
        {"model": "users.User"},

        # App with dropdown menu to all its models pages (Permissions can be added)
        {"app": "companies"},
    ],

    #############
    # User Menu #
    #############

    # Additional links to include in the user menu on the top right ("app" url names) 
    "usermenu_links": [
        {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},
        {"model": "users.User"},
        {"name": "Theme", "url": "admin-appearance"}
    ],

    #############
    # Side Menu #
    #############

    # Whether to display the search bar in the sidebar
    "sidebar_show_search": True,

    # Start with navigation collapsed
    "navigation_expanded": False,

    # Whether to display the self or the user's groups first in the sidebar
    "sidebar_show_app_list": True,

    # Whether to enable the sidebar
    "sidebar_fixed": True,

    # Add a custom icon to the admin app list
    "icons": {
        "auth": "fas fa-users-cog",
        # Use the custom user model
        "users.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "admin": "fas fa-tools",
        "companies": "fas fa-building",
        "companies.company": "fas fa-building",
        "companies.companygroup": "fas fa-layer-group",
        "finance": "fas fa-dollar-sign",
        "finance.account": "fas fa-money-check-alt",
        "finance.journalvoucher": "fas fa-book",
        "inventory": "fas fa-boxes",
        "inventory.product": "fas fa-box",
        "inventory.warehouse": "fas fa-warehouse",
        "sales": "fas fa-chart-line",
        "sales.customer": "fas fa-user-tie",
        "sales.salesorder": "fas fa-shopping-cart",
        "procurement": "fas fa-truck-loading",
        "procurement.supplier": "fas fa-truck",
        "procurement.purchaseorder": "fas fa-file-invoice",
        "assets": "fas fa-tools",
        "assets.asset": "fas fa-wrench",
        "budgeting": "fas fa-calculator",
        "budgeting.budgetline": "fas fa-money-bill-wave",
        "production": "fas fa-industry",
        "production.bom": "fas fa-clipboard-list",
        "production.workorder": "fas fa-cogs",
        "hr": "fas fa-users",
        "hr.employee": "fas fa-user-friends",
        "hr.leaverequest": "fas fa-calendar-times",
        "projects": "fas fa-project-diagram",
        "projects.project": "fas fa-tasks",
        "ai_companion": "fas fa-robot",
        "ai_companion.aitrainingexample": "fas fa-brain",
        "security": "fas fa-shield-alt",
        "security.secpermission": "fas fa-key",
        "security.secrole": "fas fa-user-tag",
        "security.secuserrole": "fas fa-user-shield",
        "security.secscope": "fas fa-globe",
        "security.secsoDRule": "fas fa-handshake-slash",
    },

    # Custom links for sidebar app list
    "order_with_respect_to": [
        "companies",
        "security",
        "finance",
        "inventory",
        "sales",
        "procurement",
        "assets",
        "budgeting",
        "production",
        "hr",
        "projects",
        "ai_companion",
        "auth",
    ],

    # Custom links to include, there are 3 places where you can add links
    "custom_links": {
        "administration_security": [
            {"name": "Companies", "url": "admin:companies_company_changelist", "icon": "fas fa-building"},
            {"name": "Company Groups", "url": "admin:companies_companygroup_changelist", "icon": "fas fa-layer-group"},
            {"name": "Permissions", "url": "admin:security_secpermission_changelist", "icon": "fas fa-key"},
            {"name": "Roles", "url": "admin:security_secrole_changelist", "icon": "fas fa-user-tag"},
            {"name": "Users", "url": "admin:users_user_changelist", "icon": "fas fa-user"},
            {"name": "Groups", "url": "admin:auth_group_changelist", "icon": "fas fa-users"},
        ],
        "finance_accounting": [
            {"name": "Accounts", "url": "admin:finance_account_changelist", "icon": "fas fa-money-check-alt"},
            {"name": "Journal Vouchers", "url": "admin:finance_journalvoucher_changelist", "icon": "fas fa-book"},
            {"name": "Invoices", "url": "admin:finance_invoice_changelist", "icon": "fas fa-file-invoice"},
            {"name": "Payments", "url": "admin:finance_payment_changelist", "icon": "fas fa-dollar-sign"},
            {"name": "Budget Lines", "url": "admin:budgeting_budgetline_changelist", "icon": "fas fa-money-bill-wave"},
        ],
        "operations_supply_chain": [
            {"name": "Products", "url": "admin:inventory_product_changelist", "icon": "fas fa-box"},
            {"name": "Warehouses", "url": "admin:inventory_warehouse_changelist", "icon": "fas fa-warehouse"},
            {"name": "Purchase Orders", "url": "admin:procurement_purchaseorder_changelist", "icon": "fas fa-truck-loading"},
            {"name": "Work Orders", "url": "admin:production_workorder_changelist", "icon": "fas fa-cogs"},
            {"name": "Assets", "url": "admin:assets_asset_changelist", "icon": "fas fa-wrench"},
        ],
        "sales_crm": [
            {"name": "Customers", "url": "admin:sales_customer_changelist", "icon": "fas fa-user-tie"},
            {"name": "Sales Orders", "url": "admin:sales_salesorder_changelist", "icon": "fas fa-shopping-cart"},
        ],
        "human_resources_people": [
            {"name": "Employees", "url": "admin:hr_employee_changelist", "icon": "fas fa-user-friends"},
            {"name": "Leave Requests", "url": "admin:hr_leaverequest_changelist", "icon": "fas fa-calendar-times"},
            {"name": "Payroll Runs", "url": "admin:hr_payrollrun_changelist", "icon": "fas fa-file-invoice-dollar"},
            {"name": "Projects", "url": "admin:projects_project_changelist", "icon": "fas fa-tasks"},
        ],
        "ai_development_tools": [
            {"name": "AI Training Examples", "url": "admin:ai_companion_aitrainingexample_changelist", "icon": "fas fa-brain"},
            {"name": "Form Templates", "url": "admin:form_builder_formtemplate_changelist", "icon": "fas fa-file-alt"},
            {"name": "Workflow Templates", "url": "admin:workflows_workflowtemplate_changelist", "icon": "fas fa-project-diagram"},
            {"name": "Migration Jobs", "url": "admin:data_migration_migrationjob_changelist", "icon": "fas fa-database"},
            {"name": "Reports", "url": "admin:report_builder_reportdefinition_changelist", "icon": "fas fa-file-chart-pie"},
            {"name": "Audit Logs", "url": "admin:audit_auditlog_changelist", "icon": "fas fa-history"},
            {"name": "Tasks", "url": "admin:tasks_taskitem_changelist", "icon": "fas fa-tasks"},
            {"name": "Notifications", "url": "admin:notifications_notification_changelist", "icon": "fas fa-bell"}
        ]
    }
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-primary",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-light-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
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

# Google Gemini API Configuration (Free LLM for Document Processing)
# Get your free API key from: https://makersuite.google.com/app/apikey
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY', None)

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
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

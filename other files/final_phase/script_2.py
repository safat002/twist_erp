
# Create Nginx configuration

nginx_conf = """events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss;

    # Upstream servers
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:80;
    }

    # HTTP server
    server {
        listen 80;
        server_name _;
        client_max_body_size 100M;

        # Static files
        location /static/ {
            alias /static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # Media files
        location /media/ {
            alias /media/;
            expires 7d;
            add_header Cache-Control "public";
        }

        # API endpoints
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
            proxy_buffering off;
        }

        # Admin
        location /admin/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # HTTPS server (uncomment and configure for production)
    # server {
    #     listen 443 ssl http2;
    #     server_name your-domain.com;
    #     
    #     ssl_certificate /etc/nginx/ssl/cert.pem;
    #     ssl_certificate_key /etc/nginx/ssl/key.pem;
    #     
    #     # SSL configuration
    #     ssl_protocols TLSv1.2 TLSv1.3;
    #     ssl_ciphers HIGH:!aNULL:!MD5;
    #     ssl_prefer_server_ciphers on;
    #     
    #     # Same location blocks as HTTP server
    # }
}
"""

# Create Django settings for production
production_settings = """from .settings import *

DEBUG = False

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Security Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'twist_erp_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
    }
}

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
"""

# Create deployment script
deploy_script = """#!/bin/bash

# TWIST ERP Deployment Script

set -e

echo "🚀 Starting TWIST ERP Deployment..."

# Colors
GREEN='\\033[0;32m'
RED='\\033[0;31m'
NC='\\033[0m'

# Check if .env exists
if [ ! -f .env ]; then
    echo "${RED}Error: .env file not found!${NC}"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '#' | xargs)

echo "📦 Building Docker images..."
docker-compose build

echo "🗄️  Running database migrations..."
docker-compose run --rm backend python manage.py migrate

echo "👤 Creating superuser (if needed)..."
docker-compose run --rm backend python manage.py createsuperuser --noinput || true

echo "📊 Loading initial data..."
docker-compose run --rm backend python manage.py loaddata initial_companies.json || true
docker-compose run --rm backend python manage.py loaddata initial_permissions.json || true

echo "🔍 Indexing AI knowledge base..."
docker-compose run --rm backend python manage.py index_knowledge_base || true

echo "🚀 Starting services..."
docker-compose up -d

echo "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Services running:"
echo "  - Backend API: http://localhost:8000"
echo "  - Frontend: http://localhost:3000"
echo "  - Admin Panel: http://localhost:8000/admin"
echo "  - API Docs: http://localhost:8000/api/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
"""

# Create management commands

manage_commands = """# backend/core/management/commands/index_knowledge_base.py

from django.core.management.base import BaseCommand
from apps.ai_companion.models import AIKnowledgeBase
from apps.ai_companion.services.vector_store import VectorStoreService

class Command(BaseCommand):
    help = 'Index knowledge base for AI search'

    def handle(self, *args, **options):
        vector_store = VectorStoreService()
        
        companies = Company.objects.filter(is_active=True)
        
        for company in companies:
            self.stdout.write(f'Indexing knowledge base for {company.name}...')
            vector_store.index_erp_data(company.id)
            
        self.stdout.write(self.style.SUCCESS('✅ Indexing complete!'))
"""

files = {
    'nginx-conf': nginx_conf,
    'production-settings.py': production_settings,
    'deploy.sh': deploy_script,
    'index_knowledge_base_command.py': manage_commands
}

for filename, content in files.items():
    with open(filename, 'w') as f:
        f.write(content)

print("✓ Created deployment and configuration files:")
for f in files.keys():
    print(f"  - {f}")

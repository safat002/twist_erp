
# Create backend Dockerfile

backend_dockerfile = """FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    postgresql-client \\
    build-essential \\
    libpq-dev \\
    curl \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
COPY phase4-6-requirements.txt /app/
RUN pip install --upgrade pip && \\
    pip install -r requirements.txt && \\
    pip install -r phase4-6-requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy project
COPY . /app/

# Create directories
RUN mkdir -p /app/media /app/staticfiles /app/logs

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Run as non-root user
RUN useradd -m -u 1000 twist && chown -R twist:twist /app
USER twist

EXPOSE 8000

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
"""

# Create frontend Dockerfile
frontend_dockerfile = """FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source
COPY . .

# Build app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy build files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
"""

# Create .env.example
env_example = """# TWIST ERP Environment Variables

# Database
DB_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://postgres:your_password@localhost:54322/twist_erp_db

# Django
SECRET_KEY=change-this-to-a-random-secret-key-in-production
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email (for notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# AI Configuration
AI_LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.1
AI_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RASA_SERVER_URL=http://localhost:5005

# File Upload
MAX_UPLOAD_SIZE=104857600

# Logging
LOG_LEVEL=INFO

# Security
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# CORS (for development)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
"""

# Create .dockerignore
dockerignore = """__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
*.log
*.pot
*.mo
.git
.gitignore
.dockerignore
.env
.env.local
docker-compose.yml
Dockerfile
README.md
*.md
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
node_modules/
dist/
build/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
"""

files = {
    'backend-Dockerfile': backend_dockerfile,
    'frontend-Dockerfile': frontend_dockerfile,
    'env-example': env_example,
    'dockerignore': dockerignore
}

for filename, content in files.items():
    with open(filename, 'w') as f:
        f.write(content)

print("✓ Created Docker and environment configuration files:")
for f in files.keys():
    print(f"  - {f}")

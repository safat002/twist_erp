#!/bin/bash

# TWIST ERP Deployment Script

set -e

echo "🚀 Starting TWIST ERP Deployment..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

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
echo "  - Backend API: http://localhost:8788"
echo "  - Frontend: http://localhost:5174"
echo "  - Admin Panel: http://localhost:8788/admin"
echo "  - API Docs: http://localhost:8788/api/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"

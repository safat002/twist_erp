TWIST ERP – Local Development Quick Start (No Docker)

Prereqs
- Python 3.10
- Node.js 18+
- PostgreSQL 15+ and Redis (for Celery; optional if you won’t run Celery)

Backend (Django)
1) Create venv and install deps
   - Windows PowerShell
     - py -3.10 -m venv venv
     - .\venv\Scripts\activate
   - Install
     - pip install -r backend/requirements.txt

2) Ensure Postgres is running (default DSN: postgresql://postgres:dev_password@localhost:54322/erp_db)
   - Adjust port/creds or set $env:DATABASE_URL if different.

3) Run DB migrations
   - cd backend
   - python manage.py migrate

4) Seed initial data (optional but recommended)
   - python manage.py loaddata ../initial_companies.json
   - python manage.py loaddata ../initial_permissions.json
   - python manage.py loaddata ../initial_roles.json
   - python manage.py createsuperuser

5) Start API server
   - python manage.py runserver 0.0.0.0:8788

Embedded PostgreSQL (local, optional)
- Ensure PostgreSQL CLI (pg_ctl, initdb, psql) is on PATH
  - Example (Windows): C:\Program Files\PostgreSQL\15\bin
- Initialize and start embedded DB on port 54322
  - python backend/manage.py pg init
- Then run migrations and server as above

Notes
- Postgres is the default for local dev. To use SQLite instead, set:
  - PowerShell: $env:DATABASE_URL = "sqlite:///db.sqlite3"

Frontend (Vite + React)
1) In a new terminal
   - cd frontend
   - npm install
   - npm run dev

2) Visit
   - Frontend: http://localhost:5173
   - API: http://localhost:8788/api/
   - Admin: http://localhost:8788/admin/

Dev Proxy
- API calls to /api/* are proxied to http://localhost:8788 by frontend/vite.config.mjs.

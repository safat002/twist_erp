$ErrorActionPreference = 'Stop'

Write-Output "Starting embedded PostgreSQL..."
python backend/manage.py pg init

Write-Output "Applying migrations..."
python backend/manage.py migrate

Write-Output "Starting Django server on 0.0.0.0:8788"
python backend/manage.py runserver 0.0.0.0:8788

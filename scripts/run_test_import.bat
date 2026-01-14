@echo off
set DJANGO_SETTINGS_MODULE=diners.settings.base
set SECRET_KEY=devkey
set API_URL=http://localhost
set API_AUTH_USER=user
set API_AUTH_PASS=pass
E:\01-PROYECTOS\06-COMEDOR\prueba\.venv\Scripts\python.exe scripts/test_import_tasks.py

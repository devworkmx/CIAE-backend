# CIAE - Backend (FastAPI + PostgreSQL)

```bash
# 1. Configurar entorno y dependencias
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# 2. Levantar base de datos PostgreSQL
docker compose up -d

# 3. Crear tablas y usuario administrador inicial
python create_admin.py

# 4. Iniciar servidor de desarrollo
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

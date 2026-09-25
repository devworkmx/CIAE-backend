# CIAE - Backend (FastAPI + PostgreSQL)

```bash
# 1. Configurar y activar entorno virtual
python -m venv venv
venv\Scripts\activate

# 2. Instalar las librerias necesarias
pip install -r requirements.txt

# 3. Copiar las variables de entorno
# Recuerda cambiar las variables de ejemplo por las reales
cp .env.example .env

# Opcional
# En dado caso de ya tener un servicio SQL, se debe eliminar primero
docker compose down -v

# 4. Levantar base de datos PostgreSQL
docker compose up -d

# 5. Crear tablas y usuario administrador inicial
python create_superadmin.py

# 6. Iniciar servidor de desarrollo
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

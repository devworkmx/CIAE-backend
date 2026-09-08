# CIAE - Backend de Certificados y Gestión de Cursos (FastAPI + PostgreSQL)

Sistema backend para la gestión de cursos, registro de alumnos y emisión de certificados con códigos QR no predecibles generados mediante tokens criptográficos de alta seguridad.

---

## 1. Requisitos Previos

- Python 3.10+
- Docker Desktop (con Docker Compose activo)
- Git

---

## 2. Configuración Inicial del Entorno

1. Abre una terminal en la raíz del proyecto (`CIAE-backend`).

2. Crea y activa el entorno virtual de Python:
   - En Windows (PowerShell / Git Bash / CMD):
     python -m venv venv
     venv\Scripts\activate

3. Instala las dependencias necesarias:
   pip install -r requirements.txt

   > Nota de compatibilidad: Asegúrate de que `bcrypt==4.0.1` esté fijado en `requirements.txt` para garantizar compatibilidad con `passlib`.

4. Configura el archivo de variables de entorno:
   Copia el archivo de ejemplo:
   cp .env.example .env

   Asegúrate de que tu `.env` tenga las siguientes variables para desarrollo local:
   DATABASE_URL=postgresql://ciae_user:ciae_pass@localhost:5432/ciae_db
   SECRET_KEY=clave_secreta_jwt_para_firmar_tokens_2026
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=480
   FRONTEND_VALIDATION_URL=http://localhost:5173/validar
   ALLOWED_ORIGINS=http://localhost:5173

---

## 3. Despliegue de la Base de Datos (Docker)

El servicio utiliza un contenedor ligero con `postgres:16-alpine`.

1. Levanta el contenedor de PostgreSQL en segundo plano:
   docker compose up -d

2. Verifica que el contenedor esté corriendo correctamente en el puerto 5432:
   docker compose ps

_(Opcional)_ Si necesitas reiniciar la base de datos desde cero eliminando tablas y volúmenes:
docker compose down -v
docker compose up -d

---

## 4. Creación del Usuario Administrador

Antes de iniciar la API, ejecuta el script de inicialización para crear las tablas en PostgreSQL y dar de alta tu primera cuenta de acceso:

python create_admin.py

Ingresa interactivamente los datos solicitados:

- Username: admin (o tu usuario)
- Email: admin@ciae.com
- Nombre completo: Nombre del administrador
- Password: Contraseña segura

---

## 5. Levantar el Servidor de Desarrollo

Inicia FastAPI con recarga automática (_hot reload_):

uvicorn app.main:app --reload --port 8000

El servidor quedará disponible en:

- API Base: http://localhost:8000
- Documentación Interactiva (Swagger UI): http://localhost:8000/docs
- Documentación Alternativa (Redoc): http://localhost:8000/redoc

---

## 6. Endpoints Principales de la API

| Módulo       | Método               | Endpoint                       | Auth Requerida | Descripción                                  |
| :----------- | :------------------- | :----------------------------- | :------------- | :------------------------------------------- |
| Auth         | POST                 | /api/auth/login                | No             | Login administrativo; retorna JWT            |
| Cursos       | GET / POST           | /api/cursos                    | Sí (JWT)       | Listar y registrar cursos                    |
| Cursos       | GET / PATCH / DELETE | /api/cursos/{id}               | Sí (JWT)       | Detalle, edición y baja de cursos            |
| Alumnos      | GET / POST           | /api/alumnos                   | Sí (JWT)       | Listado y registro de alumnos con CURP       |
| Alumnos      | GET / PATCH / DELETE | /api/alumnos/{id}              | Sí (JWT)       | Detalle, edición y baja de alumnos           |
| Certificados | GET / POST           | /api/certificados              | Sí (JWT)       | Listado y emisión de certificados            |
| Certificados | PATCH                | /api/certificados/{id}/estatus | Sí (JWT)       | Cambiar estado (vigente, expirado, revocado) |
| Certificados | GET                  | /api/certificados/{id}/qr      | Sí (JWT)       | Descarga directa del PNG del código QR       |
| Público      | GET                  | /api/public/validar/{token}    | No             | Endpoint consumido al escanear el QR         |

---

## 7. Arquitectura de Seguridad del Código QR

1. Tokens Criptográficos: Cada certificado genera un `token_publico` aleatorio de 32 bytes con `secrets.token_urlsafe(32)` (~43 caracteres no predecibles).
2. Mitigación de Ataques de Enumeración: Los códigos QR nunca codifican el `id` consecutivo de la base de datos, imposibilitando adivinar registros ajenos cambiando números en la URL.
3. Privacidad de Datos: La ruta pública de validación (`/api/public/validar/{token}`) devuelve únicamente los datos esenciales para verificar la autenticidad académica (nombre del alumno, curso, vigencia), resguardando teléfonos, correos y CURP.

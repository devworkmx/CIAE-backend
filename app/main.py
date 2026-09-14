from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import settings
from app.database import Base, engine
from app.rate_limit import limiter
from app.routers import alumnos, auth, certificados, cursos, public

# Crear tablas en PostgreSQL si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CIAE - Sistema de Certificación y Validación Académica",
    version="1.0.0",
)

# Rate limiting global (usado explícitamente en /api/public y /api/auth/login)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- MANEJADOR GLOBAL DE ERRORES DE VALIDACIÓN (Pydantic) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errores_amigables = {}

    for error in exc.errors():
        # Obtiene el nombre del campo que falló (ej. 'nombre')
        campo = error["loc"][-1]
        tipo = error["type"]

        # Traduce o personaliza el mensaje según el tipo de error de Pydantic
        if "string_too_short" in tipo or "min_length" in tipo:
            errores_amigables[campo] = "Este campo es demasiado corto (mínimo 3 caracteres)."
        elif "missing" in tipo:
            errores_amigables[campo] = "Este campo es obligatorio."
        else:
            errores_amigables[campo] = "Dato inválido."

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Error de validación en los datos enviados.",
            "errors": errores_amigables
        }
    )

# CORS: se usa la lista explícita de orígenes definida en la configuración
# (variable de entorno ALLOWED_ORIGINS). En producción, ALLOWED_ORIGINS debe
# apuntar únicamente al/los dominio(s) reales del frontend, nunca a un
# regex amplio que acepte cualquier IP de red local o cualquier puerto.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Encabezados de seguridad básicos
@app.middleware("http")
async def agregar_encabezados_seguridad(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Registro de routers
app.include_router(auth.router)
app.include_router(cursos.router)
app.include_router(alumnos.router)
app.include_router(certificados.router)
app.include_router(public.router)


@app.get("/", tags=["salud"])
def revision_salud():
    return {"estado": "activo", "servicio": "CIAE Backend API"}

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import settings
from app.database import Base, engine
from app.rate_limit import limiter
from app.routers import alumnos, auth, certificados, cursos, public, superadmin


# --- CICLO DE VIDA (Arranque limpio y rápido) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas al arrancar la aplicación sin bloquear la importación del módulo
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="CIAE - Sistema de Certificación y Validación Académica",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting global
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- MANEJADOR GLOBAL DE ERRORES DE VALIDACIÓN (Pydantic) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errores_amigables = {}

    for error in exc.errors():
        campo = error["loc"][-1]
        tipo = error["type"]

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
            "errors": errores_amigables,
        },
    )


# --- MIDDLEWARES DE RENDIMIENTO Y SEGURIDAD ---

# 1. Compresión Gzip para payloads JSON > 1KB (reduce drásticamente el tamaño transferido)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. CORS optimizado con caché de preflight (max_age)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,  # El navegador recuerda la autorización OPTIONS por 24 horas
)


# 3. Encabezados de seguridad básicos
@app.middleware("http")
async def agregar_encabezados_seguridad(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# --- REGISTRO DE ROUTERS ---
app.include_router(auth.router)
app.include_router(cursos.router)
app.include_router(alumnos.router)
app.include_router(certificados.router)
app.include_router(public.router)
app.include_router(superadmin.router)


# --- ENDPOINT DE SALUD (Health Check) ---
@app.get("/", tags=["salud"])
def revision_salud():
    return JSONResponse(
        content={"estado": "activo", "servicio": "CIAE Backend API"},
        headers={"Cache-Control": "no-store"},
    )

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import alumnos, auth, certificados, cursos, public

# Crear tablas en PostgreSQL si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CIAE - Sistema de Certificación y Validación Académica",
    version="1.0.0",
)

# Permite localhost y cualquier IP de red local (192.168.x.x, 10.x.x.x, 172.x.x.x) en cualquier puerto
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.\d+\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de routers
app.include_router(auth.router)
app.include_router(cursos.router)
app.include_router(alumnos.router)
app.include_router(certificados.router)
app.include_router(public.router)


@app.get("/", tags=["salud"])
def revision_salud():
    return {"estado": "activo", "servicio": "CIAE Backend API"}

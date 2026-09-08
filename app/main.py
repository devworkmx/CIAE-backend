from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, certificados, cursos, alumnos, public

# En producción usa Alembic para migraciones en vez de create_all.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CIAE - API de Certificados")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cursos.router)
app.include_router(alumnos.router)
app.include_router(certificados.router)
app.include_router(public.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

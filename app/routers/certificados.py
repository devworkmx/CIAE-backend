import io
from typing import List, Optional

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import Alumno, Certificado, Curso, Usuario
from app.schemas import CertificadoCreate, CertificadoOut, CertificadoUpdateEstatus
from app.security import get_current_user

router = APIRouter(
    prefix="/api/certificados",
    tags=["certificados"],
    dependencies=[Depends(get_current_user)],
)


def _url_validacion(token: str) -> str:
    # Ej: http://localhost:5173/validar/AbC123...
    # El QR siempre apunta al token aleatorio, nunca a un ID consecutivo[cite: 2]
    return f"{settings.FRONTEND_VALIDATION_URL.rstrip('/')}/{token}"


@router.get("", response_model=List[CertificadoOut])
def listar_certificados(
    curso_id: Optional[int] = None,
    alumno_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Certificado).options(joinedload(Certificado.alumno))

    if curso_id is not None:
        query = query.filter(Certificado.curso_id == curso_id)
    if alumno_id is not None:
        query = query.filter(Certificado.alumno_id == alumno_id)

    return query.order_by(Certificado.creado_en.desc()).all()


@router.get("/{certificado_id}", response_model=CertificadoOut)
def obtener_certificado(certificado_id: int, db: Session = Depends(get_db)):
    cert = (
        db.query(Certificado)
        .options(joinedload(Certificado.alumno))
        .filter(Certificado.id == certificado_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado"
        )
    return cert


@router.post("", response_model=CertificadoOut, status_code=status.HTTP_201_CREATED)
def crear_certificado(
    datos: CertificadoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # 1. Verificar que el curso exista
    curso = db.query(Curso).filter(Curso.id == datos.curso_id).first()
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El curso especificado no existe"
        )

    # 2. Verificar que el alumno exista
    alumno = db.query(Alumno).filter(Alumno.id == datos.alumno_id).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El alumno especificado no existe"
        )

    # 3. Crear el certificado enlazado (el token_publico se genera solo en el modelo)
    cert = Certificado(**datos.model_dump(), creado_por_id=current_user.id)
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


@router.patch("/{certificado_id}/estatus", response_model=CertificadoOut)
def cambiar_estatus(
    certificado_id: int,
    datos: CertificadoUpdateEstatus,
    db: Session = Depends(get_db)
):
    cert = (
        db.query(Certificado)
        .options(joinedload(Certificado.alumno))
        .filter(Certificado.id == certificado_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado"
        )

    cert.estatus = datos.estatus
    db.commit()
    db.refresh(cert)
    return cert


@router.delete("/{certificado_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_certificado(certificado_id: int, db: Session = Depends(get_db)):
    cert = db.query(Certificado).filter(Certificado.id == certificado_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado"
        )
    db.delete(cert)
    db.commit()


@router.get("/{certificado_id}/qr")
def descargar_qr(certificado_id: int, db: Session = Depends(get_db)):
    """
    Genera el PNG del QR en memoria (sin almacenar imágenes en disco ni nube)[cite: 2].
    Codifica la URL pública construida con el token_publico[cite: 2].
    """
    cert = (
        db.query(Certificado)
        .options(joinedload(Certificado.alumno))
        .filter(Certificado.id == certificado_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado"
        )

    url = _url_validacion(cert.token_publico)

    img = qrcode.make(url, box_size=10, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    nombre_limpio = cert.alumno_nombre.replace(" ", "_") if cert.alumno_nombre else f"cert_{cert.id}"
    filename = f"qr_{nombre_limpio}.png"

    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

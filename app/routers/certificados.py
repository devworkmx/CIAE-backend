import io
from datetime import date
from typing import List, Optional
from urllib.parse import urlparse
from dateutil.relativedelta import relativedelta

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import Alumno, Certificado, Curso, Usuario
from app.schemas import (
    CertificadoCreate,
    CertificadoOut,
    CertificadoUpdate,
    CertificadoUpdateEstatus,
)
from app.security import get_current_user

router = APIRouter(
    prefix="/api/certificados",
    tags=["certificados"],
    dependencies=[Depends(get_current_user)],
)


def _obtener_url_qr(request: Request, token: str) -> str:
    base_url = getattr(
        settings, "FRONTEND_VALIDATION_URL", "http://localhost:5173/validar"
    )

    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        parsed = urlparse(origin)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return f"{base}/validar/{token}"

    return f"{base_url.rstrip('/')}/{token}"


@router.get("", response_model=List[CertificadoOut])
def listar_certificados(
    curso_id: Optional[int] = None,
    alumno_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Certificado).options(
        joinedload(Certificado.alumno),
        joinedload(Certificado.curso),
    )
    if curso_id is not None:
        query = query.filter(Certificado.curso_id == curso_id)
    if alumno_id is not None:
        query = query.filter(Certificado.alumno_id == alumno_id)
    return query.order_by(Certificado.creado_en.desc()).all()


@router.get("/{certificado_id}", response_model=CertificadoOut)
def obtener_certificado(certificado_id: int, db: Session = Depends(get_db)):
    cert = (
        db.query(Certificado)
        .options(
            joinedload(Certificado.alumno),
            joinedload(Certificado.curso),
        )
        .filter(Certificado.id == certificado_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado",
        )
    return cert


@router.post("", response_model=CertificadoOut, status_code=status.HTTP_201_CREATED)
def crear_certificado(
    datos: CertificadoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Validar duplicidad de folio manual
    folio_existente = (
        db.query(Certificado)
        .filter(Certificado.folio_manual.ilike(datos.folio_manual.strip()))
        .first()
    )
    if folio_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El folio manual asignado ya existe. Por favor ingrese un folio único.",
        )

    curso = db.query(Curso).filter(Curso.id == datos.curso_id).first()
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El curso especificado no existe",
        )

    alumno = db.query(Alumno).filter(Alumno.id == datos.alumno_id).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El alumno especificado no existe",
        )

    payload = datos.model_dump()
    payload["folio_manual"] = payload["folio_manual"].strip()

    # Manejar fecha de emisión
    fecha_emision = payload.get("fecha_emision")
    if not fecha_emision:
        fecha_emision = date.today()
        payload["fecha_emision"] = fecha_emision

    # Calcular vigencia si no se especifica y el curso la requiere
    if payload.get("tiene_vigencia") and not payload.get("fecha_vigencia"):
        meses = curso.meses_vigencia or 12
        payload["fecha_vigencia"] = fecha_emision + relativedelta(months=meses)

    cert = Certificado(**payload, creado_por_id=current_user.id)
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


@router.patch("/{certificado_id}", response_model=CertificadoOut)
def actualizar_certificado(
    certificado_id: int,
    datos: CertificadoUpdate,
    db: Session = Depends(get_db),
):
    cert = (
        db.query(Certificado)
        .options(joinedload(Certificado.alumno), joinedload(Certificado.curso))
        .filter(Certificado.id == certificado_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado",
        )

    update_dict = datos.model_dump(exclude_unset=True)

    if "folio_manual" in update_dict:
        folio_limpio = update_dict["folio_manual"].strip()
        duplicado = (
            db.query(Certificado)
            .filter(
                Certificado.folio_manual.ilike(folio_limpio),
                Certificado.id != certificado_id,
            )
            .first()
        )
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El folio manual asignado ya está en uso por otro certificado",
            )
        update_dict["folio_manual"] = folio_limpio

    for key, value in update_dict.items():
        setattr(cert, key, value)

    db.commit()
    db.refresh(cert)
    return cert


@router.patch("/{certificado_id}/estatus", response_model=CertificadoOut)
def cambiar_estatus(
    certificado_id: int,
    datos: CertificadoUpdateEstatus,
    db: Session = Depends(get_db),
):
    cert = (
        db.query(Certificado)
        .options(joinedload(Certificado.alumno), joinedload(Certificado.curso))
        .filter(Certificado.id == certificado_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado",
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
            detail="Certificado no encontrado",
        )
    db.delete(cert)
    db.commit()


@router.get("/{certificado_id}/qr")
def descargar_qr(
    certificado_id: int,
    request: Request,
    base_url: Optional[str] = None,
    db: Session = Depends(get_db),
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
            detail="Certificado no encontrado",
        )

    if base_url:
        url = f"{base_url.rstrip('/')}/validar/{cert.token_publico}"
    else:
        url = _obtener_url_qr(request, cert.token_publico)

    img = qrcode.make(url, box_size=10, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    nombre_limpio = (
        cert.alumno_nombre.strip().replace(" ", "_")
        if cert.alumno_nombre
        else f"cert_{cert.id}"
    )
    filename = f"qr_{nombre_limpio}.png"

    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

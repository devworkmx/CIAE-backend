import io
from datetime import date
from typing import List, Optional
from urllib.parse import urlparse
from dateutil.relativedelta import relativedelta

import qrcode
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
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
from app.security import get_current_user, require_admin
from app.services.email import enviar_correo_certificado

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
        origen_normalizado = f"{parsed.scheme}://{parsed.netloc}"
        if origen_normalizado in settings.cors_origins:
            return f"{origen_normalizado}/validar/{token}"

    return f"{base_url.rstrip('/')}/{token}"


@router.get("", response_model=List[CertificadoOut])
def listar_certificados(
    curso_id: Optional[int] = None,
    alumno_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = (
        db.query(Certificado)
        .options(
            joinedload(Certificado.alumno),
            joinedload(Certificado.curso),
        )
        .filter(Certificado.tenant_id == current_user.tenant_id)
    )
    if curso_id is not None:
        query = query.filter(Certificado.curso_id == curso_id)
    if alumno_id is not None:
        query = query.filter(Certificado.alumno_id == alumno_id)
    return query.order_by(Certificado.creado_en.desc()).all()


@router.get("/{certificado_id}", response_model=CertificadoOut)
def obtener_certificado(
    certificado_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cert = (
        db.query(Certificado)
        .options(
            joinedload(Certificado.alumno),
            joinedload(Certificado.curso),
        )
        .filter(
            Certificado.id == certificado_id,
            Certificado.tenant_id == current_user.tenant_id,
        )
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    folio_existente = (
        db.query(Certificado)
        .filter(
            Certificado.folio_manual.ilike(datos.folio_manual.strip()),
            Certificado.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if folio_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El folio manual asignado ya existe en su institución.",
        )

    curso = (
        db.query(Curso)
        .filter(Curso.id == datos.curso_id, Curso.tenant_id == current_user.tenant_id)
        .first()
    )
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El curso especificado no existe",
        )

    alumno = (
        db.query(Alumno)
        .filter(Alumno.id == datos.alumno_id, Alumno.tenant_id == current_user.tenant_id)
        .first()
    )
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El alumno especificado no existe",
        )

    payload = datos.model_dump()
    payload["folio_manual"] = payload["folio_manual"].strip()
    payload["tenant_id"] = current_user.tenant_id

    fecha_emision = payload.get("fecha_emision")
    if not fecha_emision:
        fecha_emision = date.today()
        payload["fecha_emision"] = fecha_emision

    if payload.get("tiene_vigencia") and not payload.get("fecha_vigencia"):
        meses = curso.meses_vigencia or 12
        payload["fecha_vigencia"] = fecha_emision + relativedelta(months=meses)

    cert = Certificado(**payload, creado_por_id=current_user.id)
    db.add(cert)
    db.commit()
    db.refresh(cert)

    if alumno.email:
        background_tasks.add_task(
            enviar_correo_certificado,
            destinatario=alumno.email,
            alumno_nombre=f"{alumno.nombre} {alumno.apellidos}",
            curso_nombre=curso.nombre,
            folio=cert.folio_manual,
            token_publico=cert.token_publico,
            instructor=cert.instructor,
            tiene_vigencia=cert.tiene_vigencia,
            fecha_vigencia=str(cert.fecha_vigencia) if cert.fecha_vigencia else None,
        )

    return cert


@router.post("/{certificado_id}/renovar")
def renovar_certificado(
    certificado_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Renueva la vigencia de un certificado vencido tomando como base
    los meses_vigencia configurados en el curso correspondiente.
    Mantiene el mismo token_publico y QR original.
    """
    cert = (
        db.query(Certificado)
        .filter(
            Certificado.id == certificado_id,
            Certificado.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado en su institución.",
        )

    curso = (
        db.query(Curso)
        .filter(
            Curso.id == cert.curso_id,
            Curso.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not curso or not curso.tiene_vigencia or not curso.meses_vigencia or curso.meses_vigencia <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El curso asignado a este certificado no tiene configurada una vigencia en meses válida.",
        )

    hoy = date.today()
    nueva_expiracion = hoy + relativedelta(months=curso.meses_vigencia)

    cert.fecha_emision = hoy
    cert.fecha_vigencia = nueva_expiracion
    cert.tiene_vigencia = True
    cert.estatus = "vigente"

    db.commit()
    db.refresh(cert)

    return {
        "mensaje": f"Acreditación renovada con éxito por {curso.meses_vigencia} meses.",
        "nueva_fecha_emision": cert.fecha_emision,
        "nueva_fecha_vigencia": cert.fecha_vigencia,
        "meses_aplicados": curso.meses_vigencia,
        "folio": cert.folio_manual,
    }


@router.patch("/{certificado_id}", response_model=CertificadoOut)
def actualizar_certificado(
    certificado_id: int,
    datos: CertificadoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cert = (
        db.query(Certificado)
        .options(joinedload(Certificado.alumno), joinedload(Certificado.curso))
        .filter(
            Certificado.id == certificado_id,
            Certificado.tenant_id == current_user.tenant_id,
        )
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
                Certificado.tenant_id == current_user.tenant_id,
                Certificado.id != certificado_id,
            )
            .first()
        )
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El folio manual asignado ya está en uso en su institución",
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
    current_admin: Usuario = Depends(require_admin),
):
    cert = (
        db.query(Certificado)
        .options(joinedload(Certificado.alumno), joinedload(Certificado.curso))
        .filter(
            Certificado.id == certificado_id,
            Certificado.tenant_id == current_admin.tenant_id,
        )
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
def eliminar_certificado(
    certificado_id: int,
    db: Session = Depends(get_db),
    current_admin: Usuario = Depends(require_admin),
):
    cert = (
        db.query(Certificado)
        .filter(
            Certificado.id == certificado_id,
            Certificado.tenant_id == current_admin.tenant_id,
        )
        .first()
    )
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
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cert = (
        db.query(Certificado)
        .options(joinedload(Certificado.alumno))
        .filter(
            Certificado.id == certificado_id,
            Certificado.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado",
        )

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

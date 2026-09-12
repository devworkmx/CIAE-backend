from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Alumno, Certificado
from app.schemas import (
    AlumnoPublicoResumen,
    BusquedaPublicaResponse,
    ValidacionPublicaResponse,
)

router = APIRouter(prefix="/api/public", tags=["público"])


def _construir_respuesta_validacion(cert: Certificado) -> ValidacionPublicaResponse:
    hoy = date.today()
    sigue_vigente = True
    motivo = None
    documento_valido = True

    # 1. Comprobación crítica: ¿El alumno fue dado de baja?
    alumno_activo = cert.alumno.activo if cert.alumno and cert.alumno.activo is not None else True
    if not alumno_activo:
        documento_valido = False
        sigue_vigente = False
        motivo = "ALUMNO_DADO_DE_BAJA"

    # 2. Comprobación de estatus del certificado
    elif cert.estatus and cert.estatus != "vigente":
        documento_valido = False
        sigue_vigente = False
        motivo = "CERTIFICADO_REVOCADO"

    # 3. Comprobación de vigencia en fechas
    elif cert.tiene_vigencia and cert.fecha_vigencia and hoy > cert.fecha_vigencia:
        sigue_vigente = False
        motivo = "CERTIFICADO_VENCIDO"

    # Obtener nombre asegurando que no quede None
    nombre_alumno = cert.alumno_nombre
    if not nombre_alumno and cert.alumno:
        nombre_alumno = f"{cert.alumno.nombre} {cert.alumno.apellidos}"

    return ValidacionPublicaResponse(
        valido=documento_valido,
        folio=cert.folio_manual or "",
        alumno_nombre=nombre_alumno or "Sin Nombre",
        curso_nombre=cert.curso.nombre if cert.curso else "N/A",
        duracion_horas=cert.curso.duracion_horas if cert.curso else 0,
        fecha_emision=cert.fecha_emision,
        tiene_vigencia=bool(cert.tiene_vigencia),
        fecha_vigencia=cert.fecha_vigencia,
        vigente=sigue_vigente,
        instructor=cert.instructor or "Instructor Institucional",
        estatus=cert.estatus or "vigente",
        alumno_activo=alumno_activo,
        motivo_invalidez=motivo,
        token_publico=cert.token_publico,
    )


@router.get("/validar/{token}", response_model=ValidacionPublicaResponse)
def validar_certificado_publico(token: str, db: Session = Depends(get_db)):
    cert = (
        db.query(Certificado)
        .options(
            joinedload(Certificado.alumno),
            joinedload(Certificado.curso),
        )
        .filter(Certificado.token_publico == token)
        .first()
    )

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no registrado o token no válido",
        )

    return _construir_respuesta_validacion(cert)


@router.get("/buscar", response_model=BusquedaPublicaResponse)
def buscar_certificado_manual(
    tipo: str = Query(..., regex="^(folio|curp)$", description="Tipo: folio o curp"),
    valor: str = Query(..., min_length=1, description="Folio manual o CURP"),
    db: Session = Depends(get_db),
):
    valor_limpio = valor.strip()

    if tipo == "folio":
        cert = (
            db.query(Certificado)
            .options(
                joinedload(Certificado.alumno),
                joinedload(Certificado.curso),
            )
            .filter(Certificado.folio_manual.ilike(valor_limpio))
            .first()
        )

        if not cert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró ningún certificado asociado al folio '{valor_limpio}'.",
            )

        alumno_resumen = None
        if cert.alumno:
            alumno_resumen = AlumnoPublicoResumen(
                nombre=f"{cert.alumno.nombre} {cert.alumno.apellidos}",
                curp=cert.alumno.curp,
                activo=cert.alumno.activo if cert.alumno.activo is not None else True,
            )

        return BusquedaPublicaResponse(
            tipo_consulta="folio",
            alumno=alumno_resumen,
            certificados=[_construir_respuesta_validacion(cert)],
        )

    else:  # tipo == "curp"
        # 1. Localizar al alumno en el padrón
        alumno = (
            db.query(Alumno)
            .filter(Alumno.curp.ilike(valor_limpio))
            .first()
        )

        if not alumno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró ningún alumno registrado con la CURP '{valor_limpio}'.",
            )

        # 2. Obtener TODOS (.all()) los certificados asociados al alumno ordenados por fecha
        certs = (
            db.query(Certificado)
            .options(
                joinedload(Certificado.alumno),
                joinedload(Certificado.curso),
            )
            .filter(Certificado.alumno_id == alumno.id)
            .order_by(Certificado.fecha_emision.desc(), Certificado.id.desc())
            .all()  # <--- AQUÍ SE OBTIENEN TODOS LOS CERTIFICADOS
        )

        if not certs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El alumno está registrado en el padrón pero aún no cuenta con certificados emitidos.",
            )

        alumno_resumen = AlumnoPublicoResumen(
            nombre=f"{alumno.nombre} {alumno.apellidos}",
            curp=alumno.curp,
            activo=alumno.activo if alumno.activo is not None else True,
        )

        return BusquedaPublicaResponse(
            tipo_consulta="curp",
            alumno=alumno_resumen,
            certificados=[_construir_respuesta_validacion(c) for c in certs],
        )

from datetime import date
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Alumno, Certificado
from app.rate_limit import limiter
from app.schemas import (
    AlumnoPublicoResumen,
    BusquedaPublicaResponse,
    ContactoRequest,
    ContactoResponse,
    ValidacionPublicaResponse,
)
from app.services.email import enviar_correo_contacto

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

    nombre_institucion = cert.tenant.nombre if cert.tenant else "Institución Oficial"

    return ValidacionPublicaResponse(
        valido=documento_valido,
        folio=cert.folio_manual or "",
        institucion=nombre_institucion,
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
@limiter.limit("30/minute")
def validar_certificado_publico(
    request: Request, token: str, db: Session = Depends(get_db)
):
    cert = (
        db.query(Certificado)
        .options(
            joinedload(Certificado.alumno),
            joinedload(Certificado.curso),
            joinedload(Certificado.tenant),  # Carga la institución emisora
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
@limiter.limit("10/minute")
def buscar_certificado_manual(
    request: Request,
    tipo: str = Query(..., regex="^(folio|curp)$", description="Tipo: folio o curp"),
    valor: str = Query(..., min_length=1, max_length=50, description="Folio manual o CURP"),
    db: Session = Depends(get_db),
):
    valor_limpio = valor.strip().upper()

    if tipo == "folio":
        cert = (
            db.query(Certificado)
            .options(
                joinedload(Certificado.alumno),
                joinedload(Certificado.curso),
                joinedload(Certificado.tenant),  # Carga la institución emisora
            )
            .filter(func.upper(Certificado.folio_manual) == valor_limpio)
            .first()
        )

        if not cert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró ningún certificado asociado al folio proporcionado.",
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
        alumno = (
            db.query(Alumno)
            .filter(func.upper(Alumno.curp) == valor_limpio)
            .first()
        )

        if not alumno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró ningún alumno registrado con la CURP proporcionada.",
            )

        certs = (
            db.query(Certificado)
            .options(
                joinedload(Certificado.alumno),
                joinedload(Certificado.curso),
                joinedload(Certificado.tenant),  # Carga la institución emisora
            )
            .filter(Certificado.alumno_id == alumno.id)
            .order_by(Certificado.fecha_emision.desc(), Certificado.id.desc())
            .all()
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


@router.post("/contacto", response_model=ContactoResponse)
@limiter.limit("5/minute")
def enviar_contacto(
    request: Request,
    datos: ContactoRequest,
    background_tasks: BackgroundTasks,
):
    """
    Recibe el formulario público de contacto del sitio y despacha el correo
    en segundo plano (BackgroundTasks) para no hacer esperar al visitante
    a que Resend responda. Limitado a 5 solicitudes por minuto por IP para
    evitar que se use como vector de spam.
    """
    background_tasks.add_task(
        enviar_correo_contacto,
        nombre=datos.nombre,
        correo=datos.correo,
        mensaje=datos.mensaje,
    )
    return ContactoResponse(success=True)
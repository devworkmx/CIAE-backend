from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Alumno, Certificado
from app.schemas import ValidacionPublicaResponse

router = APIRouter(prefix="/api/public", tags=["público"])


def _construir_respuesta_validacion(cert: Certificado) -> ValidacionPublicaResponse:
    hoy = date.today()
    sigue_vigente = True

    if cert.tiene_vigencia and cert.fecha_vigencia:
        sigue_vigente = hoy <= cert.fecha_vigencia

    if cert.estatus != "vigente":
        sigue_vigente = False

    return ValidacionPublicaResponse(
        valido=True,
        folio=cert.folio_manual,
        alumno_nombre=cert.alumno_nombre,
        curso_nombre=cert.curso.nombre if cert.curso else "N/A",
        duracion_horas=cert.curso.duracion_horas if cert.curso else 0,
        fecha_emision=cert.fecha_emision,
        tiene_vigencia=cert.tiene_vigencia,
        fecha_vigencia=cert.fecha_vigencia,
        vigente=sigue_vigente,
        instructor=cert.instructor,
        estatus=cert.estatus,
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


@router.get("/buscar", response_model=ValidacionPublicaResponse)
def buscar_certificado_manual(
    tipo: str = Query(..., regex="^(folio|curp)$", description="Tipo: folio o curp"),
    valor: str = Query(..., min_length=3, description="Folio manual o CURP"),
    db: Session = Depends(get_db),
):
    valor_limpio = valor.strip()

    query = db.query(Certificado).options(
        joinedload(Certificado.alumno),
        joinedload(Certificado.curso),
    )

    if tipo == "folio":
        cert = query.filter(Certificado.folio_manual.ilike(valor_limpio)).first()
    else:  # tipo == "curp"
        cert = (
            query.join(Certificado.alumno)
            .filter(Alumno.curp.ilike(valor_limpio))
            .order_by(Certificado.fecha_emision.desc())
            .first()
        )

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún certificado asociado al {tipo.upper()} ingresado",
        )

    return _construir_respuesta_validacion(cert)

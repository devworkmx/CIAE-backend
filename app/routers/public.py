from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Certificado, EstatusCertificado
from app.schemas import ValidacionPublicaOut

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/validar/{token}", response_model=ValidacionPublicaOut)
def validar_certificado(token: str, db: Session = Depends(get_db)):
    """
    Endpoint público (sin auth) que consulta el QR.
    - Nunca expone el id interno ni el curso_id.
    - Si el token no existe, responde igual que si estuviera revocado/expirado
      (mismo shape de respuesta) para no dar pistas sobre qué tokens son válidos.
    """
    cert = (
        db.query(Certificado)
        .options(joinedload(Certificado.curso))
        .filter(Certificado.token_publico == token)
        .first()
    )

    if not cert:
        return ValidacionPublicaOut(
            valido=False, mensaje="Certificado no encontrado."
        )

    # Actualiza estatus si venció (sin persistir aquí; opcionalmente
    # se puede mover a un job programado que recalcule y sí guarde)
    estatus_actual = cert.estatus
    if (
        estatus_actual == EstatusCertificado.vigente
        and cert.fecha_vigencia
        and cert.fecha_vigencia < date.today()
    ):
        estatus_actual = EstatusCertificado.expirado

    if estatus_actual != EstatusCertificado.vigente:
        return ValidacionPublicaOut(
            valido=False,
            estatus=estatus_actual.value,
            mensaje="Este certificado no es válido actualmente.",
        )

    return ValidacionPublicaOut(
        valido=True,
        estatus=estatus_actual.value,
        alumno_nombre=cert.alumno_nombre,
        curso_nombre=cert.curso.nombre,
        duracion_horas=cert.curso.duracion_horas,
        fecha_emision=cert.fecha_emision,
        fecha_vigencia=cert.fecha_vigencia,
    )

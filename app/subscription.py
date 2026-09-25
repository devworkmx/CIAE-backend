"""
Lógica centralizada del ciclo de vida de la suscripción de un tenant.

Fase 1 del SaaS: el superadmin (tú) sigue siendo el intermediario de todo
alta, cobro y renovación. No hay pasarela de pago ni auto-registro todavía;
esto solo formaliza las reglas de acceso para que sean consistentes en toda
la app (backend y frontend) y fáciles de mover a fase 2 (pagos automáticos)
sin tocar el resto del sistema.

Reglas de negocio (definidas por el flujo real de trabajo):
- Si el superadmin CANCELA la suscripción pero el tenant aún tiene tiempo
  pagado (fecha_vencimiento en el futuro), el tenant conserva acceso
  completo hasta que se le acabe ese tiempo. No se le corta antes de tiempo.
- Si se le acaba el tiempo (fecha_vencimiento ya pasó), o fue cancelado sin
  tiempo pendiente, el tenant entra en estado "congelado": puede iniciar
  sesión y VER toda su información (certificados, alumnos, cursos), pero no
  puede crear, editar, eliminar ni emitir nada hasta que se le renueve.
- "suspendido" es un freno manual e inmediato del superadmin (p. ej. disputa
  de pago, uso indebido) que congela el acceso sin importar la vigencia
  restante.
"""

from datetime import date
from typing import Optional, Protocol

ESTADO_ACTIVO = "activo"
ESTADO_CONGELADO = "congelado"
ESTADO_SUSPENDIDO = "suspendido"

# Catálogo sugerido de planes para los formularios del superadmin. Es solo una
# guía de UI (el campo `plan` en la base de datos sigue siendo texto libre),
# así que se puede editar aquí sin migraciones.
PLANES_SUGERIDOS = [
    {"id": "basico", "nombre": "Básico", "meses_sugeridos": 1},
    {"id": "pro", "nombre": "Pro", "meses_sugeridos": 1},
    {"id": "premium", "nombre": "Premium", "meses_sugeridos": 12},
]

DURACIONES_SUGERIDAS_MESES = [1, 3, 6, 12]


class _TenantLike(Protocol):
    estatus_suscripcion: Optional[str]
    fecha_vencimiento: Optional[date]


def dias_restantes(tenant: Optional[_TenantLike]) -> Optional[int]:
    """Días que faltan para que venza el tiempo pagado (negativo si ya venció)."""
    if tenant is None or not tenant.fecha_vencimiento:
        return None
    return (tenant.fecha_vencimiento - date.today()).days


def calcular_estado_acceso(tenant: Optional[_TenantLike]) -> str:
    """
    Estado de acceso EFECTIVO del tenant, combinando el estatus manual que
    fija el superadmin con la vigencia pagada. Este es el único lugar donde
    vive esta regla; todo lo demás (backend y frontend) debe consultarlo en
    vez de reimplementar la comparación de fechas.
    """
    if tenant is None:
        return ESTADO_CONGELADO

    if tenant.estatus_suscripcion == ESTADO_SUSPENDIDO:
        return ESTADO_SUSPENDIDO

    tiempo_pagado_vencido = (
        tenant.fecha_vencimiento is not None and tenant.fecha_vencimiento < date.today()
    )
    if tiempo_pagado_vencido:
        return ESTADO_CONGELADO

    if tenant.estatus_suscripcion == "cancelado" and tenant.fecha_vencimiento is None:
        # Cancelado y sin fecha de vigencia registrada: no hay "tiempo restante"
        # que justifique mantenerlo activo.
        return ESTADO_CONGELADO

    return ESTADO_ACTIVO


def tiene_acceso_completo(tenant: Optional[_TenantLike]) -> bool:
    return calcular_estado_acceso(tenant) == ESTADO_ACTIVO


def mensaje_para_estado(estado: str) -> str:
    if estado == ESTADO_SUSPENDIDO:
        return (
            "Su institución fue suspendida por el administrador de la plataforma. "
            "Puede consultar su información, pero no crear, editar ni emitir nada "
            "hasta que se reactive."
        )
    if estado == ESTADO_CONGELADO:
        return (
            "La licencia de su institución venció. Puede consultar todo su "
            "historial, pero no podrá crear, editar ni emitir nada hasta renovar. "
            "Contacte al administrador de la plataforma para renovar su licencia."
        )
    return ""

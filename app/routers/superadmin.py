import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificado, Tenant, Usuario
from app.schemas import (
    SuperadminResetPassword,
    SuperadminTenantCreate,
    SuperadminTenantDetalle,
    SuperadminTenantOut,
    SuperadminTenantSuscripcion,
    SuperadminUsuarioCreate,
    SuperadminUsuarioEstado,
    SuperadminUsuarioOut,
)
from app.security import hash_password, require_superadmin

router = APIRouter(
    prefix="/api/superadmin",
    tags=["superadmin"],
    dependencies=[Depends(require_superadmin)],
)


def _slugify(texto: str) -> str:
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\s-]", "", texto)
    return re.sub(r"[-\s]+", "-", texto)


def _generar_slug_unico(db: Session, nombre: str, slug_propuesto: Optional[str]) -> str:
    base = _slugify(slug_propuesto or nombre)
    if not base:
        base = "institucion"
    slug = base
    contador = 2
    while db.query(Tenant).filter(Tenant.slug == slug).first():
        slug = f"{base}-{contador}"
        contador += 1
    return slug


def _verificar_username_email_libres(db: Session, username: str, email: str) -> None:
    existente = (
        db.query(Usuario)
        .filter((Usuario.username == username) | (Usuario.email == email))
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese username o correo en la plataforma",
        )


# ===================== TENANTS =====================
@router.get("/tenants", response_model=List[SuperadminTenantOut])
def listar_tenants(db: Session = Depends(get_db)):
    conteos = dict(
        db.query(Usuario.tenant_id, func.count(Usuario.id))
        .group_by(Usuario.tenant_id)
        .all()
    )
    tenants = db.query(Tenant).order_by(Tenant.creado_en.desc()).all()
    resultado = []
    for t in tenants:
        item = SuperadminTenantOut.model_validate(t)
        item.total_usuarios = conteos.get(t.id, 0)
        resultado.append(item)
    return resultado


@router.get("/tenants/{tenant_id}", response_model=SuperadminTenantDetalle)
def obtener_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institución no encontrada")
    usuarios = (
        db.query(Usuario)
        .filter(Usuario.tenant_id == tenant_id)
        .order_by(Usuario.creado_en.asc())
        .all()
    )
    detalle = SuperadminTenantDetalle.model_validate(tenant)
    detalle.usuarios = [SuperadminUsuarioOut.model_validate(u) for u in usuarios]
    detalle.total_usuarios = len(usuarios)
    return detalle


@router.post("/tenants", response_model=SuperadminTenantDetalle, status_code=status.HTTP_201_CREATED)
def crear_tenant(datos: SuperadminTenantCreate, db: Session = Depends(get_db)):
    """
    Alta manual completa: crea la institución (tenant) y su primer usuario
    administrador en una sola operación. Reemplaza a los scripts de consola
    create_admin.py / create_admin2.py.
    """
    _verificar_username_email_libres(db, datos.username, datos.email)

    slug = _generar_slug_unico(db, datos.nombre_institucion, datos.slug)

    tenant = Tenant(
        nombre=datos.nombre_institucion,
        slug=slug,
        activo=True,
        plan=datos.plan,
        fecha_vencimiento=datos.fecha_vencimiento,
        notas_pago=datos.notas_pago,
        estatus_suscripcion="activo",
        puede_emitir_certificados=True,
    )
    db.add(tenant)
    db.flush()  # obtiene tenant.id sin cerrar la transacción

    admin = Usuario(
        tenant_id=tenant.id,
        username=datos.username,
        email=datos.email,
        nombre_completo=datos.nombre_completo,
        password_hash=hash_password(datos.password),
        rol="admin",
        activo=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(tenant)
    db.refresh(admin)

    detalle = SuperadminTenantDetalle.model_validate(tenant)
    detalle.usuarios = [SuperadminUsuarioOut.model_validate(admin)]
    detalle.total_usuarios = 1
    return detalle


@router.patch("/tenants/{tenant_id}/suscripcion", response_model=SuperadminTenantOut)
def actualizar_suscripcion(
    tenant_id: int,
    datos: SuperadminTenantSuscripcion,
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institución no encontrada")

    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(tenant, campo, valor)

    db.commit()
    db.refresh(tenant)

    total_usuarios = db.query(func.count(Usuario.id)).filter(Usuario.tenant_id == tenant_id).scalar() or 0
    resultado = SuperadminTenantOut.model_validate(tenant)
    resultado.total_usuarios = total_usuarios
    return resultado


# ===================== USUARIOS =====================
@router.get("/usuarios", response_model=List[SuperadminUsuarioOut])
def listar_usuarios(tenant_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Usuario).filter(Usuario.rol != "superadmin")
    if tenant_id is not None:
        query = query.filter(Usuario.tenant_id == tenant_id)
    return query.order_by(Usuario.creado_en.desc()).all()


@router.post("/usuarios", response_model=SuperadminUsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario_en_tenant(datos: SuperadminUsuarioCreate, db: Session = Depends(get_db)):
    """Da de alta un usuario adicional (admin o capturista) dentro de un tenant ya existente."""
    tenant = db.query(Tenant).filter(Tenant.id == datos.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institución no encontrada")

    _verificar_username_email_libres(db, datos.username, datos.email)

    usuario = Usuario(
        tenant_id=datos.tenant_id,
        username=datos.username,
        email=datos.email,
        nombre_completo=datos.nombre_completo,
        password_hash=hash_password(datos.password),
        rol=datos.rol,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/usuarios/{usuario_id}/reset-password", response_model=SuperadminUsuarioOut)
def resetear_password(
    usuario_id: int,
    datos: SuperadminResetPassword,
    db: Session = Depends(get_db),
):
    usuario = (
        db.query(Usuario)
        .filter(Usuario.id == usuario_id, Usuario.rol != "superadmin")
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    usuario.password_hash = hash_password(datos.password)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/usuarios/{usuario_id}/estado", response_model=SuperadminUsuarioOut)
def cambiar_estado_usuario(
    usuario_id: int,
    datos: SuperadminUsuarioEstado,
    db: Session = Depends(get_db),
):
    usuario = (
        db.query(Usuario)
        .filter(Usuario.id == usuario_id, Usuario.rol != "superadmin")
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    usuario.activo = datos.activo
    db.commit()
    db.refresh(usuario)
    return usuario


# ===================== MÉTRICAS RÁPIDAS =====================
@router.get("/resumen")
def resumen_plataforma(db: Session = Depends(get_db)):
    total_tenants = db.query(func.count(Tenant.id)).scalar() or 0
    tenants_activos = (
        db.query(func.count(Tenant.id)).filter(Tenant.estatus_suscripcion == "activo").scalar() or 0
    )
    total_usuarios = db.query(func.count(Usuario.id)).filter(Usuario.rol != "superadmin").scalar() or 0
    total_certificados = db.query(func.count(Certificado.id)).scalar() or 0
    return {
        "total_tenants": total_tenants,
        "tenants_activos": tenants_activos,
        "total_usuarios": total_usuarios,
        "total_certificados": total_certificados,
    }

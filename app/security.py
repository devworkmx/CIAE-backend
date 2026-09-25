from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import Usuario
from app.subscription import ESTADO_ACTIVO, calcular_estado_acceso, mensaje_para_estado

# Configuración de hashing con bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 480)
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=getattr(settings, "ALGORITHM", "HS256"),
    )
    return encoded_jwt


def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[Usuario]:
    user = (
        db.query(Usuario)
        .options(joinedload(Usuario.tenant))
        .filter(
            (Usuario.username == username_or_email)
            | (Usuario.email == username_or_email)
        )
        .first()
    )

    if not user:
        return None

    hash_almacenado = getattr(user, "password_hash", getattr(user, "hashed_password", None))
    if not hash_almacenado or not verify_password(password, hash_almacenado):
        return None

    if not user.activo:
        return None

    return user


def get_current_user(
    ciae_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Lee el JWT desde la cookie httpOnly 'ciae_token'.
    Carga de forma explícita la relación con Tenant para que el frontend
    pueda conocer la institución del usuario autenticado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales de acceso",
    )

    if not ciae_token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            ciae_token,
            settings.SECRET_KEY,
            algorithms=[getattr(settings, "ALGORITHM", "HS256")],
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = (
        db.query(Usuario)
        .options(joinedload(Usuario.tenant))
        .filter(Usuario.username == username)
        .first()
    )
    if user is None or not user.activo:
        raise credentials_exception

    return user


def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Protección para acciones administrativas sensibles dentro de un tenant.
    Un superadmin no gestiona cursos/alumnos/certificados de un tenant, así
    que esta dependencia sigue exigiendo específicamente el rol "admin".
    """
    if getattr(current_user, "rol", "capturista") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere permisos de administrador",
        )
    return current_user


def require_superadmin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Protección exclusiva para el panel de superadministrador de la plataforma
    (gestión de tenants, suscripciones y reseteo de contraseñas).
    """
    if getattr(current_user, "rol", None) != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere permisos de superadministrador",
        )
    return current_user


def _verificar_tenant_con_acceso_completo(tenant) -> None:
    """
    Punto único de verificación de "¿este tenant puede escribir datos ahora?".
    Combina el estatus manual que fija el superadmin con la vigencia pagada
    (ver app/subscription.py). Se usa en TODAS las rutas que crean, editan,
    eliminan o emiten algo, para que un tenant congelado o suspendido pueda
    seguir consultando su información (GET) pero nunca modificarla.
    """
    estado = calcular_estado_acceso(tenant)
    if estado != ESTADO_ACTIVO or (tenant is not None and not tenant.puede_emitir_certificados):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "SUSCRIPCION_INACTIVA",
                "estado": estado,
                "mensaje": mensaje_para_estado(estado)
                or (
                    "Su institución no tiene una suscripción activa para "
                    "realizar esta acción. Contacte al administrador de la "
                    "plataforma para renovar su licencia."
                ),
            },
        )


def require_suscripcion_activa(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Protección de escritura para cualquier usuario autenticado (admin o
    capturista) cuyo tenant esté congelado/suspendido/sin permiso de emisión.
    Las lecturas (GET) nunca pasan por aquí: un tenant congelado siempre
    puede seguir viendo todo su historial.
    """
    _verificar_tenant_con_acceso_completo(current_user.tenant)
    return current_user


def require_admin_activo(current_admin: Usuario = Depends(require_admin)) -> Usuario:
    """Igual que require_suscripcion_activa, pero además exige rol admin."""
    _verificar_tenant_con_acceso_completo(current_admin.tenant)
    return current_admin

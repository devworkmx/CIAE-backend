from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import Usuario

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


def require_suscripcion_activa(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Bloquea acciones que consumen la suscripción (hoy: emitir certificados)
    si el tenant fue suspendido/cancelado o si el superadmin le retiró
    específicamente el permiso de emisión (por ejemplo, mientras confirma un pago).
    """
    tenant = current_user.tenant
    if tenant is None or not tenant.puede_emitir_certificados or tenant.estatus_suscripcion != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Su institución no tiene una suscripción activa para emitir "
                "certificados. Contacte al administrador de la plataforma."
            ),
        )
    return current_user

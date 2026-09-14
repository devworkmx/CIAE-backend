from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

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
        .filter(
            (Usuario.username == username_or_email)
            | (Usuario.email == username_or_email)
        )
        .first()
    )

    if not user:
        return None

    # Lee 'password_hash' definido en app/models.py con fallback por seguridad
    hash_almacenado = getattr(user, "password_hash", getattr(user, "hashed_password", None))
    if not hash_almacenado or not verify_password(password, hash_almacenado):
        return None

    # La cuenta inactiva se trata igual que credenciales inválidas de cara al
    # cliente: así la API nunca revela (a quien la llame directamente, sin
    # pasar por el frontend) si una cuenta existe pero está desactivada.
    if not user.activo:
        return None

    return user


def get_current_user(
    ciae_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Lee el JWT desde la cookie httpOnly 'ciae_token' (no desde el header
    Authorization). El navegador la envía automáticamente en cada petición
    al backend; JavaScript nunca puede leerla ni un XSS puede robarla.
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

    user = db.query(Usuario).filter(Usuario.username == username).first()
    if user is None or not user.activo:
        raise credentials_exception

    return user


def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Dependencia para proteger operaciones destructivas o sensibles
    (eliminar alumnos/cursos/certificados, cambiar estado de alumnos, etc.).
    Solo usuarios con rol "admin" pueden pasar este check.

    NOTA DE SEGURIDAD (fail-closed): el valor por defecto de getattr() aquí
    es "capturista" (un rol SIN privilegios), no "admin". Si por cualquier
    motivo el atributo `rol` no estuviera disponible en el objeto Usuario
    (por ejemplo, un objeto parcialmente cargado o un error de mapeo), el
    resultado debe ser NEGAR el acceso, nunca concederlo por accidente.
    Un default inseguro aquí sería un "fail-open": el sistema fallaría
    permitiendo justo la acción que se supone debe restringir.
    """
    if getattr(current_user, "rol", "capturista") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere permisos de administrador",
        )
    return current_user

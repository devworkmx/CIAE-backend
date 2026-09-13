from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.rate_limit import limiter
from app.schemas import LoginResponse, UsuarioActualResponse
from app.security import authenticate_user, create_access_token, get_current_user
from app.models import Usuario

router = APIRouter(prefix="/api/auth", tags=["autenticación"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Mensaje único y genérico a propósito: no distingue entre usuario
        # inexistente, contraseña incorrecta, o cuenta desactivada. Evita
        # que alguien que llame a la API directamente (sin pasar por el
        # frontend) pueda enumerar cuentas válidas o su estado.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    minutos_expiracion = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 480)
    access_token_expires = timedelta(minutes=minutos_expiracion)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # El JWT se entrega como cookie httpOnly: el navegador la guarda y la
    # reenvía sola en cada petición al backend, pero JavaScript nunca puede
    # leerla (mitiga robo de sesión por XSS). "secure" exige HTTPS real en
    # producción; "samesite=lax" evita que se envíe en peticiones de
    # terceros (mitiga CSRF básico) sin romper la navegación normal.
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=minutos_expiracion * 60,
        path="/",
    )

    return LoginResponse(
        username=user.username,
        nombre_completo=user.nombre_completo,
    )


@router.post("/logout")
def logout(response: Response):
    """Borra la cookie de sesión en el navegador. El backend no necesita
    invalidar el JWT en sí (expira solo), solo dejar de reenviarlo."""
    response.delete_cookie(key=settings.COOKIE_NAME, path="/")
    return {"detail": "Sesión cerrada correctamente"}


@router.get("/me", response_model=UsuarioActualResponse)
def obtener_usuario_actual(usuario_actual: Usuario = Depends(get_current_user)):
    """
    Le permite al frontend confirmar si hay una sesión activa y válida,
    sin poder leer la cookie httpOnly directamente desde JavaScript.
    """
    return usuario_actual

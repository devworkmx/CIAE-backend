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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    minutos_expiracion = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 480)
    access_token_expires = timedelta(minutes=minutos_expiracion)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

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
    """Borra la cookie de sesión en el navegador."""
    response.delete_cookie(key=settings.COOKIE_NAME, path="/")
    return {"detail": "Sesión cerrada correctamente"}


@router.get("/me", response_model=UsuarioActualResponse)
def obtener_usuario_actual(usuario_actual: Usuario = Depends(get_current_user)):
    """
    Devuelve los datos del usuario logueado y su tenant asociado.
    Construye el tenant explícitamente para garantizar que viaje en el JSON.
    """
    tenant_dict = None
    if usuario_actual.tenant:
        tenant_dict = {
            "id": usuario_actual.tenant.id,
            "nombre": usuario_actual.tenant.nombre,
            "slug": usuario_actual.tenant.slug,
            "activo": usuario_actual.tenant.activo,
            "creado_en": usuario_actual.tenant.creado_en,
            "estatus_suscripcion": usuario_actual.tenant.estatus_suscripcion,
            "plan": usuario_actual.tenant.plan,
            "fecha_vencimiento": usuario_actual.tenant.fecha_vencimiento,
            "notas_pago": usuario_actual.tenant.notas_pago,
            "puede_emitir_certificados": usuario_actual.tenant.puede_emitir_certificados,
            # Estado efectivo (activo/congelado/suspendido) + días restantes:
            # el frontend del panel admin usa esto para mostrar el plan/
            # vigencia y para congelar la UI sin tener que recalcular fechas.
            "estado_acceso": usuario_actual.tenant.estado_acceso,
            "dias_restantes": usuario_actual.tenant.dias_restantes,
        }

    return UsuarioActualResponse(
        username=usuario_actual.username,
        nombre_completo=usuario_actual.nombre_completo,
        email=usuario_actual.email,
        rol=usuario_actual.rol,
        tenant_id=usuario_actual.tenant_id,
        tenant=tenant_dict,
    )

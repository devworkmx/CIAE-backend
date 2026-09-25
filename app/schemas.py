from datetime import date, datetime
from typing import List, Optional
import re
from pydantic import BaseModel, EmailStr, Field, field_validator


CURP_REGEX = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])"
    r"[HM](AS|BC|BS|CC|CS|CH|CL|CM|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|"
    r"QO|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d$"
)


def _validar_password(valor: str) -> str:
    if not re.search(r"[a-z]", valor):
        raise ValueError("La contraseña debe incluir al menos una letra minúscula")
    if not re.search(r"[A-Z]", valor):
        raise ValueError("La contraseña debe incluir al menos una letra mayúscula")
    if not re.search(r"\d", valor):
        raise ValueError("La contraseña debe incluir al menos un número")
    return valor


def validar_formato_curp(valor: str) -> str:
    valor_normalizado = valor.strip().upper()
    if not CURP_REGEX.match(valor_normalizado):
        raise ValueError(
            "CURP inválida. Debe tener 18 caracteres con el formato oficial "
            "(ej. PEGC900101HDFRNR09)."
        )
    return valor_normalizado


# ===================== TENANTS =====================
ESTADOS_SUSCRIPCION_VALIDOS = {"activo", "suspendido", "cancelado"}


class TenantBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    slug: str = Field(..., min_length=2, max_length=60)


class TenantOut(TenantBase):
    id: int
    activo: bool
    creado_en: datetime
    estatus_suscripcion: str
    plan: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    notas_pago: Optional[str] = None
    puede_emitir_certificados: bool
    # Estado EFECTIVO de acceso ("activo" | "congelado" | "suspendido"),
    # ya combina estatus_suscripcion + fecha_vencimiento. El frontend debe
    # confiar en este campo en vez de recalcular la lógica de vigencia.
    estado_acceso: str
    dias_restantes: Optional[int] = None

    class Config:
        from_attributes = True


# ===================== SUPERADMIN =====================
class SuperadminTenantCreate(BaseModel):
    """Alta manual de una institución nueva junto con su primer usuario admin."""

    nombre_institucion: str = Field(..., min_length=2, max_length=150)
    slug: Optional[str] = Field(None, min_length=2, max_length=60)
    plan: Optional[str] = Field(None, max_length=50)
    fecha_vencimiento: Optional[date] = None
    notas_pago: Optional[str] = None

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    nombre_completo: str = Field(..., min_length=2, max_length=150)
    password: str = Field(..., min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def validar_complejidad_password(cls, valor: str) -> str:
        return _validar_password(valor)


class SuperadminUsuarioCreate(BaseModel):
    """Alta manual de un usuario adicional dentro de un tenant existente."""

    tenant_id: int
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    nombre_completo: str = Field(..., min_length=2, max_length=150)
    rol: str = Field("admin", pattern="^(admin|capturista)$")
    password: str = Field(..., min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def validar_complejidad_password(cls, valor: str) -> str:
        return _validar_password(valor)


class SuperadminResetPassword(BaseModel):
    password: str = Field(..., min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def validar_complejidad_password(cls, valor: str) -> str:
        return _validar_password(valor)


class SuperadminUsuarioEstado(BaseModel):
    activo: bool


class SuperadminTenantRenovacion(BaseModel):
    """
    Renovación rápida: en vez de que el superadmin calcule a mano la nueva
    fecha de vencimiento, indica cuántos meses pagó el cliente y el backend
    hace la suma correcta (si aún le quedaba tiempo, se lo respeta y suma
    encima; si ya estaba vencido, cuenta a partir de hoy).
    """

    meses: int = Field(..., gt=0, le=36)
    plan: Optional[str] = Field(None, max_length=50)
    nota_pago: Optional[str] = Field(None, max_length=500)


class SuperadminTenantSuscripcion(BaseModel):
    estatus_suscripcion: Optional[str] = None
    plan: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    notas_pago: Optional[str] = None
    puede_emitir_certificados: Optional[bool] = None
    activo: Optional[bool] = None

    @field_validator("estatus_suscripcion")
    @classmethod
    def validar_estatus(cls, valor: Optional[str]) -> Optional[str]:
        if valor is not None and valor not in ESTADOS_SUSCRIPCION_VALIDOS:
            raise ValueError(
                f"Estatus inválido. Debe ser uno de: {', '.join(sorted(ESTADOS_SUSCRIPCION_VALIDOS))}"
            )
        return valor


class SuperadminUsuarioOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    nombre_completo: str
    rol: str
    activo: bool
    tenant_id: Optional[int] = None
    creado_en: datetime

    class Config:
        from_attributes = True


class SuperadminTenantOut(TenantOut):
    total_usuarios: int = 0


class SuperadminTenantDetalle(SuperadminTenantOut):
    usuarios: List[SuperadminUsuarioOut] = []


# ===================== AUTENTICACIÓN =====================
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    username: Optional[str] = ""
    nombre_completo: Optional[str] = ""


class UsuarioActualResponse(BaseModel):
    username: str
    nombre_completo: str
    email: EmailStr
    rol: str
    tenant_id: Optional[int] = None
    tenant: Optional[TenantOut] = None

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    username: Optional[str] = None


class UsuarioBase(BaseModel):
    username: str
    email: EmailStr
    nombre_completo: str
    activo: bool = True
    rol: Optional[str] = "admin"


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def validar_complejidad_password(cls, valor: str) -> str:
        return _validar_password(valor)


class UsuarioOut(UsuarioBase):
    id: int
    tenant_id: Optional[int] = None
    creado_en: datetime

    class Config:
        from_attributes = True


# ===================== CURSOS =====================
class CursoBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=200)
    duracion_horas: int = Field(..., gt=0)
    clave_curso: Optional[str] = None
    tiene_vigencia: bool = False
    meses_vigencia: Optional[int] = None


class CursoCreate(CursoBase):
    pass


class CursoUpdate(BaseModel):
    nombre: Optional[str] = None
    duracion_horas: Optional[int] = None
    clave_curso: Optional[str] = None
    tiene_vigencia: Optional[bool] = None
    meses_vigencia: Optional[int] = None


class CursoOut(CursoBase):
    id: int
    creado_en: datetime

    class Config:
        from_attributes = True


# ===================== ALUMNOS =====================
class AlumnoBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    apellidos: str = Field(..., min_length=2, max_length=100)
    curp: str = Field(..., min_length=18, max_length=18)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    activo: bool = True


class AlumnoCreate(AlumnoBase):
    @field_validator("curp")
    @classmethod
    def validar_curp(cls, valor: str) -> str:
        return validar_formato_curp(valor)


class AlumnoUpdate(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    curp: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    activo: Optional[bool] = None

    @field_validator("curp")
    @classmethod
    def validar_curp_opcional(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return valor
        return validar_formato_curp(valor)


class AlumnoToggleEstadoRequest(BaseModel):
    activo: bool
    admin_password: str


class AlumnoOut(AlumnoBase):
    id: int
    creado_en: datetime

    class Config:
        from_attributes = True


# ===================== CERTIFICADOS =====================
class CertificadoCreate(BaseModel):
    folio_manual: str = Field(..., min_length=3, max_length=50)
    curso_id: int
    alumno_id: int
    fecha_emision: Optional[date] = None
    tiene_vigencia: bool = False
    fecha_vigencia: Optional[date] = None
    instructor: str = Field(..., min_length=3, max_length=150)
    calificacion: Optional[str] = "100"


class CertificadoUpdate(BaseModel):
    folio_manual: Optional[str] = None
    curso_id: Optional[int] = None
    alumno_id: Optional[int] = None
    instructor: Optional[str] = None
    fecha_emision: Optional[date] = None
    tiene_vigencia: Optional[bool] = None
    fecha_vigencia: Optional[date] = None
    calificacion: Optional[str] = None


class CertificadoUpdateEstatus(BaseModel):
    estatus: str


class CertificadoOut(BaseModel):
    id: int
    folio_manual: str
    token_publico: str
    curso_id: int
    alumno_id: int
    alumno_nombre: str
    curso_nombre: str
    fecha_emision: date
    tiene_vigencia: bool
    fecha_vigencia: Optional[date]
    instructor: str
    calificacion: Optional[str]
    estatus: str
    creado_en: datetime

    class Config:
        from_attributes = True


# ===================== RESPUESTA PÚBLICA =====================
class ValidacionPublicaResponse(BaseModel):
    valido: bool
    folio: Optional[str] = None
    institucion: Optional[str] = None
    alumno_nombre: Optional[str] = None
    curso_nombre: Optional[str] = None
    duracion_horas: Optional[int] = None
    fecha_emision: Optional[date] = None
    tiene_vigencia: bool = False
    fecha_vigencia: Optional[date] = None
    vigente: bool = True
    instructor: Optional[str] = None
    estatus: Optional[str] = None
    alumno_activo: bool = True
    motivo_invalidez: Optional[str] = None
    token_publico: Optional[str] = None

    class Config:
        from_attributes = True


class AlumnoPublicoResumen(BaseModel):
    nombre: str
    curp: str
    activo: bool


class BusquedaPublicaResponse(BaseModel):
    tipo_consulta: str
    alumno: Optional[AlumnoPublicoResumen] = None
    certificados: List[ValidacionPublicaResponse]

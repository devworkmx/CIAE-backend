from datetime import date, datetime
from typing import List, Optional
import re
from pydantic import BaseModel, EmailStr, Field, field_validator


# Formato oficial de CURP: 4 letras + 6 dígitos (fecha) + H/M + 5 letras
# (estado + consonantes internas) + 2 alfanuméricos + 1 dígito verificador.
CURP_REGEX = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])"
    r"[HM](AS|BC|BS|CC|CS|CH|CL|CM|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|"
    r"QO|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d$"
)


def validar_formato_curp(valor: str) -> str:
    """Normaliza y valida el formato oficial de una CURP. Lanza ValueError si no cumple."""
    valor_normalizado = valor.strip().upper()
    if not CURP_REGEX.match(valor_normalizado):
        raise ValueError(
            "CURP inválida. Debe tener 18 caracteres con el formato oficial "
            "(ej. PEGC900101HDFRNR09)."
        )
    return valor_normalizado


# ===================== AUTENTICACIÓN =====================
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    # El JWT ya NO viaja en el cuerpo de la respuesta: el backend lo entrega
    # como cookie httpOnly (ver /api/auth/login), así JavaScript nunca puede
    # leerlo directamente. Aquí solo va información no sensible para la UI.
    username: Optional[str] = ""
    nombre_completo: Optional[str] = ""


class UsuarioActualResponse(BaseModel):
    username: str
    nombre_completo: str
    email: EmailStr

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    username: Optional[str] = None


class UsuarioBase(BaseModel):
    username: str
    email: EmailStr
    nombre_completo: str
    activo: bool = True


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def validar_complejidad_password(cls, valor: str) -> str:
        if not re.search(r"[a-z]", valor):
            raise ValueError("La contraseña debe incluir al menos una letra minúscula")
        if not re.search(r"[A-Z]", valor):
            raise ValueError("La contraseña debe incluir al menos una letra mayúscula")
        if not re.search(r"\d", valor):
            raise ValueError("La contraseña debe incluir al menos un número")
        return valor


class UsuarioOut(UsuarioBase):
    id: int
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
    # OJO: esta clase también es la base de AlumnoOut (lo que se LEE/lista).
    # El validador de formato de CURP va solo en AlumnoCreate/AlumnoUpdate
    # (lo que se ESCRIBE), para no romper la lectura de registros ya
    # existentes que se hayan guardado antes de agregar esta validación.
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
    estatus: Optional[str] = None


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
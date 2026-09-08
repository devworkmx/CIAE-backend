from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models import EstatusCertificado


# ---------------------------------------------------------------------------
# AUTENTICACIÓN Y USUARIOS
# ---------------------------------------------------------------------------

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    nombre_completo: str


class UsuarioBase(BaseModel):
    username: str
    email: EmailStr
    nombre_completo: str
    activo: bool = True


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioOut(UsuarioBase):
    id: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# CURSOS
# ---------------------------------------------------------------------------

class CursoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    clave_curso: Optional[str] = None
    duracion_horas: int
    instructor: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None


class CursoCreate(CursoBase):
    pass


class CursoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    clave_curso: Optional[str] = None
    duracion_horas: Optional[int] = None
    instructor: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None


class CursoOut(CursoBase):
    id: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# ALUMNOS
# ---------------------------------------------------------------------------

class AlumnoBase(BaseModel):
    nombre: str
    apellidos: str
    curp: str
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None


class AlumnoCreate(AlumnoBase):
    pass


class AlumnoUpdate(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    curp: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None


class AlumnoOut(AlumnoBase):
    id: int
    nombre_completo: str
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# CERTIFICADOS
# ---------------------------------------------------------------------------

class CertificadoCreate(BaseModel):
    alumno_id: int
    curso_id: int
    fecha_emision: Optional[date] = None
    fecha_vigencia: Optional[date] = None
    calificacion: Optional[str] = None
    folio_impreso: Optional[str] = None


class CertificadoUpdateEstatus(BaseModel):
    estatus: EstatusCertificado


class CertificadoOut(BaseModel):
    id: int
    token_publico: str
    alumno_id: int
    curso_id: int
    alumno_nombre: str
    estatus: EstatusCertificado
    fecha_emision: date
    fecha_vigencia: Optional[date] = None
    calificacion: Optional[str] = None
    folio_impreso: Optional[str] = None
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# VALIDACIÓN PÚBLICA (QR)
# ---------------------------------------------------------------------------

class ValidacionPublicaOut(BaseModel):
    valido: bool
    estatus: Optional[str] = None
    mensaje: Optional[str] = None
    alumno_nombre: Optional[str] = None
    curso_nombre: Optional[str] = None
    duracion_horas: Optional[int] = None
    fecha_emision: Optional[date] = None
    fecha_vigencia: Optional[date] = None

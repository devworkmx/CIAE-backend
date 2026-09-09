from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ===================== AUTENTICACIÓN =====================
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: Optional[str] = ""
    nombre_completo: Optional[str] = ""


class TokenData(BaseModel):
    username: Optional[str] = None


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

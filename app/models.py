import enum
import secrets
from datetime import date, datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
    Enum,
    Text,
    Boolean,
)
from sqlalchemy.orm import relationship
from app.database import Base


def generar_token_seguro() -> str:
    # 32 bytes en urlsafe producen 43 caracteres alfanuméricos imposibles de adivinar
    return secrets.token_urlsafe(32)


class EstatusCertificado(str, enum.Enum):
    vigente = "vigente"
    expirado = "expirado"
    revocado = "revocado"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    nombre_completo = Column(String(150), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    certificados_creados = relationship("Certificado", back_populates="creado_por")


class Curso(Base):
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    clave_curso = Column(String(50), unique=True, nullable=True)  # Ej. "SEG-2026-A"
    duracion_horas = Column(Integer, nullable=False)
    instructor = Column(String(150), nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    certificados = relationship(
        "Certificado", back_populates="curso", cascade="all, delete-orphan"
    )


class Alumno(Base):
    __tablename__ = "alumnos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellidos = Column(String(150), nullable=False)
    curp = Column(String(18), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True)
    telefono = Column(String(20), nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    certificados = relationship(
        "Certificado", back_populates="alumno", cascade="all, delete-orphan"
    )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}".strip()


class Certificado(Base):
    __tablename__ = "certificados"

    id = Column(Integer, primary_key=True, index=True)

    # Token seguro no correlativo para la URL pública del QR
    token_publico = Column(
        String(64),
        default=generar_token_seguro,
        unique=True,
        index=True,
        nullable=False,
    )

    # Claves foráneas internas
    alumno_id = Column(
        Integer, ForeignKey("alumnos.id", ondelete="CASCADE"), nullable=False
    )
    curso_id = Column(
        Integer, ForeignKey("cursos.id", ondelete="CASCADE"), nullable=False
    )
    creado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    # Metadatos del certificado
    estatus = Column(
        Enum(EstatusCertificado), default=EstatusCertificado.vigente, nullable=False
    )
    fecha_emision = Column(Date, default=date.today, nullable=False)
    fecha_vigencia = Column(Date, nullable=True)
    calificacion = Column(String(10), nullable=True)
    folio_impreso = Column(String(50), nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    # Relaciones ORM
    alumno = relationship("Alumno", back_populates="certificados")
    curso = relationship("Curso", back_populates="certificados")
    creado_por = relationship("Usuario", back_populates="certificados_creados")

    @property
    def alumno_nombre(self) -> str:
        return self.alumno.nombre_completo if self.alumno else ""

import secrets
from datetime import date, datetime
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre_completo = Column(String(150), nullable=False)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    # Alias de compatibilidad para evitar AttributeError
    @property
    def hashed_password(self) -> str:
        return self.password_hash

    @hashed_password.setter
    def hashed_password(self, value: str) -> None:
        self.password_hash = value


class Curso(Base):
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    duracion_horas = Column(Integer, nullable=False)
    clave_curso = Column(String(50), nullable=True)
    tiene_vigencia = Column(Boolean, default=False)
    meses_vigencia = Column(Integer, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    certificados = relationship("Certificado", back_populates="curso")


class Alumno(Base):
    __tablename__ = "alumnos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    curp = Column(String(18), unique=True, index=True, nullable=False)
    email = Column(String(100), nullable=True)
    telefono = Column(String(20), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    certificados = relationship("Certificado", back_populates="alumno")


class Certificado(Base):
    __tablename__ = "certificados"

    id = Column(Integer, primary_key=True, index=True)
    folio_manual = Column(String(50), unique=True, index=True, nullable=False)
    token_publico = Column(
        String(64),
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(32),
        nullable=False,
    )
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=False)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"), nullable=False)
    creado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    fecha_emision = Column(Date, default=date.today, nullable=False)
    tiene_vigencia = Column(Boolean, default=False)
    fecha_vigencia = Column(Date, nullable=True)
    instructor = Column(String(150), nullable=False)
    calificacion = Column(String(10), nullable=True)
    estatus = Column(String(20), default="vigente")  # vigente, expirado, revocado
    creado_en = Column(DateTime, default=datetime.utcnow)

    curso = relationship("Curso", back_populates="certificados")
    alumno = relationship("Alumno", back_populates="certificados")

    @property
    def alumno_nombre(self) -> str:
        return f"{self.alumno.nombre} {self.alumno.apellidos}" if self.alumno else ""

    @property
    def curso_nombre(self) -> str:
        return self.curso.nombre if self.curso else ""

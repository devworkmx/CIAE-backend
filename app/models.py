import secrets
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.subscription import calcular_estado_acceso, dias_restantes as _dias_restantes

# Estados posibles de la suscripción de un tenant (fase 1: manejo manual por el superadmin)
ESTADOS_SUSCRIPCION = ("activo", "suspendido", "cancelado")


class Tenant(Base):
    """Representa a cada cliente, institución, escuela o academia."""
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    slug = Column(String(60), unique=True, index=True, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    # ---- Suscripción (gestionada manualmente por el superadmin en fase 1) ----
    estatus_suscripcion = Column(String(20), default="activo", nullable=False)
    plan = Column(String(50), nullable=True)
    fecha_vencimiento = Column(Date, nullable=True)
    notas_pago = Column(Text, nullable=True)
    # Permite separar "el tenant existe y puede entrar" de "puede emitir certificados".
    # Útil hoy para congelar la emisión sin bloquear el acceso, y en fase 2 para
    # bloquear la emisión a tenants que se auto-registren sin haber pagado aún.
    puede_emitir_certificados = Column(Boolean, default=True, nullable=False)

    usuarios = relationship("Usuario", back_populates="tenant", cascade="all, delete-orphan")
    cursos = relationship("Curso", back_populates="tenant", cascade="all, delete-orphan")
    alumnos = relationship("Alumno", back_populates="tenant", cascade="all, delete-orphan")
    certificados = relationship("Certificado", back_populates="tenant", cascade="all, delete-orphan")

    @property
    def estado_acceso(self) -> str:
        """Estado de acceso EFECTIVO (activo/congelado/suspendido). Ver app/subscription.py."""
        return calcular_estado_acceso(self)

    @property
    def dias_restantes(self) -> Optional[int]:
        """Días para que venza el tiempo pagado (negativo si ya venció)."""
        return _dias_restantes(self)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    # Nullable porque el superadmin de la plataforma no pertenece a ningún tenant.
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre_completo = Column(String(150), nullable=False)
    activo = Column(Boolean, default=True)
    rol = Column(String(20), nullable=False, default="admin")
    creado_en = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="usuarios")

    @property
    def hashed_password(self) -> str:
        return self.password_hash

    @hashed_password.setter
    def hashed_password(self, value: str) -> None:
        self.password_hash = value


class Curso(Base):
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    duracion_horas = Column(Integer, nullable=False)
    clave_curso = Column(String(50), nullable=True)
    tiene_vigencia = Column(Boolean, default=False)
    meses_vigencia = Column(Integer, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="cursos")
    certificados = relationship("Certificado", back_populates="curso", cascade="all, delete-orphan")


class Alumno(Base):
    __tablename__ = "alumnos"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    curp = Column(String(18), nullable=False, index=True)
    email = Column(String(100), nullable=True)
    telefono = Column(String(20), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    # Restricción única por institución: dos academias diferentes pueden tener al mismo alumno
    __table_args__ = (
        UniqueConstraint("tenant_id", "curp", name="uq_tenant_alumno_curp"),
    )

    tenant = relationship("Tenant", back_populates="alumnos")
    certificados = relationship("Certificado", back_populates="alumno", cascade="all, delete-orphan")


class Certificado(Base):
    __tablename__ = "certificados"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    folio_manual = Column(String(50), nullable=False, index=True)

    # El token público permanece único globalmente para la validación pública por QR
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

    # Restricción única por institución: dos clientes pueden usar folios que comiencen igual (ej. "FOLIO-001")
    __table_args__ = (
        UniqueConstraint("tenant_id", "folio_manual", name="uq_tenant_certificado_folio"),
    )

    tenant = relationship("Tenant", back_populates="certificados")
    curso = relationship("Curso", back_populates="certificados")
    alumno = relationship("Alumno", back_populates="certificados")

    @property
    def alumno_nombre(self) -> str:
        return f"{self.alumno.nombre} {self.alumno.apellidos}" if self.alumno else ""

    @property
    def curso_nombre(self) -> str:
        return self.curso.nombre if self.curso else ""

import sys
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.database import Base, engine, get_db
from app.models import Tenant, Usuario
from app.security import hash_password
from app.schemas import UsuarioCreate
import re

# ==========================================
# CONFIGURA AQUÍ LAS DOS CUENTAS DE ADMIN
# ==========================================
ADMINS_A_CREAR = [
    {
        "username": "josergz",
        "email": "joserdgz.dev@gmail.com",
        "nombre_completo": "Jose de Jesus Rodriguez Angel",
        "password": "adminTI_2026_jose*",  # Asegúrate de cumplir las reglas de Pydantic
    },
    {
        "username": "lanserdiaz",
        "email": "lanser.dev99@gmail.com",
        "nombre_completo": "Lanser Manuel Diaz Mojarra",
        "password": "adminTI_2026_lanser*",
    }
]

def slugify(texto: str) -> str:
    """Convierte texto en slug limpio: 'Academia López 123' -> 'academia-lopez-123'."""
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\s-]", "", texto)
    return re.sub(r"[-\s]+", "-", texto)


def main():
    print("\n=======================================================")
    print("  Creación de Tenant y Doble Administrador (Multi-Tenant) ")
    print("=======================================================\n")

    Base.metadata.create_all(bind=engine)
    db: Session = next(get_db())

    try:
        # 1. GESTIÓN DEL TENANT (INSTITUCIÓN / ESCUELA)
        print("1. Seleccionar o Crear Institución:")
        print("   [1] Crear una NUEVA institución")
        print("   [2] Asignar a una institución EXISTENTE")
        opcion = input("Seleccione opción (1 o 2) [1]: ").strip() or "1"

        tenant_id = None

        if opcion == "2":
            tenants = db.query(Tenant).order_by(Tenant.nombre.asc()).all()
            if not tenants:
                print("\nNo existen instituciones registradas. Debe crear una nueva.")
                opcion = "1"
            else:
                print("\nInstituciones disponibles:")
                for t in tenants:
                    print(f"   [{t.id}] {t.nombre} (slug: {t.slug})")
                tenant_input = input("\nIngrese el ID de la institución: ").strip()
                tenant_existente = db.query(Tenant).filter(Tenant.id == int(tenant_input)).first()
                if not tenant_existente:
                    print(f"Error: La institución con ID {tenant_input} no existe.")
                    sys.exit(1)
                tenant_id = tenant_existente.id
                print(f"-> Asignando a: {tenant_existente.nombre}")

        if opcion == "1":
            nombre_tenant = input("\nNombre de la nueva institución (ej. CIAE Certificaciones): ").strip()
            if not nombre_tenant:
                print("El nombre de la institución es obligatorio.")
                sys.exit(1)

            slug_propuesto = slugify(nombre_tenant)
            slug = input(f"Slug identificador [{slug_propuesto}]: ").strip() or slug_propuesto

            tenant_duplicado = db.query(Tenant).filter(Tenant.slug == slug).first()
            if tenant_duplicado:
                print(f"Error: Ya existe una institución con el slug '{slug}'.")
                sys.exit(1)

            nuevo_tenant = Tenant(nombre=nombre_tenant, slug=slug, activo=True)
            db.add(nuevo_tenant)
            db.commit()
            db.refresh(nuevo_tenant)
            tenant_id = nuevo_tenant.id
            print(f"-> Institución '{nuevo_tenant.nombre}' creada con éxito (ID: {tenant_id}).\n")

        # 2. GESTIÓN AUTOMATIZADA DE LOS ADMINISTRADORES
        print("2. Creando cuentas de Superadministradores...")

        for data in ADMINS_A_CREAR:
            username = data["username"]
            email = data["email"]
            nombre_completo = data["nombre_completo"]
            password = data["password"]

            # Verificar si ya existe
            existente = (
                db.query(Usuario)
                .filter((Usuario.username == username) | (Usuario.email == email))
                .first()
            )
            if existente:
                print(f"-> Aviso: El usuario '{username}' o email '{email}' ya existe en la base de datos. Se omite.")
                continue

            # Validar con Pydantic
            try:
                UsuarioCreate(
                    username=username,
                    email=email,
                    nombre_completo=nombre_completo,
                    password=password,
                )
            except ValidationError as e:
                print(f"\nError de validación para el usuario {username}:")
                for error in e.errors():
                    print(f"  - {error['msg']}")
                sys.exit(1)

            # Crear instancia
            admin = Usuario(
                tenant_id=tenant_id,
                username=username,
                email=email,
                nombre_completo=nombre_completo,
                password_hash=hash_password(password),
                rol="admin",
                activo=True,
            )

            db.add(admin)
            print(f"-> Administrador '{username}' preparado para registro.")

        db.commit()
        print(f"\n ¡Proceso completado! Las cuentas de administrador fueron vinculadas al tenant ID {tenant_id}.")

    except KeyboardInterrupt:
        print("\nOperación cancelada.")
        sys.exit(0)
    except Exception as e:
        db.rollback()
        print(f"\nOcurrió un error inesperado: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

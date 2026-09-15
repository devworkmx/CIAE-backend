import getpass
import re
import sys
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.database import Base, engine, get_db
from app.models import Tenant, Usuario
from app.security import hash_password
from app.schemas import UsuarioCreate


def slugify(texto: str) -> str:
    """Convierte texto en slug limpio: 'Academia López 123' -> 'academia-lopez-123'."""
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\s-]", "", texto)
    return re.sub(r"[-\s]+", "-", texto)


def main():
    print("\n=======================================================")
    print("  Creación de Tenant y Administrador (Multi-Tenant)    ")
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
            nombre_tenant = input("\nNombre de la nueva institución (ej. Instituto Harvard): ").strip()
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

        # 2. GESTIÓN DEL USUARIO ADMINISTRADOR
        print("2. Datos del Usuario Administrador:")
        username = input("Username: ").strip()
        if not username:
            print("El username es obligatorio.")
            sys.exit(1)

        email = input("Email: ").strip()
        if not email:
            print("El email es obligatorio.")
            sys.exit(1)

        nombre_completo = input("Nombre completo: ").strip()
        if not nombre_completo:
            print("El nombre completo es obligatorio.")
            sys.exit(1)

        existente = (
            db.query(Usuario)
            .filter((Usuario.username == username) | (Usuario.email == email))
            .first()
        )
        if existente:
            print(f"Error: Ya existe un usuario con username '{username}' o email '{email}'.")
            sys.exit(1)

        password = getpass.getpass("Password: ")
        confirmar = getpass.getpass("Confirmar password: ")

        if password != confirmar:
            print("Las contraseñas no coinciden.")
            sys.exit(1)

        try:
            UsuarioCreate(
                username=username,
                email=email,
                nombre_completo=nombre_completo,
                password=password,
            )
        except ValidationError as e:
            print("\nLa contraseña o los datos no cumplen los requisitos:")
            for error in e.errors():
                print(f"  - {error['msg']}")
            sys.exit(1)

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
        db.commit()
        db.refresh(admin)

        print(f"\n ¡Éxito! Administrador '{username}' creado y vinculado al tenant ID {tenant_id}.")

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

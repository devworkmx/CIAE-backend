"""
Crea (o valida) la existencia de un usuario con rol "superadmin".
Este script solo se necesita UNA VEZ por entorno (o cuando quieras dar de
alta a otra persona del equipo de la plataforma con este rol). Después de
eso, todo lo demás (dar de alta tenants, resetear contraseñas, gestionar
suscripciones) se hace desde el panel web /superadmin.

Uso:
    python create_superadmin.py
"""
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Usuario
from app.schemas import UsuarioCreate
from app.security import hash_password


def main():
    print("\n=======================================================")
    print("  Creación de Superadministrador de la plataforma CIAE  ")
    print("=======================================================\n")

    Base.metadata.create_all(bind=engine)
    db: Session = next(get_db())

    try:
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

        superadmin = Usuario(
            tenant_id=None,
            username=username,
            email=email,
            nombre_completo=nombre_completo,
            password_hash=hash_password(password),
            rol="superadmin",
            activo=True,
        )

        db.add(superadmin)
        db.commit()

        print(f"\n ¡Éxito! Superadministrador '{username}' creado.")
        print("   Ya puede iniciar sesión en /login y será redirigido a /superadmin.")

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

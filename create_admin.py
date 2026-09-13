import getpass
import sys
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.database import Base, engine, get_db
from app.models import Usuario
from app.security import hash_password
from app.schemas import UsuarioCreate


def main():
    print("=== Creación de Usuario Administrador ===")

    # Asegura que las tablas existan en PostgreSQL
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

        # Verificar si ya existe
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

        # Reutiliza EXACTAMENTE la misma regla de complejidad que usa la API
        # (UsuarioCreate en schemas.py): 10+ caracteres, mayúscula, minúscula y número.
        # Así una cuenta de administrador nunca puede quedar más débil que
        # cualquier cuenta creada normalmente desde el panel.
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

        # Instanciar pasando 'password_hash' tal como está definido en app/models.py
        admin = Usuario(
            username=username,
            email=email,
            nombre_completo=nombre_completo,
            password_hash=hash_password(password),
            activo=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print(f"\n¡Éxito! Usuario admin '{username}' creado correctamente.")

    except Exception as e:
        db.rollback()
        print(f"\nOcurrió un error inesperado al guardar en la base de datos: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

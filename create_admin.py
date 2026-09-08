"""
Script para crear el primer usuario administrador.
Uso:
    python create_admin.py
"""
import getpass
import sys
from app.database import SessionLocal, Base, engine
from app.models import Usuario
from app.security import hash_password

# Crea las tablas si no existen aún en PostgreSQL
Base.metadata.create_all(bind=engine)


def main():
    db = SessionLocal()
    try:
        username = input("Username: ").strip()
        email = input("Email: ").strip()
        nombre_completo = input("Nombre completo: ").strip()

        if not username or not email or not nombre_completo:
            print("Error: El usuario, email y nombre completo no pueden estar vacíos.")
            return

        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirmar password: ")

        if not password:
            print("Error: La contraseña no puede estar vacía.")
            return

        if password != password_confirm:
            print("Error: Las contraseñas no coinciden.")
            return

        # Validar duplicados tanto en username como en email
        if db.query(Usuario).filter(Usuario.username == username).first():
            print(f"Error: El username '{username}' ya está registrado.")
            return

        if db.query(Usuario).filter(Usuario.email == email).first():
            print(f"Error: El correo '{email}' ya está registrado.")
            return

        usuario = Usuario(
            username=username,
            email=email,
            nombre_completo=nombre_completo,
            hashed_password=hash_password(password),
            activo=True,
        )
        db.add(usuario)
        db.commit()
        print(f"\n¡Éxito! Usuario admin '{username}' creado correctamente.")

    except Exception as e:
        db.rollback()
        print(f"\nOcurrió un error inesperado al guardar en la base de datos: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alumno, Usuario
from app.schemas import (
    AlumnoCreate,
    AlumnoOut,
    AlumnoUpdate,
    AlumnoToggleEstadoRequest,
)
from app.security import get_current_user, verify_password

router = APIRouter(
    prefix="/api/alumnos",
    tags=["alumnos"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=List[AlumnoOut])
def listar_alumnos(db: Session = Depends(get_db)):
    return db.query(Alumno).order_by(Alumno.apellidos.asc()).all()


@router.get("/{alumno_id}", response_model=AlumnoOut)
def obtener_alumno(alumno_id: int, db: Session = Depends(get_db)):
    alumno = db.query(Alumno).filter(Alumno.id == alumno_id).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado"
        )
    return alumno


@router.post("", response_model=AlumnoOut, status_code=status.HTTP_201_CREATED)
def crear_alumno(datos: AlumnoCreate, db: Session = Depends(get_db)):
    existente = db.query(Alumno).filter(Alumno.curp == datos.curp.upper()).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un alumno registrado con esta CURP",
        )
    payload = datos.model_dump()
    payload["curp"] = payload["curp"].upper()
    alumno = Alumno(**payload)
    db.add(alumno)
    db.commit()
    db.refresh(alumno)
    return alumno


@router.patch("/{alumno_id}", response_model=AlumnoOut)
def actualizar_alumno(
    alumno_id: int, datos: AlumnoUpdate, db: Session = Depends(get_db)
):
    alumno = db.query(Alumno).filter(Alumno.id == alumno_id).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado"
        )

    update_dict = datos.model_dump(exclude_unset=True)
    if "curp" in update_dict:
        update_dict["curp"] = update_dict["curp"].upper()
        conflicto = (
            db.query(Alumno)
            .filter(Alumno.curp == update_dict["curp"], Alumno.id != alumno_id)
            .first()
        )
        if conflicto:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La CURP ingresada ya pertenece a otro alumno registrado",
            )

    for key, value in update_dict.items():
        setattr(alumno, key, value)
    db.commit()
    db.refresh(alumno)
    return alumno


@router.patch("/{alumno_id}/estado", response_model=AlumnoOut)
def cambiar_estado_alumno(
    alumno_id: int,
    payload: AlumnoToggleEstadoRequest,
    current_admin: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validar la contraseña del administrador actual
    if not verify_password(payload.admin_password, current_admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña de administrador incorrecta",
        )

    alumno = db.query(Alumno).filter(Alumno.id == alumno_id).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado"
        )

    alumno.activo = payload.activo
    db.commit()
    db.refresh(alumno)
    return alumno


@router.delete("/{alumno_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_alumno(alumno_id: int, db: Session = Depends(get_db)):
    alumno = db.query(Alumno).filter(Alumno.id == alumno_id).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado"
        )
    db.delete(alumno)
    db.commit()

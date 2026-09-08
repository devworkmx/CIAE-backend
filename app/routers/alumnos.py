from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alumno
from app.schemas import AlumnoCreate, AlumnoOut, AlumnoUpdate
from app.security import get_current_user

router = APIRouter(
    prefix="/api/alumnos",
    tags=["alumnos"],
    dependencies=[Depends(get_current_user)],  # Requiere sesión admin
)


@router.get("", response_model=List[AlumnoOut])
def listar_alumnos(
    busqueda: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Alumno)
    if busqueda:
        termino = f"%{busqueda}%"
        query = query.filter(
            (Alumno.nombre.ilike(termino)) |
            (Alumno.apellidos.ilike(termino)) |
            (Alumno.curp.ilike(termino))
        )
    return query.order_by(Alumno.apellidos.asc()).all()


@router.get("/{alumno_id}", response_model=AlumnoOut)
def obtener_alumno(alumno_id: int, db: Session = Depends(get_db)):
    alumno = db.query(Alumno).filter(Alumno.id == alumno_id).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alumno no encontrado"
        )
    return alumno


@router.post("", response_model=AlumnoOut, status_code=status.HTTP_201_CREATED)
def crear_alumno(datos: AlumnoCreate, db: Session = Depends(get_db)):
    # Normalizar CURP a mayúsculas
    curp_limpia = datos.curp.strip().upper()

    # Validar que no exista un alumno con la misma CURP
    existente = db.query(Alumno).filter(Alumno.curp == curp_limpia).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un alumno registrado con la CURP '{curp_limpia}'"
        )

    nuevo_alumno = Alumno(
        nombre=datos.nombre.strip(),
        apellidos=datos.apellidos.strip(),
        curp=curp_limpia,
        email=datos.email,
        telefono=datos.telefono,
    )
    db.add(nuevo_alumno)
    db.commit()
    db.refresh(nuevo_alumno)
    return nuevo_alumno


@router.patch("/{alumno_id}", response_model=AlumnoOut)
def actualizar_alumno(
    alumno_id: int,
    datos: AlumnoUpdate,
    db: Session = Depends(get_db)
):
    alumno = db.query(Alumno).filter(Alumno.id == alumno_id).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alumno no encontrado"
        )

    datos_dict = datos.model_dump(exclude_unset=True)

    # Si se actualiza la CURP, verificar que no colisione con otro registro
    if "curp" in datos_dict and datos_dict["curp"]:
        curp_limpia = datos_dict["curp"].strip().upper()
        duplicado = (
            db.query(Alumno)
            .filter(Alumno.curp == curp_limpia, Alumno.id != alumno_id)
            .first()
        )
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La CURP '{curp_limpia}' ya pertenece a otro alumno"
            )
        datos_dict["curp"] = curp_limpia

    for campo, valor in datos_dict.items():
        setattr(alumno, campo, valor)

    db.commit()
    db.refresh(alumno)
    return alumno


@router.delete("/{alumno_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_alumno(alumno_id: int, db: Session = Depends(get_db)):
    alumno = db.query(Alumno).filter(Alumno.id == alumno_id).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alumno no encontrado"
        )
    db.delete(alumno)
    db.commit()

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Curso
from app.schemas import CursoCreate, CursoOut, CursoUpdate
from app.security import get_current_user

router = APIRouter(
    prefix="/api/cursos",
    tags=["cursos"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=List[CursoOut])
def listar_cursos(db: Session = Depends(get_db)):
    return db.query(Curso).order_by(Curso.nombre.asc()).all()


@router.get("/{curso_id}", response_model=CursoOut)
def obtener_curso(curso_id: int, db: Session = Depends(get_db)):
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    return curso


@router.post("", response_model=CursoOut, status_code=status.HTTP_201_CREATED)
def crear_curso(datos: CursoCreate, db: Session = Depends(get_db)):
    curso = Curso(**datos.model_dump())
    db.add(curso)
    db.commit()
    db.refresh(curso)
    return curso


@router.patch("/{curso_id}", response_model=CursoOut)
def actualizar_curso(curso_id: int, datos: CursoUpdate, db: Session = Depends(get_db)):
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    for key, value in datos.model_dump(exclude_unset=True).items():
        setattr(curso, key, value)
    db.commit()
    db.refresh(curso)
    return curso


@router.delete("/{curso_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_curso(curso_id: int, db: Session = Depends(get_db)):
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    db.delete(curso)
    db.commit()

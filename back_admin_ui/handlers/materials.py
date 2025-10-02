from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from services.db import schema
from services.db.db import get_db
from services.db.service import MaterialService

router = APIRouter(prefix="/materials", tags=["materials"])


@router.post("/", response_model=schema.Material, status_code=status.HTTP_201_CREATED)
def create_material(
        material_in: schema.MaterialCreate,
        db: Session = Depends(get_db)
) -> schema.Material:
    # так же реализовать все проверки
    service = MaterialService(db)
    material = service.create_material(material_in)
    return schema.Material.model_validate(material)


@router.get("/", response_model=List[schema.Material])
def list_materials(
        doc_id: int = Query(..., ge=1),
        limit: int = Query(100, ge=1),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db),
) -> List[schema.Material]:
    # все проверки и офсет с лимитами, так же админу выдается все, а остальные если привязаны
    service = MaterialService(db)
    materials = service.list_materials(doc_id=doc_id, limit=limit, offset=offset)
    return [schema.Material.model_validate(item) for item in materials]


@router.get("/{material_id}", response_model=schema.Material)
def get_material(material_id: int, db: Session = Depends(get_db)) -> schema.Material:
    # реализовать проверки и если пользователь привязан к данному материалу - показываем, нет - значит нет, админу все
    service = MaterialService(db)
    material = service.get_material(material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return schema.Material.model_validate(material)


@router.put("/{material_id}", response_model=schema.Material)
def update_material(
        material_id: int, material_in: schema.MaterialUpdate, db: Session = Depends(get_db)
) -> schema.Material:
    #  реализовать проверки
    service = MaterialService(db)
    material = service.update_material(material_id, material_in)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return schema.Material.model_validate(material)


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(material_id: int, db: Session = Depends(get_db)) -> None:
    # только админ
    service = MaterialService(db)
    deleted = service.delete_material(material_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

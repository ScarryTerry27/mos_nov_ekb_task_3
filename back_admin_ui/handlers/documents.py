from typing import List

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from services.db import schema
from services.db.db import get_db
from services.db.service import DocumentService, MaterialService
from services.others.photo_client import analyze_photo

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=schema.Document, status_code=status.HTTP_201_CREATED)
def create_document(
    document_in: schema.DocumentCreate, db: Session = Depends(get_db)
) -> schema.Document:
    # здесь выполнить проверку существует ли пользователь и объект если нет выдаем нот фоунд
    service = DocumentService(db)
    document = service.create_document(document_in)
    return schema.Document.model_validate(document)


@router.get("/", response_model=List[schema.Document])
def list_documents(
    object_id: int = Query(..., ge=1),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[schema.Document]:
    # все проверки и офсет с лимитами, так же админу выдается все, а остальные если привязаны
    service = DocumentService(db)
    documents = service.list_documents(object_id=object_id, limit=limit, offset=offset)
    return [schema.Document.model_validate(item) for item in documents]


@router.post(
    "/process-photo",
    response_model=schema.PhotoProcessingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def process_photo(
    user_id: int = Form(...),
    object_id: int = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> schema.PhotoProcessingResponse:
    """Accept a photo, forward it to the analysis service and persist the results."""

    if photo.content_type not in {"image/jpeg", "image/png", "image/jpg"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only JPEG and PNG are allowed.",
        )

    image_bytes = await photo.read()
    try:
        document_data, materials_data = await analyze_photo(
            image_bytes=image_bytes,
            filename=photo.filename or "photo.jpg",
            content_type=photo.content_type or "image/jpeg",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Analyzer HTTP error: {e.response.status_code}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyzer failed: {e}") from e

    document_service = DocumentService(db)
    material_service = MaterialService(db)

    document_create = schema.DocumentCreate(
        user_id=user_id,
        object_id=object_id,
        doc_type=document_data.doc_type,
        doc_number=document_data.doc_number,
        doc_date_start=document_data.doc_date_start,
        doc_date_end=document_data.doc_date_end,
        doc_image_id=document_data.doc_image_id,
    )
    document = document_service.create_document(document_create)

    saved_materials: List[schema.Material] = []
    for material_data in materials_data:
        material_create = schema.MaterialCreate(
            name=material_data.name,
            okpd=material_data.okpd,
            amount=material_data.amount,
            uom=material_data.uom,
            to_be_certified=material_data.to_be_certified,
            certificate=material_data.certificate,
            doc_id=document.document_id,
        )
        material = material_service.create_material(material_create)
        saved_materials.append(schema.Material.model_validate(material))

    response = schema.PhotoProcessingResponse(
        document=schema.Document.model_validate(document),
        materials=saved_materials,
    )

    return response


@router.get("/{document_id}", response_model=schema.Document)
def get_document(document_id: int, db: Session = Depends(get_db)) -> schema.Document:
    # реализовать проверки и если пользователь привязан к данному материалу - показываем, нет - значит нет, админу все
    service = DocumentService(db)
    document = service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return schema.Document.model_validate(document)


@router.put("/{document_id}", response_model=schema.Document)
def update_document(
    document_id: int, document_in: schema.DocumentUpdate, db: Session = Depends(get_db)
) -> schema.Document:
    # здесь так де проверки на id и user и так далее
    service = DocumentService(db)
    document = service.update_document(document_id, document_in)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return schema.Document.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> None:
    # удалить может только админ
    service = DocumentService(db)
    deleted = service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


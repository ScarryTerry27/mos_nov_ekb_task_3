from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.db import model, schema


class UserService:
    """Service layer for CRUD operations on :class:`model.User`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_user(self, user_in: schema.UserCreate) -> model.User:
        """Create a new user in the database."""
        user = model.User(
            name=user_in.name,
            password=user_in.password,
            role=model.RoleEnum(user_in.role.value),
        )
        self._session.add(user)
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            raise
        self._session.refresh(user)
        return user

    def list_users(self) -> List[model.User]:
        """Return all users."""
        return self._session.query(model.User).all()

    def get_user_by_id(self, user_id: int) -> Optional[model.User]:
        """Return a user by its ID."""
        return (
            self._session.query(model.User)
            .filter(model.User.user_id == user_id)
            .first()
        )

    def get_user_by_name(self, name: str) -> Optional[model.User]:
        """Return a user by its name."""
        return self._session.query(model.User).filter(model.User.name == name).first()

    def update_user(
        self, user_id: int, user_in: schema.UserUpdate
    ) -> Optional[model.User]:
        """Update user fields."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        if user_in.name is not None:
            user.name = user_in.name
        if user_in.password is not None:
            user.password = user_in.password
        if user_in.role is not None:
            user.role = model.RoleEnum(user_in.role.value)
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def update_password(self, user_id: int, new_password: str) -> Optional[model.User]:
        """Update password for a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        user.password = new_password
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def delete_user(self, user_id: int) -> bool:
        """Delete a user by its ID."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        self._session.delete(user)
        self._session.commit()
        return True

    def authenticate(self, name: str, password: str) -> Optional[model.User]:
        """Validate user credentials."""
        user = self.get_user_by_name(name)
        if user and user.password == password:
            return user
        return None

    def new_list_users(
        self,
        *,
        role: Optional[model.RoleEnum] = None,
        name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[model.User]:
        q = self._session.query(model.User)
        if role is not None:
            q = q.filter(model.User.role == role)
        if name:
            q = q.filter(model.User.name.like(f"%{name}%"))
        q = q.order_by(model.User.user_id).offset(offset).limit(limit)
        return q.all()


class ObjectService:
    """Service layer for CRUD operations on :class:`model.Object`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_object(self, object_in: schema.ObjectCreate) -> model.Object:
        obj = model.Object(
            name=object_in.name,
            admin_id=object_in.admin_id,
            inspector_id=object_in.inspector_id,
            contractor_id=object_in.contractor_id,
            status=object_in.status,
            address=object_in.address,
            object_lat=object_in.object_lat,
            object_lon=object_in.object_lon,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return obj

    def list_objects(
        self, *, limit: int, offset: int, role: schema.RoleEnum, user_id: int
    ) -> List[model.Object]:
        query = self._session.query(model.Object)

        if role == schema.RoleEnum.INSPECTOR:
            query = query.filter(model.Object.inspector_id == user_id)
        elif role == schema.RoleEnum.CONTRACTOR:
            query = query.filter(model.Object.contractor_id == user_id)

        return query.offset(offset).limit(limit).all()

    def get_object(self, object_id: int) -> Optional[model.Object]:
        return (
            self._session.query(model.Object)
            .filter(model.Object.object_id == object_id)
            .first()
        )

    def update_object(
        self, object_id: int, object_in: schema.ObjectUpdate
    ) -> Optional[model.Object]:
        obj = self.get_object(object_id)
        if not obj:
            return None

        if object_in.name is not None:
            obj.name = object_in.name
        if object_in.admin_id is not None:
            obj.admin_id = object_in.admin_id
        if object_in.inspector_id is not None:
            obj.inspector_id = object_in.inspector_id
        if object_in.contractor_id is not None:
            obj.contractor_id = object_in.contractor_id
        if object_in.status is not None:
            obj.status = object_in.status
        if object_in.address is not None:
            obj.address = object_in.address
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return obj

    def delete_object(self, object_id: int) -> bool:
        obj = self.get_object(object_id)
        if not obj:
            return False
        self._session.delete(obj)
        self._session.commit()
        return True


class SubObjectService:
    """Service layer for CRUD operations on :class:`model.SubObject`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_subobject(self, subobject_in: schema.SubObjectCreate) -> model.SubObject:
        subobject = model.SubObject(
            name=subobject_in.name,
            object_id=subobject_in.object_id,
            status_inspector=(
                model.StatusEnum(subobject_in.status_inspector.value)
                if subobject_in.status_inspector
                else None
            ),
            status_contractor=(
                model.StatusEnum(subobject_in.status_contractor.value)
                if subobject_in.status_contractor
                else None
            ),
            status_admin=(
                model.StatusEnum(subobject_in.status_admin.value)
                if subobject_in.status_admin
                else None
            ),
            prescription_info=subobject_in.prescription_info,
            start_date=subobject_in.start_date,
            finish_date=subobject_in.finish_date,
        )
        self._session.add(subobject)
        self._session.commit()
        self._session.refresh(subobject)
        return subobject

    def list_subobjects(
        self,
        *,
        object_id: int,
        limit: int,
        offset: int,
        role: schema.RoleEnum,
        user_id: int,
    ) -> List[model.SubObject]:
        query = self._session.query(model.SubObject).filter(
            model.SubObject.object_id == object_id
        )

        if role in (schema.RoleEnum.INSPECTOR, schema.RoleEnum.CONTRACTOR):
            query = query.join(
                model.Object, model.SubObject.object_id == model.Object.object_id
            )
            if role == schema.RoleEnum.INSPECTOR:
                query = query.filter(model.Object.inspector_id == user_id)
            else:
                query = query.filter(model.Object.contractor_id == user_id)

        return query.offset(offset).limit(limit).all()

    def get_subobject(self, subobject_id: int) -> Optional[model.SubObject]:
        return (
            self._session.query(model.SubObject)
            .filter(model.SubObject.subobject_id == subobject_id)
            .first()
        )

    def update_subobject(
        self, subobject_id: int, subobject_in: schema.SubObjectUpdate
    ) -> Optional[model.SubObject]:
        subobject = self.get_subobject(subobject_id)
        if not subobject:
            return None

        if "name" in subobject_in.model_fields_set:
            subobject.name = subobject_in.name
        if "status_inspector" in subobject_in.model_fields_set:
            subobject.status_inspector = (
                model.StatusEnum(subobject_in.status_inspector.value)
                if subobject_in.status_inspector is not None
                else None
            )
        if "status_contractor" in subobject_in.model_fields_set:
            subobject.status_contractor = (
                model.StatusEnum(subobject_in.status_contractor.value)
                if subobject_in.status_contractor is not None
                else None
            )
        if "status_admin" in subobject_in.model_fields_set:
            subobject.status_admin = (
                model.StatusEnum(subobject_in.status_admin.value)
                if subobject_in.status_admin is not None
                else None
            )
        if "prescription_info" in subobject_in.model_fields_set:
            subobject.prescription_info = subobject_in.prescription_info
        if "object_id" in subobject_in.model_fields_set:
            subobject.object_id = subobject_in.object_id
        self._session.add(subobject)
        self._session.commit()
        self._session.refresh(subobject)
        return subobject

    def delete_subobject(self, subobject_id: int) -> bool:
        subobject = self.get_subobject(subobject_id)
        if not subobject:
            return False
        self._session.delete(subobject)
        self._session.commit()
        return True


class CheckService:
    """Service layer for CRUD operations on :class:`model.Check`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_check(self, check_in: schema.CheckCreate) -> model.Check:
        check = model.Check(
            subobject_id=check_in.subobject_id,
            location=check_in.location,
            info=check_in.info,
            status_check=(
                model.CheckStatusEnum(check_in.status_check.value)
                if check_in.status_check
                else None
            ),
        )
        self._session.add(check)
        self._session.commit()
        self._session.refresh(check)
        return check

    def list_checks(
        self,
        *,
        subobject_id: int,
        limit: int,
        offset: int,
        role: schema.RoleEnum,
        user_id: int,
    ) -> List[model.Check]:
        query = self._session.query(model.Check).filter(
            model.Check.subobject_id == subobject_id
        )

        if role == schema.RoleEnum.INSPECTOR:
            query = (
                query.join(
                    model.SubObject,
                    model.Check.subobject_id == model.SubObject.subobject_id,
                )
                .join(model.Object, model.SubObject.object_id == model.Object.object_id)
                .filter(model.Object.inspector_id == user_id)
            )

        return query.offset(offset).limit(limit).all()

    def get_check(self, check_id: int) -> Optional[model.Check]:
        return (
            self._session.query(model.Check)
            .filter(model.Check.check_id == check_id)
            .first()
        )

    def update_check(
        self, check_id: int, check_in: schema.CheckUpdate
    ) -> Optional[model.Check]:
        check = self.get_check(check_id)
        if not check:
            return None

        if "location" in check_in.model_fields_set:
            check.location = check_in.location
        if "info" in check_in.model_fields_set:
            check.info = check_in.info
        if "status_check" in check_in.model_fields_set:
            check.status_check = (
                model.CheckStatusEnum(check_in.status_check.value)
                if check_in.status_check is not None
                else None
            )
        if "subobject_id" in check_in.model_fields_set:
            check.subobject_id = check_in.subobject_id
        self._session.add(check)
        self._session.commit()
        self._session.refresh(check)
        return check

    def delete_check(self, check_id: int) -> bool:
        check = self.get_check(check_id)
        if not check:
            return False
        self._session.delete(check)
        self._session.commit()
        return True


class IncidentService:
    """Service layer for CRUD operations on :class:`model.Incident`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_incident(self, incident_in: schema.IncidentCreate) -> model.Incident:
        incident = model.Incident(
            check_id=incident_in.check_id,
            photo=incident_in.photo,
            incident_status=incident_in.incident_status,
            incident_info=incident_in.incident_info,
            prescription_type=(
                model.PrescriptionTypeEnum(incident_in.prescription_type.value)
                if incident_in.prescription_type
                else None
            ),
        )
        self._session.add(incident)
        self._session.commit()
        self._session.refresh(incident)
        return incident

    def list_incidents(
        self, *, check_id: int, limit: int, offset: int
    ) -> List[model.Incident]:
        return (
            self._session.query(model.Incident)
            .filter(model.Incident.check_id == check_id)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_incident(self, incident_id: int) -> Optional[model.Incident]:
        return (
            self._session.query(model.Incident)
            .filter(model.Incident.incident_id == incident_id)
            .first()
        )

    def update_incident(
        self, incident_id: int, incident_in: schema.IncidentUpdate
    ) -> Optional[model.Incident]:
        incident = self.get_incident(incident_id)
        if not incident:
            return None

        if "photo" in incident_in.model_fields_set:
            incident.photo = incident_in.photo
        if "incident_status" in incident_in.model_fields_set:
            incident.incident_status = incident_in.incident_status
        if "incident_info" in incident_in.model_fields_set:
            incident.incident_info = incident_in.incident_info
        if "prescription_type" in incident_in.model_fields_set:
            incident.prescription_type = (
                model.PrescriptionTypeEnum(incident_in.prescription_type.value)
                if incident_in.prescription_type is not None
                else None
            )
        if "check_id" in incident_in.model_fields_set:
            incident.check_id = incident_in.check_id
        self._session.add(incident)
        self._session.commit()
        self._session.refresh(incident)
        return incident

    def delete_incident(self, incident_id: int) -> bool:
        incident = self.get_incident(incident_id)
        if not incident:
            return False
        self._session.delete(incident)
        self._session.commit()
        return True


class DocumentService:
    """Service layer for CRUD operations on :class:`model.Document`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_document(self, document_in: schema.DocumentCreate) -> model.Document:
        document = model.Document(
            user_id=document_in.user_id,
            object_id=document_in.object_id,
            doc_type=model.DocTypeEnum(document_in.doc_type.value),
            doc_number=document_in.doc_number,
            doc_date_start=document_in.doc_date_start,
            doc_date_end=document_in.doc_date_end,
            doc_image_id=document_in.doc_image_id,
        )
        self._session.add(document)
        self._session.commit()
        self._session.refresh(document)
        return document

    def list_documents(
        self, *, object_id: int, limit: int, offset: int
    ) -> List[model.Document]:
        return (
            self._session.query(model.Document)
            .filter(model.Document.object_id == object_id)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_document(self, document_id: int) -> Optional[model.Document]:
        return (
            self._session.query(model.Document)
            .filter(model.Document.document_id == document_id)
            .first()
        )

    def update_document(
        self, document_id: int, document_in: schema.DocumentUpdate
    ) -> Optional[model.Document]:
        document = self.get_document(document_id)
        if not document:
            return None

        if document_in.user_id is not None:
            document.user_id = document_in.user_id
        if document_in.object_id is not None:
            document.object_id = document_in.object_id
        if document_in.doc_type is not None:
            document.doc_type = model.DocTypeEnum(document_in.doc_type.value)
        if document_in.doc_number is not None:
            document.doc_number = document_in.doc_number
        if document_in.doc_date_start is not None:
            document.doc_date_start = document_in.doc_date_start
        if document_in.doc_date_end is not None:
            document.doc_date_end = document_in.doc_date_end
        if document_in.doc_image_id is not None:
            document.doc_image_id = document_in.doc_image_id
        self._session.add(document)
        self._session.commit()
        self._session.refresh(document)
        return document

    def delete_document(self, document_id: int) -> bool:
        document = self.get_document(document_id)
        if not document:
            return False
        self._session.delete(document)
        self._session.commit()
        return True


class MaterialService:
    """Service layer for CRUD operations on :class:`model.Material`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_material(self, material_in: schema.MaterialCreate) -> model.Material:
        material = model.Material(
            name=material_in.name,
            doc_id=material_in.doc_id,
            okpd=material_in.okpd,
            amount=material_in.amount,
            uom=material_in.uom,
            to_be_certified=material_in.to_be_certified,
            certificate=material_in.certificate,
        )
        self._session.add(material)
        self._session.commit()
        self._session.refresh(material)
        return material

    def list_materials(
        self, *, doc_id: int, limit: int, offset: int
    ) -> List[model.Material]:
        return (
            self._session.query(model.Material)
            .filter(model.Material.doc_id == doc_id)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_material(self, material_id: int) -> Optional[model.Material]:
        return (
            self._session.query(model.Material)
            .filter(model.Material.material_id == material_id)
            .first()
        )

    def update_material(
        self, material_id: int, material_in: schema.MaterialUpdate
    ) -> Optional[model.Material]:
        material = self.get_material(material_id)
        if not material:
            return None

        if material_in.name is not None:
            material.name = material_in.name
        if material_in.doc_id is not None:
            material.doc_id = material_in.doc_id
        if material_in.okpd is not None:
            material.okpd = material_in.okpd
        if material_in.amount is not None:
            material.amount = material_in.amount
        if material_in.uom is not None:
            material.uom = material_in.uom
        if material_in.to_be_certified is not None:
            material.to_be_certified = material_in.to_be_certified
        if material_in.certificate is not None:
            material.certificate = material_in.certificate
        self._session.add(material)
        self._session.commit()
        self._session.refresh(material)
        return material

    def delete_material(self, material_id: int) -> bool:
        material = self.get_material(material_id)
        if not material:
            return False
        self._session.delete(material)
        self._session.commit()
        return True

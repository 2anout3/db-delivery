from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, services
from ..database import get_db
from ..security import get_current_user, hash_password, require_roles


router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.post("", response_model=schemas.ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: schemas.ClientCreate,
    db: Session = Depends(get_db),
    _: models.UserAccount = Depends(require_roles("employee", "admin")),
):
    services.ensure_unique_user_fields(db, payload.login, payload.phone)

    user = models.UserAccount(
        login=payload.login,
        password_hash=hash_password(payload.password),
        role="client",
    )
    db.add(user)
    db.flush()

    person = models.Person(
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
    )
    db.add(person)
    db.flush()

    client = models.Client(
        person_id=person.person_id,
        user_id=user.user_id,
        client_status=payload.client_status,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    db.refresh(person)
    return client


@router.get("", response_model=list[schemas.ClientRead])
def list_clients(
    db: Session = Depends(get_db),
    _: models.UserAccount = Depends(get_current_user),
):
    result = db.execute(
        select(models.Client)
        .options(joinedload(models.Client.person))
        .order_by(models.Client.client_id)
    )
    return result.scalars().all()

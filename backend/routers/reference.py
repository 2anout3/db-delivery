from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user


router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("/branches", response_model=list[schemas.BranchRead])
def list_branches(
    db: Session = Depends(get_db),
    _: models.UserAccount = Depends(get_current_user),
):
    result = db.execute(
        select(models.Branch)
        .options(joinedload(models.Branch.address))
        .order_by(models.Branch.branch_id)
    )
    return result.scalars().all()


@router.get("/statuses", response_model=list[schemas.DeliveryStatusRead])
def list_statuses(
    db: Session = Depends(get_db),
    _: models.UserAccount = Depends(get_current_user),
):
    result = db.execute(
        select(models.DeliveryStatus).order_by(models.DeliveryStatus.sort_order)
    )
    return result.scalars().all()


@router.get("/cities", response_model=list[str])
def list_cities(
    db: Session = Depends(get_db),
    _: models.UserAccount = Depends(get_current_user),
):
    result = db.execute(
        select(models.Address.city)
        .join(models.Branch, models.Branch.address_id == models.Address.address_id)
        .distinct()
        .order_by(models.Address.city)
    )
    return result.scalars().all()

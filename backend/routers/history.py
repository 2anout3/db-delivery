from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, services
from ..database import get_db
from ..security import get_current_user


router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/delivery/{delivery_id}", response_model=list[schemas.DeliveryStatusHistoryRead])
def get_delivery_history(
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: models.UserAccount = Depends(get_current_user),
):
    delivery = services.get_delivery_or_404(db, delivery_id)
    if not services.can_access_delivery(current_user, delivery):
        raise HTTPException(status_code=403, detail="Нет доступа к истории этой доставки")

    history = db.execute(
        select(models.DeliveryStatusHistory)
        .options(
            joinedload(models.DeliveryStatusHistory.old_status),
            joinedload(models.DeliveryStatusHistory.new_status),
        )
        .where(models.DeliveryStatusHistory.delivery_id == delivery_id)
        .order_by(models.DeliveryStatusHistory.changed_at)
    ).scalars().all()

    return [
        schemas.DeliveryStatusHistoryRead(
            history_id=item.history_id,
            delivery_id=item.delivery_id,
            changed_at=item.changed_at,
            comment=item.comment,
            old_status=item.old_status,
            new_status=item.new_status,
            changed_by_employee_id=item.changed_by_employee_id,
        )
        for item in history
    ]

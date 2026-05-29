from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, services
from ..database import get_db
from ..security import get_current_user


router = APIRouter(prefix="/api/couriers", tags=["couriers"])


@router.get("", response_model=list[schemas.CourierRead])
def list_couriers(
    db: Session = Depends(get_db),
    _: models.UserAccount = Depends(get_current_user),
):
    couriers = db.execute(
        select(models.Courier)
        .options(
            joinedload(models.Courier.employee).joinedload(models.Employee.person),
            joinedload(models.Courier.employee).joinedload(models.Employee.branch),
        )
        .where(models.Courier.employee.has(models.Employee.is_active.is_(True)))
        .order_by(models.Courier.employee_id)
    ).scalars().all()

    return [
        schemas.CourierRead(
            employee_id=item.employee_id,
            transport_type=item.transport_type,
            capacity_kg=item.capacity_kg,
            employee_role=item.employee.employee_role,
            full_name=item.employee.person.full_name,
            branch_name=item.employee.branch.name,
        )
        for item in couriers
    ]


@router.post("/self-assign/{delivery_id}", response_model=schemas.DeliveryRead)
def self_assign_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: models.UserAccount = Depends(get_current_user),
):
    if services.get_effective_role(current_user) != "courier":
        raise HTTPException(status_code=403, detail="Только курьер может взять доставку")
    if not current_user.employee or not current_user.employee.courier:
        raise HTTPException(status_code=403, detail="Нужен профиль курьера")
    if not current_user.employee.is_active:
        raise HTTPException(status_code=403, detail="Курьер неактивен")

    delivery = db.execute(
        select(models.Delivery)
        .options(
            joinedload(models.Delivery.current_status),
            joinedload(models.Delivery.assignments).joinedload(models.DeliveryCourierAssignment.call_address),
        )
        .where(models.Delivery.delivery_id == delivery_id)
    ).unique().scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Доставка не найдена")
    open_assignments = [item for item in delivery.assignments if item.courier_id is None]
    if not open_assignments:
        raise HTTPException(status_code=400, detail="У доставки нет открытой курьерской заявки")
    open_assignment = next(
        (
            item
            for item in open_assignments
            if services.can_courier_take_assignment(current_user.employee.courier, item, delivery)
            and (
                (item.service_type == "pickup" and delivery.current_status.code == "WAITING_COURIER")
                or (item.service_type == "delivery" and delivery.current_status.code == "AT_DESTINATION_BRANCH")
            )
        ),
        None,
    )
    if not open_assignment:
        raise HTTPException(
            status_code=403,
            detail="Курьер может взять только доступную заявку из своего города, филиала и в пределах грузоподъемности",
        )

    db.execute(
        text(
            "CALL assign_courier_to_delivery(:delivery_id, :courier_id, :client_id, "
            ":service_type, :call_address_id, :service_cost, :employee_id, :comment)"
        ),
        {
            "delivery_id": delivery.delivery_id,
            "courier_id": current_user.employee.employee_id,
            "client_id": open_assignment.client_id,
            "service_type": open_assignment.service_type,
            "call_address_id": open_assignment.call_address_id,
            "service_cost": Decimal("0.00"),
            "employee_id": current_user.employee.employee_id,
            "comment": f"Курьер #{current_user.employee.employee_id} взял доставку",
        },
    )

    db.commit()
    return services.get_delivery_or_404(db, delivery_id)

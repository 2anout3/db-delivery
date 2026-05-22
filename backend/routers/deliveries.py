from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..database import get_db
from ..security import get_current_user


router = APIRouter(prefix="/api/deliveries", tags=["deliveries"])


@router.post("", response_model=schemas.DeliveryRead, status_code=status.HTTP_201_CREATED)
def create_delivery(
    payload: schemas.DeliveryCreate,
    db: Session = Depends(get_db),
    current_user: models.UserAccount = Depends(get_current_user),
):
    services.require_capability(current_user, "can_create_delivery")

    effective_role = services.get_effective_role(current_user)
    sender_client_id = current_user.client.client_id if current_user.client else payload.sender_client_id
    if effective_role == "client" and not current_user.client:
        raise HTTPException(status_code=403, detail="Только клиент может создать доставку")
    if effective_role == "admin" and sender_client_id is None:
        raise HTTPException(status_code=400, detail="Администратор должен указать sender_client_id")
    if sender_client_id is None:
        raise HTTPException(status_code=400, detail="Не удалось определить отправителя")

    sender = db.get(models.Client, sender_client_id)
    if not sender:
        raise HTTPException(status_code=404, detail="Отправитель не найден")

    recipient = db.get(models.Client, payload.recipient_client_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Получатель не найден")

    origin_branch = db.get(models.Branch, payload.origin_branch_id)
    destination_branch = db.get(models.Branch, payload.destination_branch_id)
    if not origin_branch or not destination_branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    if payload.sender_courier_required and not payload.sender_address:
        raise HTTPException(status_code=400, detail="Для курьера у отправителя нужен адрес отправителя")
    if payload.sender_courier_required and payload.sender_address.city != origin_branch.address.city:
        raise HTTPException(status_code=400, detail="Город адреса отправителя должен совпадать с городом филиала отправления")

    sender_address = (
        services.create_address(db, payload.sender_address)
        if payload.sender_courier_required
        else origin_branch.address
    )
    initial_status = services.get_status_by_code(db, "CREATED")
    operator = services.get_default_operator(db)
    services.set_status_change_context(db, operator.employee_id, "Доставка создана")

    delivery = models.Delivery(
        tracking_number=services.build_tracking_number(),
        sender_client_id=sender_client_id,
        recipient_client_id=payload.recipient_client_id,
        origin_branch_id=payload.origin_branch_id,
        destination_branch_id=payload.destination_branch_id,
        sender_address_id=sender_address.address_id,
        recipient_address_id=destination_branch.address_id,
        created_by_employee_id=operator.employee_id,
        current_status_id=initial_status.status_id,
        declared_weight_kg=payload.declared_weight_kg,
        declared_value=payload.declared_value,
        description=payload.description,
    )
    db.add(delivery)
    db.flush()

    if payload.sender_courier_required:
        db.add(
            models.DeliveryCourierAssignment(
                delivery_id=delivery.delivery_id,
                courier_id=None,
                client_id=sender_client_id,
                service_type="pickup",
                call_address_id=sender_address.address_id,
                service_cost=0,
            )
        )

    db.commit()
    db.refresh(delivery)
    return services.get_delivery_or_404(db, delivery.delivery_id)


@router.post("/{delivery_id}/recipient-courier-request", response_model=schemas.DeliveryRead)
def request_recipient_courier(
    delivery_id: int,
    payload: schemas.RecipientCourierRequest,
    db: Session = Depends(get_db),
    current_user: models.UserAccount = Depends(get_current_user),
):
    delivery = services.get_delivery_or_404(db, delivery_id)
    is_recipient = current_user.client and current_user.client.client_id == delivery.recipient_client_id
    if current_user.role != "admin" and not is_recipient:
        raise HTTPException(status_code=403, detail="Только получатель может запросить курьера")
    existing_assignment = next(
        (item for item in delivery.assignments if item.service_type == "delivery"),
        None,
    )
    if existing_assignment:
        raise HTTPException(status_code=400, detail="Курьерская доставка для получателя уже запрошена")

    if payload.recipient_address.city != delivery.destination_branch.address.city:
        raise HTTPException(status_code=400, detail="Город адреса получателя должен совпадать с городом филиала назначения")
    address = services.create_address(db, payload.recipient_address)
    db.add(
        models.DeliveryCourierAssignment(
            delivery_id=delivery.delivery_id,
            courier_id=None,
            client_id=delivery.recipient_client_id,
            service_type="delivery",
            call_address_id=address.address_id,
            service_cost=0,
        )
    )
    db.commit()
    return services.get_delivery_or_404(db, delivery_id)


@router.get("", response_model=list[schemas.DeliveryRead])
def list_deliveries(
    db: Session = Depends(get_db),
    current_user: models.UserAccount = Depends(get_current_user),
):
    query = (
        select(models.Delivery)
        .options(*services.get_delivery_load_options())
        .order_by(models.Delivery.delivery_id.desc())
    )
    query = services.apply_delivery_scope(query, current_user)

    result = db.execute(query).unique().scalars().all()
    return result


@router.get("/{delivery_id}", response_model=schemas.DeliveryRead)
def get_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: models.UserAccount = Depends(get_current_user),
):
    delivery = services.get_delivery_or_404(db, delivery_id)
    if not services.can_access_delivery(current_user, delivery):
        raise HTTPException(status_code=403, detail="Нет доступа к этой доставке")
    return delivery


@router.patch("/{delivery_id}/status", response_model=schemas.DeliveryRead)
def update_delivery_status(
    delivery_id: int,
    payload: schemas.DeliveryStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.UserAccount = Depends(get_current_user),
):
    services.require_capability(current_user, "can_update_status")
    if not current_user.employee and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Нужен профиль сотрудника")

    delivery = services.get_delivery_or_404(db, delivery_id)

    new_status = db.get(models.DeliveryStatus, payload.new_status_id)
    if not new_status:
        raise HTTPException(status_code=404, detail="Новый статус не найден")
    services.validate_status_transition(delivery, new_status)

    employee_id = current_user.employee.employee_id if current_user.employee else delivery.created_by_employee_id
    db.execute(
        text("CALL change_delivery_status(:delivery_id, :status_id, :employee_id, :comment)"),
        {
            "delivery_id": delivery_id,
            "status_id": new_status.status_id,
            "employee_id": employee_id,
            "comment": payload.comment,
        },
    )
    db.commit()
    return services.get_delivery_or_404(db, delivery_id)

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .security import hash_password


def create_address(db: Session, payload: schemas.AddressCreate) -> models.Address:
    city_exists = db.execute(
        select(models.Address.address_id)
        .join(models.Branch, models.Branch.address_id == models.Address.address_id)
        .where(models.Address.city == payload.city)
        .limit(1)
    ).scalar_one_or_none()
    if city_exists is None:
        raise HTTPException(status_code=400, detail="Город должен быть выбран из городов с филиалами")

    address = models.Address(**payload.model_dump())
    db.add(address)
    db.flush()
    return address


def build_tracking_number() -> str:
    return f"TRK-{uuid4().hex[:12].upper()}"


def get_status_by_code(db: Session, code: str) -> models.DeliveryStatus:
    status_obj = db.execute(
        select(models.DeliveryStatus).where(models.DeliveryStatus.code == code)
    ).scalar_one_or_none()
    if not status_obj:
        raise HTTPException(status_code=400, detail=f"Статус {code} не найден")
    return status_obj


def get_default_operator(db: Session) -> models.Employee:
    operator = db.execute(
        select(models.Employee)
        .where(models.Employee.is_active.is_(True))
        .order_by(models.Employee.employee_id)
        .limit(1)
    ).scalars().first()
    if not operator:
        raise HTTPException(
            status_code=400,
            detail="Нет активного сотрудника для регистрации доставки. Выполните backend/init_db.sql.",
        )
    return operator


def get_effective_role(user: models.UserAccount) -> str:
    if user.role == "admin":
        return "admin"
    if user.client:
        return "client"
    if user.employee and user.employee.courier:
        return "courier"
    if user.employee:
        return "employee"
    return user.role


def get_permissions(user: models.UserAccount) -> dict[str, bool]:
    effective_role = get_effective_role(user)
    return {
        "can_view_deliveries": True,
        "can_create_delivery": effective_role in {"client", "admin"},
        "can_assign_courier": effective_role in {"employee", "admin"},
        "can_self_assign_delivery": effective_role == "courier",
        "can_update_status": effective_role in {"employee", "admin"},
        "can_manage_accounts": effective_role == "admin",
        "can_manage_clients": effective_role in {"employee", "admin"},
    }


def build_user_profile(user: models.UserAccount) -> schemas.UserProfile:
    person = user.client.person if user.client else user.employee.person if user.employee else None
    employee = user.employee
    courier = employee.courier if employee else None
    return schemas.UserProfile(
        user_id=user.user_id,
        login=user.login,
        role=user.role,
        effective_role=get_effective_role(user),
        created_at=user.created_at,
        full_name=person.full_name if person else None,
        phone=person.phone if person else None,
        email=person.email if person else None,
        client_id=user.client.client_id if user.client else None,
        client_status=user.client.client_status if user.client else None,
        registered_at=user.client.registered_at if user.client else None,
        employee_id=employee.employee_id if employee else None,
        employee_role=employee.employee_role if employee else None,
        hired_at=employee.hired_at if employee else None,
        is_active=employee.is_active if employee else None,
        branch_id=employee.branch_id if employee else None,
        branch=employee.branch if employee else None,
        transport_type=courier.transport_type if courier else None,
        capacity_kg=courier.capacity_kg if courier else None,
        permissions=get_permissions(user),
    )


def require_capability(user: models.UserAccount, capability: str) -> None:
    if user.role == "admin":
        return
    if not get_permissions(user).get(capability, False):
        raise HTTPException(status_code=403, detail="Недостаточно прав")


def get_allowed_next_status_codes(delivery: models.Delivery) -> set[str]:
    current_code = delivery.current_status.code
    has_courier_requests = bool(delivery.assignments)
    has_open_courier_requests = any(item.courier_id is None for item in delivery.assignments)

    if current_code in {"DELIVERED", "CANCELLED"}:
        return set()
    if current_code == "CREATED":
        return {"PROCESSING", "CANCELLED"}
    if current_code == "PROCESSING":
        next_codes = {"CANCELLED"}
        if has_courier_requests and not has_open_courier_requests:
            next_codes.add("COURIER_ASSIGNED")
        elif not has_courier_requests:
            next_codes.add("IN_TRANSIT")
        return next_codes
    if current_code == "COURIER_ASSIGNED":
        return {"CANCELLED"} if has_open_courier_requests else {"IN_TRANSIT", "CANCELLED"}
    if current_code == "IN_TRANSIT":
        return {"DELIVERED", "CANCELLED"}
    return set()


def validate_status_transition(delivery: models.Delivery, new_status: models.DeliveryStatus) -> None:
    if new_status.status_id == delivery.current_status_id:
        raise HTTPException(status_code=400, detail="Доставка уже находится в этом статусе")

    allowed_codes = get_allowed_next_status_codes(delivery)
    if new_status.code not in allowed_codes:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Нельзя перевести доставку из статуса '{delivery.current_status.name}' "
                f"в статус '{new_status.name}'"
            ),
        )


def get_delivery_load_options():
    return (
        joinedload(models.Delivery.origin_branch).joinedload(models.Branch.address),
        joinedload(models.Delivery.destination_branch).joinedload(models.Branch.address),
        joinedload(models.Delivery.sender).joinedload(models.Client.person),
        joinedload(models.Delivery.recipient).joinedload(models.Client.person),
        joinedload(models.Delivery.sender_address),
        joinedload(models.Delivery.recipient_address),
        joinedload(models.Delivery.current_status),
        joinedload(models.Delivery.assignments).joinedload(models.DeliveryCourierAssignment.call_address),
        joinedload(models.Delivery.assignments)
        .joinedload(models.DeliveryCourierAssignment.courier)
        .joinedload(models.Courier.employee)
        .joinedload(models.Employee.person),
    )


def apply_delivery_scope(query, user: models.UserAccount):
    effective_role = get_effective_role(user)
    if user.role == "admin":
        return query
    if effective_role == "client" and user.client:
        return query.where(
            (models.Delivery.sender_client_id == user.client.client_id)
            | (models.Delivery.recipient_client_id == user.client.client_id)
        )
    if effective_role == "courier" and user.employee:
        waiting_for_courier = models.Delivery.assignments.any(
            models.DeliveryCourierAssignment.courier_id.is_(None)
        )
        return query.where(
            waiting_for_courier
            | models.Delivery.assignments.any(
                models.DeliveryCourierAssignment.courier_id == user.employee.employee_id
            )
        )
    return query


def can_access_delivery(user: models.UserAccount, delivery: models.Delivery) -> bool:
    effective_role = get_effective_role(user)
    if user.role == "admin":
        return True
    if effective_role == "client" and user.client:
        return user.client.client_id in (delivery.sender_client_id, delivery.recipient_client_id)
    if effective_role == "courier" and user.employee:
        assigned_to_current_courier = any(
            item.courier_id == user.employee.employee_id for item in delivery.assignments
        )
        waiting_for_courier = any(item.courier_id is None for item in delivery.assignments)
        return assigned_to_current_courier or waiting_for_courier
    return True


def get_delivery_or_404(db: Session, delivery_id: int) -> models.Delivery:
    delivery = db.execute(
        select(models.Delivery)
        .options(*get_delivery_load_options())
        .where(models.Delivery.delivery_id == delivery_id)
    ).unique().scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Доставка не найдена")
    return delivery


def set_status_change_context(db: Session, employee_id: int | None, comment: str | None) -> None:
    db.execute(
        text("SELECT set_config('app.changed_by_employee_id', :employee_id, true)"),
        {"employee_id": str(employee_id) if employee_id is not None else ""},
    )
    db.execute(
        text("SELECT set_config('app.status_comment', :comment, true)"),
        {"comment": comment or ""},
    )


def ensure_unique_user_fields(
    db: Session,
    login: str,
    phone: str,
) -> None:
    login_exists = db.execute(
        select(models.UserAccount).where(models.UserAccount.login == login)
    ).scalar_one_or_none()
    if login_exists:
        raise HTTPException(status_code=400, detail="Логин уже используется")

    phone_exists = db.execute(
        select(models.Person).where(models.Person.phone == phone)
    ).scalar_one_or_none()
    if phone_exists:
        raise HTTPException(status_code=400, detail="Телефон уже используется")


def create_account_by_role(db: Session, payload: schemas.AdminAccountCreate) -> schemas.AdminAccountRead:
    ensure_unique_user_fields(db, payload.login, payload.phone)

    user = models.UserAccount(
        login=payload.login,
        password_hash=hash_password(payload.password),
        role=payload.role,
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

    client_id = None
    employee_id = None
    courier_id = None

    if payload.role == "client":
        client = models.Client(
            person_id=person.person_id,
            user_id=user.user_id,
            client_status=payload.client_status,
        )
        db.add(client)
        db.flush()
        client_id = client.client_id
    else:
        if payload.branch_id is None:
            raise HTTPException(status_code=400, detail="Для сотрудника требуется branch_id")

        branch = db.get(models.Branch, payload.branch_id)
        if not branch:
            raise HTTPException(status_code=404, detail="Филиал не найден")

        effective_role = payload.employee_role or (
            "courier" if payload.role == "courier" else "admin" if payload.role == "admin" else "operator"
        )
        employee = models.Employee(
            user_id=user.user_id,
            person_id=person.person_id,
            branch_id=payload.branch_id,
            employee_role=effective_role,
            is_active=payload.is_active,
        )
        db.add(employee)
        db.flush()
        employee_id = employee.employee_id

        if payload.role == "courier":
            if not payload.transport_type or payload.capacity_kg is None:
                raise HTTPException(
                    status_code=400,
                    detail="Для курьера требуются transport_type и capacity_kg",
                )
            courier = models.Courier(
                employee_id=employee.employee_id,
                transport_type=payload.transport_type,
                capacity_kg=payload.capacity_kg,
            )
            db.add(courier)
            db.flush()
            courier_id = courier.employee_id

    db.commit()
    return schemas.AdminAccountRead(
        user_id=user.user_id,
        login=user.login,
        role=payload.role,
        person_id=person.person_id,
        client_id=client_id,
        employee_id=employee_id,
        courier_id=courier_id,
    )

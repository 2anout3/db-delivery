from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, services
from ..database import get_db
from ..security import create_access_token, get_current_user, hash_password, verify_password


router = APIRouter(prefix="/api/auth", tags=["auth"])

DEMO_PASSWORDS_BY_LOGIN = {
    "admin": "admin123",
    "operator1": "operator123",
    "courier1": "courier123",
    "courier2": "courier123",
    "courier3": "courier123",
    "client1": "client123",
    "client2": "client123",
    "client3": "client123",
    "client4": "client123",
}


@router.get("/login-page-users", response_model=list[schemas.LoginPageUser])
def login_page_users(db: Session = Depends(get_db)):
    users = db.execute(
        select(models.UserAccount)
        .options(
            joinedload(models.UserAccount.client).joinedload(models.Client.person),
            joinedload(models.UserAccount.employee).joinedload(models.Employee.person),
            joinedload(models.UserAccount.employee).joinedload(models.Employee.courier),
        )
        .order_by(models.UserAccount.user_id)
    ).unique().scalars().all()

    result = []
    for user in users:
        person = user.client.person if user.client else user.employee.person if user.employee else None
        result.append(
            schemas.LoginPageUser(
                user_id=user.user_id,
                login=user.login,
                role=user.role,
                effective_role=services.get_effective_role(user),
                full_name=person.full_name if person else None,
                phone=person.phone if person else None,
                email=person.email if person else None,
                client_status=user.client.client_status if user.client else None,
                employee_role=user.employee.employee_role if user.employee else None,
                password_hint=DEMO_PASSWORDS_BY_LOGIN.get(user.login),
            )
        )
    return result


@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
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
        client_status="active",
    )
    db.add(client)
    db.commit()

    token = create_access_token({"sub": str(user.user_id), "role": user.role})
    return schemas.Token(access_token=token, role=user.role, user_id=user.user_id)


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(
        select(models.UserAccount).where(models.UserAccount.login == payload.login)
    ).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    token = create_access_token({"sub": str(user.user_id), "role": user.role})
    return schemas.Token(access_token=token, role=user.role, user_id=user.user_id)


@router.post("/demo-login/{user_id}", response_model=schemas.Token)
def demo_login(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.UserAccount, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    token = create_access_token({"sub": str(user.user_id), "role": user.role})
    return schemas.Token(access_token=token, role=user.role, user_id=user.user_id)


@router.get("/me", response_model=schemas.UserProfile)
def me(
    current_user: models.UserAccount = Depends(get_current_user),
):
    return services.build_user_profile(current_user)

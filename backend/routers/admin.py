from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..database import get_db
from ..security import require_roles


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/accounts", response_model=schemas.AdminAccountRead, status_code=201)
def create_account(
    payload: schemas.AdminAccountCreate,
    db: Session = Depends(get_db),
    _: models.UserAccount = Depends(require_roles("admin")),
):
    return services.create_account_by_role(db, payload)

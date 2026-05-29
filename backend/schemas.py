from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int


class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class UserRegister(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=3, max_length=120)
    phone: str = Field(min_length=5, max_length=20)
    email: EmailStr


class AddressBase(BaseModel):
    city: str = Field(min_length=2, max_length=100)
    street: str = Field(min_length=2, max_length=100)
    house: str = Field(min_length=1, max_length=20)
    apartment: Optional[str] = Field(default="", max_length=20)
    postal_code: Optional[str] = Field(default="", max_length=20)
    comment: Optional[str] = Field(default="", max_length=255)


class AddressCreate(AddressBase):
    pass


class AddressRead(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    address_id: int


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    person_id: int
    full_name: str
    phone: Optional[str]
    email: Optional[str]
    created_at: datetime


class BranchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    branch_id: int
    name: str
    address: AddressRead


class ClientCreate(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=3, max_length=120)
    phone: str = Field(min_length=5, max_length=20)
    email: EmailStr
    client_status: str = Field(default="active", pattern="^(active|inactive)$", max_length=20)


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: int
    client_status: str
    registered_at: datetime
    person: PersonRead
    user_id: Optional[int]


class ClientSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: int
    client_status: str
    person: PersonRead


class DeliveryStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status_id: int
    code: str
    name: str
    description: Optional[str]
    sort_order: int


class DeliveryCreate(BaseModel):
    sender_client_id: Optional[int] = None
    recipient_client_id: int
    origin_branch_id: int
    destination_branch_id: int
    sender_address: Optional[AddressCreate] = None
    declared_weight_kg: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    declared_value: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    description: Optional[str] = Field(default=None, min_length=3, max_length=255)
    sender_courier_required: bool = False


class DeliveryCostPreviewRequest(BaseModel):
    origin_branch_id: int
    destination_branch_id: int
    declared_weight_kg: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    declared_value: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class DeliveryCostPreviewRead(BaseModel):
    base_cost: Decimal
    extra_cost: Decimal
    total_cost: Decimal


class RecipientCourierRequest(BaseModel):
    recipient_address: AddressCreate


class DeliveryStatusUpdate(BaseModel):
    new_status_id: int
    comment: str = Field(default="", max_length=255)


class CourierAssignmentCreate(BaseModel):
    courier_id: int
    client_id: int
    service_type: str = Field(min_length=3, max_length=20)
    call_address: AddressCreate
    service_cost: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class CourierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    transport_type: str
    capacity_kg: Decimal
    employee_role: str
    full_name: str
    branch_name: str


class CourierAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    delivery_id: int
    courier_id: Optional[int]
    client_id: int
    service_type: str
    service_cost: Decimal
    assigned_at: datetime
    completed_at: Optional[datetime]
    call_address: AddressRead


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    delivery_id: int
    tracking_number: str
    sender_client_id: int
    recipient_client_id: int
    sender: ClientSummaryRead
    recipient: ClientSummaryRead
    origin_branch: BranchRead
    destination_branch: BranchRead
    sender_address: AddressRead
    recipient_address: AddressRead
    created_by_employee_id: int
    current_status: DeliveryStatusRead
    declared_weight_kg: Decimal
    declared_value: Decimal
    description: Optional[str]
    base_cost: Decimal
    extra_cost: Decimal
    total_cost: Decimal
    sender_courier_required: bool
    recipient_courier_required: bool
    recipient_courier_address: Optional[AddressRead] = None
    created_at: datetime
    delivered_at: Optional[datetime]
    assignments: list[CourierAssignmentRead] = []


class DeliveryStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: int
    delivery_id: int
    changed_at: datetime
    comment: Optional[str]
    old_status: Optional[DeliveryStatusRead]
    new_status: DeliveryStatusRead
    changed_by_employee_id: Optional[int]


class UserProfile(BaseModel):
    user_id: int
    login: str
    role: str
    effective_role: str
    created_at: datetime
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    client_id: Optional[int] = None
    client_status: Optional[str] = None
    registered_at: Optional[datetime] = None
    employee_id: Optional[int] = None
    employee_role: Optional[str] = None
    hired_at: Optional[date] = None
    is_active: Optional[bool] = None
    branch_id: Optional[int] = None
    branch: Optional[BranchRead] = None
    transport_type: Optional[str] = None
    capacity_kg: Optional[Decimal] = None
    permissions: dict[str, bool]


class LoginPageUser(BaseModel):
    user_id: int
    login: str
    role: str
    effective_role: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    client_status: Optional[str] = None
    employee_role: Optional[str] = None
    password_hint: Optional[str] = None


class EmployeeSeedCreate(BaseModel):
    login: str
    password: str
    full_name: str
    phone: str
    email: EmailStr
    branch_id: int
    employee_role: str
    transport_type: Optional[str] = None
    capacity_kg: Optional[Decimal] = None
    is_active: bool = True


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    user_id: int
    person_id: int
    branch_id: int
    employee_role: str
    hired_at: date
    is_active: bool


class AdminAccountCreate(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=3, max_length=120)
    phone: str = Field(min_length=5, max_length=20)
    email: EmailStr
    role: str = Field(pattern="^(client|employee|admin|courier)$")
    client_status: str = Field(default="active", pattern="^(active|inactive)$", max_length=20)
    branch_id: Optional[int] = None
    employee_role: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = True
    transport_type: Optional[str] = Field(default=None, pattern="^(foot|bicycle|motorcycle|car|truck)$", max_length=50)
    capacity_kg: Optional[Decimal] = Field(default=None, gt=0, max_digits=8, decimal_places=2)


class AdminAccountRead(BaseModel):
    user_id: int
    login: str
    role: str
    person_id: int
    client_id: Optional[int] = None
    employee_id: Optional[int] = None
    courier_id: Optional[int] = None

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base


class UserAccount(Base):
    __tablename__ = "users_account"

    user_id = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    client = relationship("Client", back_populates="user", uselist=False)
    employee = relationship("Employee", back_populates="user", uselist=False)


class Address(Base):
    __tablename__ = "addresses"

    address_id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False)
    street = Column(String(100), nullable=False)
    house = Column(String(20), nullable=False)
    apartment = Column(String(20), nullable=True)
    postal_code = Column(String(20), nullable=True)
    comment = Column(String(255), nullable=True)


class Branch(Base):
    __tablename__ = "branches"

    branch_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    address_id = Column(Integer, ForeignKey("addresses.address_id"), unique=True, nullable=False)

    address = relationship("Address")
    employees = relationship("Employee", back_populates="branch")


class Person(Base):
    __tablename__ = "persons"

    person_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    client = relationship("Client", back_populates="person", uselist=False)
    employee = relationship("Employee", back_populates="person", uselist=False)


class Client(Base):
    __tablename__ = "clients"

    client_id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.person_id"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users_account.user_id"), unique=True, nullable=True)
    client_status = Column(String(20), nullable=False, default="active")
    registered_at = Column(DateTime, nullable=False, server_default=func.now())

    person = relationship("Person", back_populates="client")
    user = relationship("UserAccount", back_populates="client")


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_account.user_id"), unique=True, nullable=False)
    person_id = Column(Integer, ForeignKey("persons.person_id"), unique=True, nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.branch_id"), nullable=False)
    employee_role = Column(String(20), nullable=False)
    hired_at = Column(Date, nullable=False, server_default=func.current_date())
    is_active = Column(Boolean, nullable=False, default=True)

    user = relationship("UserAccount", back_populates="employee")
    person = relationship("Person", back_populates="employee")
    branch = relationship("Branch", back_populates="employees")
    courier = relationship("Courier", back_populates="employee", uselist=False)


class Courier(Base):
    __tablename__ = "couriers"

    employee_id = Column(Integer, ForeignKey("employees.employee_id"), primary_key=True)
    transport_type = Column(String(50), nullable=False)
    capacity_kg = Column(Numeric(8, 2), nullable=False)

    employee = relationship("Employee", back_populates="courier")


class DeliveryStatus(Base):
    __tablename__ = "delivery_statuses"

    status_id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False)


class Delivery(Base):
    __tablename__ = "deliveries"

    delivery_id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(30), unique=True, nullable=False, index=True)
    sender_client_id = Column(Integer, ForeignKey("clients.client_id"), nullable=False)
    recipient_client_id = Column(Integer, ForeignKey("clients.client_id"), nullable=False)
    origin_branch_id = Column(Integer, ForeignKey("branches.branch_id"), nullable=False)
    destination_branch_id = Column(Integer, ForeignKey("branches.branch_id"), nullable=False)
    sender_address_id = Column(Integer, ForeignKey("addresses.address_id"), nullable=False)
    recipient_address_id = Column(Integer, ForeignKey("addresses.address_id"), nullable=False)
    created_by_employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    current_status_id = Column(Integer, ForeignKey("delivery_statuses.status_id"), nullable=False)
    declared_weight_kg = Column(Numeric(8, 2), nullable=False)
    declared_value = Column(Numeric(10, 2), nullable=False)
    description = Column(String(255), nullable=True)
    base_cost = Column(Numeric(10, 2), nullable=False, default=0)
    extra_cost = Column(Numeric(10, 2), nullable=False, default=0)
    total_cost = Column(Numeric(10, 2), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    delivered_at = Column(DateTime, nullable=True)

    sender = relationship("Client", foreign_keys=[sender_client_id])
    recipient = relationship("Client", foreign_keys=[recipient_client_id])
    origin_branch = relationship("Branch", foreign_keys=[origin_branch_id])
    destination_branch = relationship("Branch", foreign_keys=[destination_branch_id])
    sender_address = relationship("Address", foreign_keys=[sender_address_id])
    recipient_address = relationship("Address", foreign_keys=[recipient_address_id])
    creator = relationship("Employee", foreign_keys=[created_by_employee_id])
    current_status = relationship("DeliveryStatus")
    assignments = relationship("DeliveryCourierAssignment", back_populates="delivery")
    status_history = relationship(
        "DeliveryStatusHistory",
        back_populates="delivery",
        order_by="DeliveryStatusHistory.changed_at",
    )

    @property
    def sender_courier_required(self) -> bool:
        return any(item.service_type == "pickup" for item in self.assignments)

    @property
    def recipient_courier_required(self) -> bool:
        return any(item.service_type == "delivery" for item in self.assignments)

    @property
    def recipient_courier_address(self):
        for item in self.assignments:
            if item.service_type == "delivery":
                return item.call_address
        return None


class DeliveryCourierAssignment(Base):
    __tablename__ = "delivery_courier_assignments"

    assignment_id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.delivery_id"), nullable=False)
    courier_id = Column(Integer, ForeignKey("couriers.employee_id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.client_id"), nullable=False)
    service_type = Column(String(20), nullable=False)
    call_address_id = Column(Integer, ForeignKey("addresses.address_id"), nullable=False)
    service_cost = Column(Numeric(10, 2), nullable=False)
    assigned_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    delivery = relationship("Delivery", back_populates="assignments")
    courier = relationship("Courier")
    client = relationship("Client")
    call_address = relationship("Address")


class DeliveryStatusHistory(Base):
    __tablename__ = "delivery_status_history"

    history_id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.delivery_id"), nullable=False)
    old_status_id = Column(Integer, ForeignKey("delivery_statuses.status_id"), nullable=True)
    new_status_id = Column(Integer, ForeignKey("delivery_statuses.status_id"), nullable=False)
    changed_by_employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)
    changed_at = Column(DateTime, nullable=False, server_default=func.now())
    comment = Column(String(255), nullable=True)

    delivery = relationship("Delivery", back_populates="status_history")
    old_status = relationship("DeliveryStatus", foreign_keys=[old_status_id])
    new_status = relationship("DeliveryStatus", foreign_keys=[new_status_id])
    changed_by = relationship("Employee", foreign_keys=[changed_by_employee_id])

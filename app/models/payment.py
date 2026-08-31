import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Currency(str, enum.Enum):
    USD = "USD"
    KHR = "KHR"


class PaymentType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    FULL_PAYMENT = "FULL_PAYMENT"
    BALANCE = "BALANCE"
    REFUND = "REFUND"


class PaymentMethod(str, enum.Enum):
    KHQR = "KHQR"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class CallbackStatus(str, enum.Enum):
    NOT_SENT = "NOT_SENT"
    SENT = "SENT"
    FAILED = "FAILED"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    booking_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(Enum(Currency), nullable=False)
    payment_type: Mapped[PaymentType] = mapped_column(Enum(PaymentType), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod), default=PaymentMethod.KHQR, nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True, nullable=False
    )

    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    merchant_reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    transaction_ref: Mapped[str | None] = mapped_column(String(255), unique=True)
    khqr_hash: Mapped[str | None] = mapped_column(String(255), unique=True)
    qr_payload: Mapped[str | None] = mapped_column(Text)

    callback_status: Mapped[CallbackStatus] = mapped_column(
        Enum(CallbackStatus), default=CallbackStatus.NOT_SENT, nullable=False
    )
    callback_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(500))

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_callback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

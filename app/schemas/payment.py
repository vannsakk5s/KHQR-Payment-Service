from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import (
    CallbackStatus,
    Currency,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
)


class CreatePaymentRequest(BaseModel):
    booking_id: int = Field(gt=0)
    customer_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: Currency
    payment_type: PaymentType
    payment_method: PaymentMethod = PaymentMethod.KHQR
    idempotency_key: str = Field(min_length=8, max_length=100)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    booking_id: int
    customer_id: int
    amount: Decimal
    currency: Currency
    payment_type: PaymentType
    payment_method: PaymentMethod
    status: PaymentStatus
    merchant_reference: str
    transaction_ref: str | None
    khqr_hash: str | None
    qr_payload: str | None
    callback_status: CallbackStatus
    expires_at: datetime | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VerifyPaymentResponse(BaseModel):
    payment: PaymentResponse
    hotel_notified: bool


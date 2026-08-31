import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import require_internal_api_key
from app.models.payment import CallbackStatus, Payment, PaymentStatus
from app.schemas.payment import (
    CreatePaymentRequest,
    PaymentResponse,
    VerifyPaymentResponse,
)
from app.services.hotel_client import notify_hotel
from app.services.khqr import MockKhqrProvider, get_khqr_provider


router = APIRouter(
    prefix="/api/v1/payments",
    tags=["Payments"],
    dependencies=[Depends(require_internal_api_key)],
)


def find_payment_or_404(payment_id: str, db: Session) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(request: CreatePaymentRequest, db: Session = Depends(get_db)):
    existing = db.scalar(
        select(Payment).where(Payment.idempotency_key == request.idempotency_key)
    )
    if existing:
        return existing

    merchant_reference = f"HTL-{request.booking_id}-{uuid.uuid4().hex[:10]}"
    provider = get_khqr_provider()
    try:
        khqr = provider.create_payment_qr(
            amount=request.amount,
            currency=request.currency,
            merchant_reference=merchant_reference,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"KHQR provider error: {exc}") from exc

    payment = Payment(
        booking_id=request.booking_id,
        customer_id=request.customer_id,
        amount=request.amount,
        currency=request.currency,
        payment_type=request.payment_type,
        payment_method=request.payment_method,
        idempotency_key=request.idempotency_key,
        merchant_reference=merchant_reference,
        khqr_hash=khqr.khqr_hash,
        qr_payload=khqr.qr_payload,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=get_settings().khqr_ttl_minutes),
    )
    db.add(payment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate payment reference") from exc
    db.refresh(payment)
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    return find_payment_or_404(payment_id, db)


@router.get("/booking/{booking_id}", response_model=list[PaymentResponse])
def get_booking_payments(booking_id: int, db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(Payment)
            .where(Payment.booking_id == booking_id)
            .order_by(Payment.created_at.desc())
        )
    )


@router.post("/{payment_id}/verify", response_model=VerifyPaymentResponse)
def verify_payment(payment_id: str, db: Session = Depends(get_db)):
    payment = find_payment_or_404(payment_id, db)

    if payment.status == PaymentStatus.PAID:
        return VerifyPaymentResponse(
            payment=payment,
            hotel_notified=payment.callback_status == CallbackStatus.SENT,
        )

    now = datetime.now(timezone.utc)
    expires_at = payment.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and now > expires_at:
        payment.status = PaymentStatus.EXPIRED
        db.commit()
        db.refresh(payment)
        return VerifyPaymentResponse(payment=payment, hotel_notified=False)

    try:
        verification = get_khqr_provider().check_payment(payment.khqr_hash or "")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"KHQR provider error: {exc}") from exc

    hotel_notified = False
    if verification.paid:
        amount_mismatch = (
            verification.amount is not None and verification.amount != payment.amount
        )
        currency_mismatch = (
            verification.currency is not None
            and verification.currency.upper() != payment.currency.value
        )
        receiver_mismatch = (
            verification.receiver_account_id is not None
            and get_settings().bakong_account_id
            and verification.receiver_account_id != get_settings().bakong_account_id
        )
        if amount_mismatch or currency_mismatch or receiver_mismatch:
            payment.status = PaymentStatus.REVIEW_REQUIRED
            payment.failure_reason = (
                "Verified KHQR transaction details do not match payment"
            )
            db.commit()
            db.refresh(payment)
            return VerifyPaymentResponse(payment=payment, hotel_notified=False)

        payment.status = PaymentStatus.PAID
        payment.transaction_ref = (
            verification.transaction_ref or f"KHQR-{payment.khqr_hash}"
        )
        payment.paid_at = now
        db.commit()
        db.refresh(payment)

        payment.callback_attempts += 1
        payment.last_callback_at = now
        hotel_notified = notify_hotel(payment)
        payment.callback_status = (
            CallbackStatus.SENT if hotel_notified else CallbackStatus.FAILED
        )
        db.commit()
        db.refresh(payment)

    return VerifyPaymentResponse(payment=payment, hotel_notified=hotel_notified)


@router.post("/{payment_id}/mock-paid", response_model=VerifyPaymentResponse)
def mark_mock_payment_paid(payment_id: str, db: Session = Depends(get_db)):
    settings = get_settings()
    provider = get_khqr_provider()
    if settings.app_env.lower() == "production" or not isinstance(provider, MockKhqrProvider):
        raise HTTPException(status_code=404, detail="Not found")

    payment = find_payment_or_404(payment_id, db)
    provider.mark_paid(payment.khqr_hash or "")
    return verify_payment(payment_id, db)

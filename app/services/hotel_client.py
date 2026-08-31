import httpx

from app.core.config import get_settings
from app.models.payment import Payment


def notify_hotel(payment: Payment) -> bool:
    settings = get_settings()
    if not settings.hotel_api_base_url:
        return False

    path = settings.hotel_callback_path.format(booking_id=payment.booking_id)
    payload = {
        "paymentId": payment.id,
        "bookingId": payment.booking_id,
        "amount": str(payment.amount),
        "currency": payment.currency.value,
        "paymentType": payment.payment_type.value,
        "transactionRef": payment.transaction_ref,
        "paidAt": payment.paid_at.isoformat() if payment.paid_at else None,
    }
    headers = {"X-Service-API-Key": settings.hotel_service_api_key}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{settings.hotel_api_base_url.rstrip('/')}{path}",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


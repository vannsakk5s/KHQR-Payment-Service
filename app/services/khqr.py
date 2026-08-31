import hashlib
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.models.payment import Currency


@dataclass(frozen=True)
class KhqrResult:
    qr_payload: str
    khqr_hash: str


@dataclass(frozen=True)
class KhqrVerification:
    paid: bool
    transaction_ref: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    receiver_account_id: str | None = None


class KhqrProvider:
    def create_payment_qr(
        self, *, amount: Decimal, currency: Currency, merchant_reference: str
    ) -> KhqrResult:
        raise NotImplementedError

    def check_payment(self, khqr_hash: str) -> KhqrVerification:
        raise NotImplementedError


class MockKhqrProvider(KhqrProvider):
    def __init__(self) -> None:
        self._paid_hashes: set[str] = set()
        self._payments: dict[str, tuple[Decimal, str]] = {}

    def create_payment_qr(
        self, *, amount: Decimal, currency: Currency, merchant_reference: str
    ) -> KhqrResult:
        payload = f"MOCK-KHQR|{merchant_reference}|{currency.value}|{amount:.2f}"
        result = KhqrResult(
            qr_payload=payload,
            khqr_hash=hashlib.md5(payload.encode(), usedforsecurity=False).hexdigest(),
        )
        self._payments[result.khqr_hash] = (amount, currency.value)
        return result

    def check_payment(self, khqr_hash: str) -> KhqrVerification:
        amount, currency = self._payments.get(khqr_hash, (None, None))
        return KhqrVerification(
            paid=khqr_hash in self._paid_hashes,
            amount=amount,
            currency=currency,
        )

    def mark_paid(self, khqr_hash: str) -> None:
        self._paid_hashes.add(khqr_hash)


class BakongKhqrProvider(KhqrProvider):
    """Adapter around a community Python KHQR SDK.

    For production, confirm the SDK version and API/network requirements with
    NBC or your acquiring bank before enabling this provider.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.bakong_token or not settings.bakong_account_id:
            raise RuntimeError("BAKONG_TOKEN and BAKONG_ACCOUNT_ID are required")
        try:
            from bakong_khqr import KHQR
        except ImportError as exc:
            raise RuntimeError(
                'Install the real provider dependency: pip install ".[bakong]"'
            ) from exc
        self.settings = settings
        self.client = KHQR(settings.bakong_token)

    def create_payment_qr(
        self, *, amount: Decimal, currency: Currency, merchant_reference: str
    ) -> KhqrResult:
        qr = self.client.create_qr(
            account_id=self.settings.bakong_account_id,
            merchant_name=self.settings.bakong_merchant_name,
            merchant_city=self.settings.bakong_merchant_city,
            amount=float(amount),
            currency=currency.value,
            store_label=self.settings.bakong_store_label,
            phone_number=self.settings.bakong_phone_number or None,
            bill_number=merchant_reference[:25],
            terminal_label="HOTEL-API",
            static=False,
            expiration=max(1, int(self.settings.khqr_ttl_minutes / 1440)),
        )
        return KhqrResult(qr_payload=qr, khqr_hash=self.client.generate_md5(qr))

    def check_payment(self, khqr_hash: str) -> KhqrVerification:
        status = self.client.check_payment(khqr_hash)
        paid = str(status).upper() == "PAID"
        if not paid:
            return KhqrVerification(paid=False)

        details = self.client.get_payment(khqr_hash) or {}
        raw_amount = details.get("amount")
        return KhqrVerification(
            paid=True,
            transaction_ref=details.get("externalRef") or details.get("hash"),
            amount=Decimal(str(raw_amount)) if raw_amount is not None else None,
            currency=details.get("currency"),
            receiver_account_id=details.get("toAccountId"),
        )


@lru_cache
def get_khqr_provider() -> KhqrProvider:
    settings = get_settings()
    if settings.khqr_provider.lower() == "bakong":
        return BakongKhqrProvider(settings)
    return MockKhqrProvider()

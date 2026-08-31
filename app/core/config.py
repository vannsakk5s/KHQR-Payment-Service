from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hotel KHQR Payment Service"
    app_env: str = "development"
    database_url: str = "sqlite:///./payments.db"
    internal_api_key: str = "dev-only-change-me"

    khqr_provider: str = "mock"
    khqr_ttl_minutes: int = 10

    bakong_token: str = ""
    bakong_account_id: str = ""
    bakong_merchant_name: str = "Your Hotel"
    bakong_merchant_city: str = "Phnom Penh"
    bakong_store_label: str = "Hotel Booking"
    bakong_phone_number: str = ""

    hotel_api_base_url: str = ""
    hotel_callback_path: str = (
        "/api/v1/internal/bookings/{booking_id}/payment-confirmed"
    )
    hotel_service_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


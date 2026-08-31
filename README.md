# Hotel KHQR Payment Service

FastAPI microservice សម្រាប់ភ្ជាប់ Hotel Booking Server ជាមួយ KHQR។ Project នេះ
ចាប់ផ្ដើមជា `mock` ដើម្បី test payment flow ហើយអាចប្ដូរទៅ Bakong provider ពេលមាន
Developer Token និង Merchant/Bakong Account។

> Security: កុំដាក់ Bakong token ក្នុង Git, Vue ឬ Flutter។ Hotel Server ប៉ុណ្ណោះ
> ដែលគួរហៅ Payment Server ដោយប្រើ `X-Internal-API-Key`។

## Architecture

```text
Vue / Flutter -> Hotel Spring Boot -> FastAPI Payment -> Bakong KHQR
                                      |
                                      +-> PostgreSQL
```

Payment Server ជា source of truth សម្រាប់ payment status។ Hotel Server ជា source
of truth សម្រាប់ booking status។ `booking_id` នៅ Payment DB ជា external reference
មិនមែន cross-database foreign key ទេ។

## 1. Local setup

តម្រូវការ៖ Python 3.11+។

```bash
cd khqr-payment-service
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
pip install -e ".[test]"
uvicorn app.main:app --reload
```

Git Bash:

```bash
source .venv/Scripts/activate
cp .env.example .env
pip install -e '.[test]'
uvicorn app.main:app --reload
```

បើក៖

- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

នៅ Swagger ចុច endpoint ហើយដាក់ header៖

```text
X-Internal-API-Key: change-this-long-random-key
```

តម្លៃនេះត្រូវដូច `INTERNAL_API_KEY` ក្នុង `.env`។

## 2. Test payment flow

Create deposit payment៖

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-Internal-API-Key: change-this-long-random-key" \
  -d '{
    "booking_id": 2,
    "customer_id": 6,
    "amount": 30.00,
    "currency": "USD",
    "payment_type": "DEPOSIT",
    "payment_method": "KHQR",
    "idempotency_key": "booking-2-deposit-v1"
  }'
```

Copy `id` ពី response ហើយ simulate payment៖

```bash
curl -X POST http://localhost:8000/api/v1/payments/PAYMENT_ID/mock-paid \
  -H "X-Internal-API-Key: change-this-long-random-key"
```

`mock-paid` មានតែនៅ `APP_ENV=development` និង `KHQR_PROVIDER=mock` ប៉ុណ្ណោះ។

## 3. Docker + PostgreSQL

```bash
cp .env.example .env
docker compose up --build -d
docker compose logs -f payment-api
```

PostgreSQL មិនត្រូវ expose port ទៅ public Internet។ Production ត្រូវប្ដូរ database
password និង internal API keys ទាំងអស់។

## 4. Enable real Bakong adapter

Python KHQR package ក្នុង starter នេះជា community adapter មិនមែន official NBC
Python SDK ទេ។ ត្រូវ verify version, account eligibility, server network access និង
production terms ជាមួយ NBC ឬ bank partner មុនប្រើប្រាក់ពិត។

```bash
pip install -e '.[bakong]'
```

កែ `.env`៖

```env
APP_ENV=production
KHQR_PROVIDER=bakong
BAKONG_TOKEN=your-real-token
BAKONG_ACCOUNT_ID=your_name@bank
BAKONG_MERCHANT_NAME=Your Hotel
BAKONG_MERCHANT_CITY=Phnom Penh
```

Official references:

- https://bakong.nbc.gov.kh/
- https://api-bakong.nbc.gov.kh/document

## 5. Hotel Server request

Hotel Server ត្រូវយក amount ពី booking ក្នុង database របស់វា ហើយបញ្ជូនទៅ Payment
Server។ កុំទុកចិត្ត amount ដែល Vue/Flutter ផ្ញើមក។

```json
{
  "booking_id": 2,
  "customer_id": 6,
  "amount": 30.00,
  "currency": "USD",
  "payment_type": "DEPOSIT",
  "payment_method": "KHQR",
  "idempotency_key": "booking-2-deposit-v1"
}
```

ពេល verify បាន `PAID`, Payment Server នឹង POST ទៅ៖

```text
{HOTEL_API_BASE_URL}/api/v1/internal/bookings/{booking_id}/payment-confirmed
```

Hotel Server ត្រូវ verify `X-Service-API-Key`, amount, currency, payment ID និង
ការពារ callback ដដែលកុំឱ្យ confirm booking ពីរដង។

## 6. Run tests

```bash
pytest -q
```

## Before production

- Replace automatic `create_all` with Alembic migrations.
- Use HTTPS through Nginx and keep port 8000 private when possible.
- Use a strong random service key and rotate it.
- Add callback retry/background worker (Celery, RQ, or scheduled job).
- Add structured logs, rate limiting, monitoring and database backups.
- Re-check room hold before confirming booking; define refund/compensation flow.
- Do not log tokens, full QR payloads, or sensitive transaction data.
# KHQR-Payment-Service

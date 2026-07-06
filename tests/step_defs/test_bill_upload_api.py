from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from model_bakery import baker
from pytest_bdd import given, parsers, scenario, then, when

from accounts.models import Bill

TOKEN = "test-bill-upload-token"  # noqa: S105
BILL_DATA = {
    "name": "Brico - visserie",
    "amount": "123.45",
    "date": "2026-07-01",
    "category": "6010",
    "iban": "BE71096123456769",
}


@scenario("bill_upload_api.feature", "A bill is created with a valid token")
def test_bill_created(db):
    pass


@scenario("bill_upload_api.feature", "A request with a wrong token is rejected")
def test_wrong_token_rejected(db):
    pass


@scenario("bill_upload_api.feature", "The API is disabled when no token is configured")
def test_no_token_configured(db):
    pass


@scenario("bill_upload_api.feature", "Invalid data is rejected")
def test_invalid_data_rejected(db):
    pass


@scenario("bill_upload_api.feature", "Duplicate bills are rejected")
def test_duplicate_rejected(db):
    pass


@given("the bill upload API is configured with a token")
def configured_token(settings, tmp_path):
    settings.BILL_UPLOAD_TOKEN = TOKEN
    settings.MEDIA_ROOT = tmp_path


@given("the bill upload API has no token configured")
def no_token(settings, tmp_path):
    settings.BILL_UPLOAD_TOKEN = ""
    settings.MEDIA_ROOT = tmp_path


@given("an identical bill already exists")
def existing_bill():
    bill = baker.make(Bill, name=BILL_DATA["name"], date=BILL_DATA["date"])
    bill.set_amount(Decimal(BILL_DATA["amount"]))


def _post_bill(client, token, data):
    payload = {
        **data,
        "file": SimpleUploadedFile("bill.pdf", b"%PDF-1.4 fake bill"),
    }
    return client.post(
        reverse("api_bill_upload"),
        payload,
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


@when(
    parsers.parse("I post a bill with {token_kind} token"),
    target_fixture="response",
)
def post_bill(client, token_kind):
    token = {
        "the valid": TOKEN,
        "a wrong": "wrong-token",
        "an empty": "",
    }[token_kind]
    return _post_bill(client, token, BILL_DATA)


@when("I post a bill without an amount", target_fixture="response")
def post_bill_without_amount(client):
    data = {k: v for k, v in BILL_DATA.items() if k != "amount"}
    return _post_bill(client, TOKEN, data)


@then("the bill is created with its document")
def check_bill_created(response):
    assert response.status_code == 201, response.content
    bill = Bill.objects.with_amounts().get(id=response.json()["id"])
    assert bill.name == BILL_DATA["name"]
    assert bill.amount == Decimal(BILL_DATA["amount"])
    assert bill.date.isoformat() == BILL_DATA["date"]
    assert bill.category == int(BILL_DATA["category"])
    assert bill.iban == BILL_DATA["iban"]
    assert bill.payments.get(operation__isnull=True).expected_iban == BILL_DATA["iban"]
    assert bill.file.read().startswith(b"%PDF")
    assert response.json()["admin_url"] == reverse(
        "admin:accounts_bill_change", args=[bill.id]
    )


@then("the request is rejected as unauthorized")
def check_unauthorized(response):
    assert response.status_code == 401


@then("the request is rejected with validation errors")
def check_validation_errors(response):
    assert response.status_code == 400
    assert "amount" in response.json()["errors"]


@then("the request is rejected as a duplicate")
def check_duplicate(response):
    assert response.status_code == 409
    assert Bill.objects.count() == 1


@then("no bill is created")
def check_no_bill():
    assert Bill.objects.count() == 0

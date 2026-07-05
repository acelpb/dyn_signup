from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from pytest_bdd import given, scenario, then, when

from accounts.models import ApiToken, Bill, DeviceAuthorization


@scenario(
    "device_auth.feature", "An assistant obtains a token approved by the treasurer"
)
def test_device_flow_happy_path(db):
    pass


@scenario("device_auth.feature", "The treasurer denies the request")
def test_device_flow_denied(db):
    pass


@scenario("device_auth.feature", "An expired device authorization yields no token")
def test_device_flow_expired(db):
    pass


@scenario("device_auth.feature", "A regular user cannot approve a device authorization")
def test_device_flow_regular_user(db):
    pass


@given("an assistant that started a device authorization", target_fixture="device")
def device(client, settings, tmp_path):
    settings.BILL_UPLOAD_TOKEN = ""
    settings.MEDIA_ROOT = tmp_path
    response = client.post(reverse("device_auth_start"), {"client_name": "Claude Code"})
    assert response.status_code == 201
    return response.json()


@given("the device authorization has expired")
def expire_device(device):
    DeviceAuthorization.objects.filter(device_code=device["device_code"]).update(
        expires_at=timezone.now() - timezone.timedelta(minutes=1)
    )


def _poll(client, device):
    return client.post(
        reverse("device_auth_token"), {"device_code": device["device_code"]}
    )


@then("polling for the token reports pending")
def poll_pending(client, device):
    response = _poll(client, device)
    assert response.status_code == 202
    assert response.json()["status"] == "pending"


@when("the treasurer approves the request on the verification page")
def approve(admin_client, device):
    response = admin_client.get(device["verification_url"])
    assert response.status_code == 200
    assert "Claude Code" in response.content.decode("utf-8")
    response = admin_client.post(device["verification_url"], {"action": "approve"})
    assert response.status_code == 200


@when("the treasurer denies the request on the verification page")
def deny(admin_client, device):
    response = admin_client.post(device["verification_url"], {"action": "deny"})
    assert response.status_code == 200
    assert ApiToken.objects.count() == 0


@then("polling for the token returns a token", target_fixture="token")
def poll_approved(client, device):
    response = _poll(client, device)
    assert response.status_code == 200, response.content
    data = response.json()
    assert data["status"] == "approved"
    token = ApiToken.objects.get()
    assert token.token_hash == ApiToken.hash_token(data["token"])
    assert data["token"] not in token.token_hash
    return data["token"]


@then("the token can be used to upload a bill")
def upload_with_token(client, token):
    response = client.post(
        reverse("api_bill_upload"),
        {
            "name": "Brico - visserie",
            "amount": "12.34",
            "date": "2026-07-01",
            "file": SimpleUploadedFile("bill.pdf", b"%PDF-1.4 fake bill"),
        },
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 201, response.content
    assert Bill.objects.count() == 1


@then("polling again is rejected")
def poll_again_rejected(client, device):
    response = _poll(client, device)
    assert response.status_code == 400
    assert response.json()["status"] == "invalid"


@then("polling for the token reports the code as invalid")
def poll_invalid(client, device):
    response = _poll(client, device)
    assert response.status_code == 400
    assert response.json()["status"] == "invalid"


@then("polling for the token reports the code as expired")
def poll_expired(client, device):
    response = _poll(client, device)
    assert response.status_code == 400
    assert response.json()["status"] == "expired"
    assert not DeviceAuthorization.objects.exists()


@when("the participant opens the verification page", target_fixture="response")
def participant_opens(client, participant, device):
    client.force_login(participant)
    return client.get(device["verification_url"])


@then("the verification page access is denied")
def verification_denied(response):
    assert response.status_code == 403

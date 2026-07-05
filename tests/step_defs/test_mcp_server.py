import base64
import json
import re
from decimal import Decimal

from django.urls import reverse
from model_bakery import baker
from pytest_bdd import given, scenario, then, when

from accounts.models import ApiToken, Bill

BILL_ARGS = {"name": "Brico - visserie", "amount": "123.45", "date": "2026-07-01"}


@scenario(
    "mcp_server.feature", "An assistant initializes and discovers the upload tool"
)
def test_mcp_initialize_and_list(db):
    pass


@scenario(
    "mcp_server.feature", "An assistant uploads a bill with its document through MCP"
)
def test_mcp_upload_bill(db):
    pass


@scenario("mcp_server.feature", "A duplicate upload through MCP is rejected")
def test_mcp_duplicate(db):
    pass


@scenario("mcp_server.feature", "A wrong token is rejected")
def test_mcp_wrong_token(db):
    pass


@scenario(
    "mcp_server.feature", "The treasurer generates a connector token in the browser"
)
def test_token_page(db):
    pass


@scenario("mcp_server.feature", "A regular user cannot generate a token")
def test_token_page_denied(db):
    pass


def _rpc(client, token, method, params=None, message_id=1):
    return client.post(
        reverse("mcp_server", args=[token]),
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": message_id,
                "method": method,
                "params": params or {},
            }
        ),
        content_type="application/json",
    )


@given("an issued API token", target_fixture="raw_token")
def raw_token(db, settings, tmp_path):
    settings.BILL_UPLOAD_TOKEN = ""
    settings.MEDIA_ROOT = tmp_path
    _, raw = ApiToken.issue(name="test connector", user=None)
    return raw


@given("an identical bill already exists")
def existing_bill():
    baker.make(
        Bill,
        name=BILL_ARGS["name"],
        amount=Decimal(BILL_ARGS["amount"]),
        date=BILL_ARGS["date"],
    )


@when("the assistant initializes the MCP session", target_fixture="response")
def initialize(client, raw_token):
    return _rpc(
        client,
        raw_token,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    )


@then("the server introduces itself with its protocol version")
def check_initialize(response):
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["protocolVersion"] == "2025-06-18"
    assert result["serverInfo"]["name"] == "dyn-signup"
    assert "tools" in result["capabilities"]


@when("the assistant lists the MCP tools", target_fixture="response")
def list_tools(client, raw_token):
    return _rpc(client, raw_token, "tools/list")


@then("the upload_bill tool is listed")
def check_tools(response):
    tools = response.json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["upload_bill"]
    assert set(tools[0]["inputSchema"]["required"]) == {"name", "amount", "date"}


@when("the assistant calls upload_bill with a document", target_fixture="response")
def call_upload_bill(client, raw_token):
    return _rpc(
        client,
        raw_token,
        "tools/call",
        {
            "name": "upload_bill",
            "arguments": {
                **BILL_ARGS,
                "file_base64": base64.b64encode(b"%PDF-1.4 fake bill").decode(),
                "filename": "facture.pdf",
            },
        },
    )


@then("the MCP call succeeds and the bill is created with its document")
def check_bill_created(response):
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    bill = Bill.objects.get(id=payload["id"])
    assert bill.amount == Decimal(BILL_ARGS["amount"])
    assert bill.file.read().startswith(b"%PDF")
    assert payload["document_attached"] is True
    assert payload["admin_url"].startswith("http")


@then("the MCP call reports an error mentioning the duplicate")
def check_duplicate(response):
    result = response.json()["result"]
    assert result["isError"] is True
    assert "already exists" in result["content"][0]["text"]
    assert Bill.objects.count() == 1


@when(
    "the assistant calls the MCP endpoint with a wrong token", target_fixture="response"
)
def call_wrong_token(client):
    return _rpc(client, "wrong-token", "tools/list")


@then("the MCP request is rejected as unauthorized")
def check_unauthorized(response):
    assert response.status_code == 401


@when("the treasurer generates a token on the token page", target_fixture="response")
def generate_token(admin_client, settings, tmp_path):
    settings.BILL_UPLOAD_TOKEN = ""
    settings.MEDIA_ROOT = tmp_path
    return admin_client.post(reverse("api_token_create"), {"name": "Mon connecteur"})


@then("the page shows the MCP URL once and the token works")
def check_token_page(response, client):
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    match = re.search(r"/mcp/([A-Za-z0-9_-]+)/", content)
    assert match, "MCP URL not found on the page"
    rpc_response = _rpc(client, match.group(1), "tools/list")
    assert rpc_response.status_code == 200
    assert ApiToken.objects.count() == 1


@when("the participant opens the token page", target_fixture="response")
def participant_opens(client, participant):
    client.force_login(participant)
    return client.get(reverse("api_token_create"))


@then("the token page access is denied")
def check_denied(response):
    assert response.status_code == 403

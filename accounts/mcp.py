"""Minimal MCP (Model Context Protocol) server over streamable HTTP.

Implements just enough JSON-RPC for LLM clients (claude.ai custom
connectors, Claude Code) to list and call tools. The server is stateless:
every POST carries one JSON-RPC message and gets a plain JSON response,
which the MCP spec allows for servers that never push notifications.

Authentication: the URL contains a plaintext API token (claude.ai custom
connectors cannot send custom headers without OAuth), verified against the
hashed ApiToken store on every request.
"""

import base64
import binascii
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from accounts.forms import try_create_bill
from accounts.models import ExpenditureChoices, authenticate_api_token

PROTOCOL_VERSION = "2025-06-18"
MAX_FILE_BYTES = 5 * 1024 * 1024

UPLOAD_BILL_TOOL = {
    "name": "upload_bill",
    "description": (
        "Create a bill (facture) in the Dynamobile accounting tool. "
        "Confirm the extracted fields with the user before calling. "
        "Duplicates (same name, amount and date) are rejected."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Short label: vendor + what it is, e.g. "
                "'Brico - matériel signalisation'. Append the invoice "
                "number if visible.",
            },
            "amount": {
                "type": "string",
                "description": "Total including VAT, positive decimal with "
                "a dot separator, e.g. '123.45'.",
            },
            "date": {
                "type": "string",
                "description": "Invoice/bill date (not the due date), "
                "ISO format YYYY-MM-DD.",
            },
            "category": {
                "type": "string",
                "description": "Optional accounting category code: "
                + "; ".join(
                    f"{choice.value}={choice.label}" for choice in ExpenditureChoices
                )
                + ". Pick the closest match; omit when unsure.",
            },
            "iban": {
                "type": "string",
                "description": "Optional: the vendor IBAN to pay the bill "
                "to, if printed on the document.",
            },
            "file_base64": {
                "type": "string",
                "description": "Optional: the bill document (PDF/image) "
                "encoded in base64.",
            },
            "filename": {
                "type": "string",
                "description": "Filename for the document, e.g. 'facture.pdf'.",
            },
        },
        "required": ["name", "amount", "date"],
    },
}


def _error(message_id, code, message):
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }


def _tool_text(payload, is_error=False):
    return {
        "content": [{"type": "text", "text": json.dumps(payload)}],
        "isError": is_error,
    }


@method_decorator(csrf_exempt, name="dispatch")
class McpServerView(View):
    http_method_names = ["post", "get"]

    def get(self, request, token):
        # No server-initiated stream: stateless JSON responses only.
        return HttpResponse(status=405)

    def post(self, request, token):
        if not authenticate_api_token(token):
            return JsonResponse({"error": "Invalid token."}, status=401)
        try:
            message = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(_error(None, -32700, "Parse error"), status=400)
        if not isinstance(message, dict):
            return JsonResponse(
                _error(None, -32600, "Batch messages are not supported"), status=400
            )

        message_id = message.get("id")
        if message_id is None:
            # Notification (e.g. notifications/initialized): acknowledge.
            return HttpResponse(status=202)

        method = message.get("method")
        if method == "initialize":
            result = self._initialize(message)
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [UPLOAD_BILL_TOOL]}
        elif method == "tools/call":
            result = self._call_tool(request, message)
        else:
            return JsonResponse(
                _error(message_id, -32601, f"Method not found: {method}")
            )
        return JsonResponse({"jsonrpc": "2.0", "id": message_id, "result": result})

    def _initialize(self, message):
        client_version = (message.get("params") or {}).get("protocolVersion")
        return {
            "protocolVersion": client_version or PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "dyn-signup", "version": "1.0.0"},
        }

    def _call_tool(self, request, message):
        params = message.get("params") or {}
        if params.get("name") != "upload_bill":
            return _tool_text(
                {"error": f"Unknown tool: {params.get('name')}"}, is_error=True
            )
        arguments = params.get("arguments") or {}

        uploaded_file = None
        if file_base64 := arguments.get("file_base64"):
            try:
                content = base64.b64decode(file_base64, validate=True)
            except (binascii.Error, ValueError):
                return _tool_text(
                    {"error": "file_base64 is not valid base64."}, is_error=True
                )
            if len(content) > MAX_FILE_BYTES:
                return _tool_text({"error": "Document larger than 5MB."}, is_error=True)
            uploaded_file = SimpleUploadedFile(
                arguments.get("filename") or "facture.pdf", content
            )

        result = try_create_bill(
            {
                key: arguments.get(key)
                for key in ("name", "amount", "date", "category", "iban")
                if arguments.get(key)
            },
            {"file": uploaded_file} if uploaded_file else None,
            require_file=False,
        )
        if result["status"] == "invalid":
            return _tool_text({"errors": result["errors"]}, is_error=True)
        if result["status"] == "duplicate":
            return _tool_text(
                {
                    "error": "A bill with the same name, amount and date already "
                    "exists. Do not resubmit unless the user confirms it is a "
                    "different bill.",
                    "existing_ids": result["existing_ids"],
                },
                is_error=True,
            )

        bill = result["bill"]
        return _tool_text(
            {
                "id": bill.id,
                "name": bill.name,
                "amount": str(bill.amount),
                "date": bill.date.isoformat(),
                "category": bill.category,
                "iban": bill.iban,
                "document_attached": bool(uploaded_file),
                "admin_url": request.build_absolute_uri(
                    reverse("admin:accounts_bill_change", args=[bill.id])
                ),
            }
        )

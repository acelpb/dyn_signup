# Create your views here.
import datetime
import re
import secrets
from collections import defaultdict

from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin
from django.db.models import (
    BooleanField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
)
from django.db.models.functions import Round
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from accounts.forms import try_create_bill
from accounts.models import (
    ApiToken,
    Bill,
    DeviceAuthorization,
    ExpenditureChoices,
    ExpenseReport,
    IncomeChoices,
    Operation,
    OperationValidation,
    authenticate_api_token,
)

DEVICE_AUTH_LIFETIME = datetime.timedelta(minutes=15)
DEVICE_AUTH_POLL_INTERVAL = 5


class TreasurerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.groups.filter(name="Trésorier").exists()


def _normalize_iban(value):
    return re.sub(r"\s", "", value or "").upper()


@method_decorator(csrf_exempt, name="dispatch")
class BillUploadAPIView(View):
    """Create a Bill from an external tool (e.g. an LLM assistant).

    Expects a multipart POST with `name`, `amount`, `date` and the bill
    document as `file`, authenticated with `Authorization: Bearer <token>`
    where the token is settings.BILL_UPLOAD_TOKEN.
    """

    http_method_names = ["post"]

    def _authenticate(self, request):
        header = request.headers.get("Authorization", "")
        provided = header.removeprefix("Bearer ")
        if not provided or header == provided:
            return False
        return authenticate_api_token(provided)

    def post(self, request):
        if not self._authenticate(request):
            return JsonResponse({"error": "Invalid or missing token."}, status=401)

        result = try_create_bill(request.POST, request.FILES)
        if result["status"] == "invalid":
            return JsonResponse({"errors": result["errors"]}, status=400)
        if result["status"] == "duplicate":
            return JsonResponse(
                {
                    "error": "A bill with the same name, amount and date "
                    "already exists.",
                    "existing_ids": result["existing_ids"],
                },
                status=409,
            )

        bill = result["bill"]
        return JsonResponse(
            {
                "id": bill.id,
                "name": bill.name,
                "amount": str(bill.amount),
                "date": bill.date.isoformat(),
                "category": bill.category,
                "iban": bill.iban,
                "file": bill.file.url,
                "admin_url": reverse("admin:accounts_bill_change", args=[bill.id]),
            },
            status=201,
        )


@method_decorator(csrf_exempt, name="dispatch")
class DeviceAuthStartView(View):
    """First step of the device flow: an external tool requests access.

    Returns a device_code (secret, used to poll for the token) and the
    verification URL the user must open to approve the request.
    """

    http_method_names = ["post"]

    def post(self, request):
        DeviceAuthorization.objects.filter(expires_at__lt=timezone.now()).delete()
        authorization = DeviceAuthorization.objects.create(
            device_code=secrets.token_urlsafe(32),
            user_code=secrets.token_urlsafe(16),
            client_name=(request.POST.get("client_name") or "LLM assistant")[:100],
            expires_at=timezone.now() + DEVICE_AUTH_LIFETIME,
        )
        return JsonResponse(
            {
                "device_code": authorization.device_code,
                "verification_url": request.build_absolute_uri(
                    reverse("device_auth_approve", args=[authorization.user_code])
                ),
                "expires_in": int(DEVICE_AUTH_LIFETIME.total_seconds()),
                "interval": DEVICE_AUTH_POLL_INTERVAL,
            },
            status=201,
        )


class DeviceAuthApproveView(TreasurerRequiredMixin, View):
    "Browser page where the treasurer approves or denies a device request."

    def _get_authorization(self, user_code):
        return DeviceAuthorization.objects.filter(
            user_code=user_code, expires_at__gte=timezone.now(), approved_by=None
        ).first()

    def get(self, request, user_code):
        authorization = self._get_authorization(user_code)
        state = "ask" if authorization else "not_found"
        return render(
            request,
            "device_approve.html",
            {"authorization": authorization, "state": state},
        )

    def post(self, request, user_code):
        authorization = self._get_authorization(user_code)
        if authorization is None:
            state = "not_found"
        elif request.POST.get("action") == "approve":
            authorization.approved_by = request.user
            authorization.save(update_fields=["approved_by"])
            state = "approved"
        else:
            authorization.delete()
            state = "denied"
        return render(
            request,
            "device_approve.html",
            {"authorization": authorization, "state": state},
        )


@method_decorator(csrf_exempt, name="dispatch")
class DeviceAuthTokenView(View):
    """Polling endpoint: exchanges an approved device_code for a token.

    The plaintext token is returned exactly once; the device authorization
    is deleted as soon as the token is claimed.
    """

    http_method_names = ["post"]

    def post(self, request):
        authorization = DeviceAuthorization.objects.filter(
            device_code=request.POST.get("device_code", "")
        ).first()
        if authorization is None:
            return JsonResponse({"status": "invalid"}, status=400)
        if authorization.expires_at < timezone.now():
            authorization.delete()
            return JsonResponse({"status": "expired"}, status=400)
        if authorization.approved_by is None:
            return JsonResponse(
                {"status": "pending", "interval": DEVICE_AUTH_POLL_INTERVAL},
                status=202,
            )
        _, raw_token = ApiToken.issue(
            name=f"{authorization.client_name} — approuvé par "
            f"{authorization.approved_by}",
            user=authorization.approved_by,
        )
        authorization.delete()
        return JsonResponse({"status": "approved", "token": raw_token})


class CreateApiTokenView(TreasurerRequiredMixin, View):
    """Generate an API token in the browser, shown only once.

    Meant for configuring MCP connectors (e.g. claude.ai), where the device
    flow is not available: the page shows the ready-to-paste MCP URL.
    """

    def get(self, request):
        return render(request, "api_token_create.html", {"state": "ask"})

    def post(self, request):
        name = (request.POST.get("name") or "Connecteur MCP")[:100]
        _, raw_token = ApiToken.issue(
            name=f"{name} — créé par {request.user}", user=request.user
        )
        return render(
            request,
            "api_token_create.html",
            {
                "state": "created",
                "token": raw_token,
                "mcp_url": request.build_absolute_uri(
                    reverse("mcp_server", args=[raw_token])
                ),
            },
        )


class PendingPaymentsView(TreasurerRequiredMixin, TemplateView):
    """Everything the treasurer still has to pay, gathered in a single table.

    A pending payment is a group of open items (OperationValidation without
    an operation, negative amount) sharing the same event — a bill, an
    expense report or a refund. Payment can only be confirmed by an imported
    bank operation, so for each entry the view also suggests unjustified
    imported operations with a matching amount, ready to be settled through
    the unified settle endpoint.
    """

    template_name = "pending_payments.html"

    def get_context_data(self, **kwargs):
        open_items = list(
            OperationValidation.objects.payables()
            .select_related("content_type")
            .order_by("object_id", "id")
        )
        groups = {}
        for item in open_items:
            groups.setdefault((item.content_type_id, item.object_id), []).append(item)

        # Imported outgoing operations not yet justified: candidates proving
        # a pending payment was actually executed.
        candidate_operations = defaultdict(list)
        for operation in Operation.objects.filter(
            operationvalidation__isnull=True, amount__lt=0
        ).order_by("-date"):
            candidate_operations[operation.amount].append(operation)

        pending_payments = []
        for (_content_type_id, object_id), items in groups.items():
            content_type = items[0].content_type
            event = content_type.model_class().objects.filter(pk=object_id).first()
            if event is None:
                continue
            pending_payments.append(
                self._build_entry(event, content_type, items, candidate_operations)
            )
        pending_payments.sort(
            key=lambda entry: (
                entry["due_date"] or datetime.date.max,
                entry["reference"],
            )
        )

        totals_by_type = defaultdict(int)
        for entry in pending_payments:
            totals_by_type[entry["type_label"]] += entry["to_pay"]

        kwargs["pending_payments"] = pending_payments
        kwargs["totals_by_type"] = dict(totals_by_type)
        kwargs["total"] = sum(entry["to_pay"] for entry in pending_payments)
        return super().get_context_data(**kwargs)

    def _build_entry(self, event, content_type, items, candidate_operations):
        payee_name = next(
            (
                i.expected_counterparty_name
                for i in items
                if i.expected_counterparty_name
            ),
            "",
        )
        payee_iban = next((i.expected_iban for i in items if i.expected_iban), "")
        fallback_name, fallback_iban = self._payee_fallback(event)
        payee_name = payee_name or fallback_name
        payee_iban = payee_iban or fallback_iban

        total_open = sum(item.amount for item in items)
        normalized = _normalize_iban(payee_iban)
        matches = sorted(
            (
                {
                    "operation": operation,
                    "iban_match": bool(normalized)
                    and _normalize_iban(operation.counterparty_IBAN) == normalized,
                }
                for operation in candidate_operations[total_open]
            ),
            key=lambda match: not match["iban_match"],
        )
        try:
            admin_url = reverse(
                f"admin:{event._meta.app_label}_{event._meta.model_name}_change",
                args=[event.pk],
            )
        except NoReverseMatch:
            admin_url = ""

        if isinstance(event, Bill):
            type_label = "Facture"
        elif isinstance(event, ExpenseReport):
            type_label = "Note de frais"
        else:
            type_label = "Remboursement"

        return {
            "type_label": type_label,
            "event": event,
            "reference": str(event),
            "admin_url": admin_url,
            "content_type_id": content_type.id,
            "object_id": event.pk,
            "to_pay": -total_open,
            "payee_name": payee_name,
            "payee_iban": payee_iban,
            "due_date": min((i.due_date for i in items if i.due_date), default=None)
            or getattr(event, "submitted_date", None),
            "blocked": isinstance(event, ExpenseReport) and not event.validated,
            "matches": matches,
            "items": items,
        }

    @staticmethod
    def _payee_fallback(event):
        "Payee derived from the event when the open items carry none."
        if isinstance(event, ExpenseReport):
            beneficiary = event.beneficiary
            name = (
                (beneficiary.get_full_name() or beneficiary.email)
                if beneficiary
                else ""
            )
            return name, event.iban
        if isinstance(event, Bill):
            return "", event.iban
        owner = getattr(event, "owner", None)
        if owner is None and (signup_group := getattr(event, "signup_group", None)):
            owner = signup_group.owner
        if owner:
            return owner.get_full_name() or owner.email, ""
        return "", ""


class AnnualAccountsView(PermissionRequiredMixin, TemplateView):
    permission_required = "is_superuser"
    template_name = "account_details.html"

    def get_context_data(self, **kwargs):
        # Year is passed via URL. Calendar year: Jan 1 of <year> to Jan 1 of <year + 1> (exclusive)
        year = int(self.kwargs.get("year"))
        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year + 1, 1, 1)

        movement_details = {
            validation_type: total
            for validation_type, total in OperationValidation.objects.filter(
                operation__date__gte=start_date,
                operation__date__lt=end_date,
            )
            .values("validation_type")
            .annotate(year_sum=Sum("amount"))
            .values_list("validation_type", "year_sum")
        }

        charges = (
            ("60", "APPROVISIONNEMENTS ET MARCHANDISES"),
            ("61", "SERVICES ET BIENS DIVERS"),
            ("65", "AUTRES CHARGES"),
        )
        charges = {
            _: {
                (number, description): movement_details.get(number, 0)
                for number, description in ExpenditureChoices.choices
                if str(number).startswith(_[0])
            }
            for _ in charges
        }
        kwargs["charges"] = charges
        for group, validation_types in charges.items():
            charges[group]["sum"] = sum(validation_types.values())
        kwargs["total_spends"] = sum((_["sum"] for _ in charges.values()))

        incomes = (
            ("70", "CHIFFRE D'AFFAIRES"),
            ("75", "PRODUITS FINANCIERS"),
        )
        incomes = {
            _: {
                (number, description): movement_details.get(number, 0)
                for number, description in IncomeChoices.choices
                if str(number).startswith(_[0])
            }
            for _ in incomes
        }
        for group, validation_types in incomes.items():
            incomes[group]["sum"] = sum(validation_types.values())
        kwargs["incomes"] = incomes
        kwargs["total_incomes"] = sum((_["sum"] for _ in incomes.values()))

        pending_operations = (
            Operation.objects.alias(
                _justified_amount=Round(
                    Sum("operationvalidation__amount") - F("amount"), 2
                )
            )
            .annotate(
                _justified_amount=F("_justified_amount"),
                _justified=ExpressionWrapper(
                    Q(_justified_amount__exact=0), output_field=BooleanField()
                ),
            )
            .filter(date__gte=start_date, date__lt=end_date, _justified__isnull=True)
        )
        kwargs["positive_pending_transactions"] = pending_operations.filter(
            amount__gt=0
        ).aggregate(total=Sum("amount"))["total"]
        kwargs["negative_pending_transactions"] = pending_operations.filter(
            amount__lt=0
        ).aggregate(total=Sum("amount"))["total"]
        kwargs["total"] = kwargs["total_incomes"] + kwargs["total_spends"]
        kwargs["year"] = year
        # Display period as 01/01/<year> → 31/12/<year>
        period_end_display = datetime.date(year, 12, 31)
        kwargs["period"] = (
            f"{start_date.strftime('%d/%m/%Y')} → {period_end_display.strftime('%d/%m/%Y')}"
        )
        return kwargs

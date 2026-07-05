# Create your views here.
import datetime
import re
import secrets
from collections import defaultdict

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin
from django.db.models import (
    BooleanField,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, Round
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from accounts.forms import BillUploadForm
from accounts.models import (
    ApiToken,
    Bill,
    DeviceAuthorization,
    ExpenditureChoices,
    ExpenseReport,
    IncomeChoices,
    Operation,
    OperationValidation,
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
        static_token = settings.BILL_UPLOAD_TOKEN
        if static_token and constant_time_compare(provided, static_token):
            return True
        token = ApiToken.objects.filter(
            token_hash=ApiToken.hash_token(provided)
        ).first()
        if token:
            token.last_used_at = timezone.now()
            token.save(update_fields=["last_used_at"])
            return True
        return False

    def post(self, request):
        if not self._authenticate(request):
            return JsonResponse({"error": "Invalid or missing token."}, status=401)

        form = BillUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)

        duplicates = Bill.objects.filter(
            name=form.cleaned_data["name"],
            amount=form.cleaned_data["amount"],
            date=form.cleaned_data["date"],
        )
        if duplicates.exists():
            return JsonResponse(
                {
                    "error": "A bill with the same name, amount and date "
                    "already exists.",
                    "existing_ids": list(duplicates.values_list("id", flat=True)),
                },
                status=409,
            )

        bill = form.save()
        return JsonResponse(
            {
                "id": bill.id,
                "name": bill.name,
                "amount": str(bill.amount),
                "date": bill.date.isoformat(),
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


class PendingPaymentsView(TreasurerRequiredMixin, TemplateView):
    """Everything the treasurer still has to pay, gathered in a single page.

    Two sources of pending payments:
    - expense reports whose expense lines are not yet linked to a bank
      operation (reimbursements to members),
    - bills whose amount is not fully covered by bank operations.

    Payment can only be confirmed by an imported bank operation, so for each
    pending item the view also suggests unjustified imported operations with a
    matching amount, ready to be linked through the existing admin flows.
    """

    template_name = "pending_payments.html"

    def get_context_data(self, **kwargs):
        expense_reports = list(
            ExpenseReport.objects.annotate(
                remaining=Sum(
                    "expenses__amount",
                    filter=Q(expenses__operation__isnull=True),
                )
            )
            .exclude(remaining__isnull=True)
            .exclude(remaining=0)
            .select_related("beneficiary")
            .order_by("submitted_date", "id")
        )
        bills = list(
            Bill.objects.annotate(
                remaining=F("amount")
                + Coalesce(
                    Sum(
                        "payments__amount",
                        filter=Q(payments__operation__isnull=False),
                    ),
                    Value(0, output_field=DecimalField()),
                )
            )
            .exclude(remaining=0)
            .order_by("date", "id")
        )
        # Bank operations paying something out are negative, so remaining
        # amounts can carry either sign; the transfer to make is the absolute value.
        for item in expense_reports + bills:
            item.to_pay = abs(item.remaining)

        # Imported outgoing operations not yet justified: candidates proving
        # a pending payment was actually executed.
        candidate_operations = defaultdict(list)
        for operation in Operation.objects.filter(
            operationvalidation__isnull=True, amount__lt=0
        ).order_by("-date"):
            candidate_operations[operation.amount].append(operation)

        for er in expense_reports:
            iban = _normalize_iban(er.iban)
            er.matches = sorted(
                (
                    {
                        "operation": operation,
                        "iban_match": _normalize_iban(operation.counterparty_IBAN)
                        == iban,
                    }
                    for operation in candidate_operations[er.remaining]
                ),
                key=lambda match: not match["iban_match"],
            )
        for bill in bills:
            bill.matches = [
                {"operation": operation, "iban_match": False}
                for operation in candidate_operations[-bill.remaining]
            ]

        kwargs["expense_reports"] = expense_reports
        kwargs["bills"] = bills
        kwargs["total_expense_reports"] = sum(er.to_pay for er in expense_reports)
        kwargs["total_bills"] = sum(bill.to_pay for bill in bills)
        kwargs["total"] = kwargs["total_expense_reports"] + kwargs["total_bills"]
        return super().get_context_data(**kwargs)


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

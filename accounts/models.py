# Create your models here.

import hashlib
import secrets
from datetime import datetime

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.functions import Coalesce
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from schwifty import IBAN


class Account(models.Model):
    name = models.CharField(max_length=55)
    IBAN = models.CharField(max_length=16, unique=True)
    current_ballance = models.DecimalField(max_digits=11, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class Operation(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    year = models.IntegerField()
    number = models.IntegerField()
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    currency = models.TextField(default="EUR")
    effective_date = models.DateField()
    counterparty_IBAN = models.CharField(max_length=255)
    counterparty_name = models.CharField(max_length=255)
    communication = models.CharField(max_length=255)
    reference = models.CharField(max_length=255)

    class Meta:
        unique_together = (
            "account",
            "year",
            "number",
        )

    def __str__(self):
        return f"{self.year} {self.number} - {self.amount}€ - {self.counterparty_name}"


class ExpenditureChoices(models.IntegerChoices):
    # 60 Sourcing and merch
    EQUIPMENT = 6010, _("matériel")
    EQUIPMENT_RENTAL = 6015, _("location de matériel")
    MOBILE_KITCHEN = 6030, _("cuisine mobile")
    SNACK = 6031, _("encas / collations")
    MERCH = 6041, _("marchandises(t-shirts etc)")
    # 61 goods and services
    ROOM_RENTAL = 6104, _("location salles")
    MEETING_EXPENSES = 6111, _("frais réunions")
    OFFICE_SUPPLIES = 6120, _("fournitures bureau")
    POST = 6124, _("poste")
    CULTURAL_ACTIVITIES = 6131, _("activités culturelles")
    PHOTOCOPY = 6132, _("photocopies")
    CONFERENCES = 6133, _("conférences communiqués presse")
    BOOKLET = 6135, _("brochures")
    SPORT_ACTIVITIES = 6136, _("activités sportives")
    GROUP_INSURANCE = 6141, _("assurance sportive groupe")
    GOODWILL = 6142, _("goodwill - cadeaux")
    ORGANISER_TRANSPORT = 6150, _("transport organisateurs")
    ORGANISER_KM_ALLOWANCE = 6151, _("indemnités km organisateurs")
    ORGANISER_ROOM_BOARD = 6152, _("logement repas organisateurs")
    CAR_FOLLOWING = 6153, _("voitures suiveuses")
    PARTICIPANT_TRANSPORT = 6154, _("transport participants")
    PARTICIPANT_HOUSING = 6156, _("logement participants")
    TELECOM = 6160, _("telecom")
    WEBSITE = 6161, _("site web")
    DOC_MAPS = 6171, _("documentation - cartes")
    TRAINING = 6173, _("formation")
    # 65 OTHER
    BANK_FEES = 6501, _("frais bancaires")
    ADMINISTRATIVE_FEES = 6502, _("frais administratifs")


class IncomeChoices(models.IntegerChoices):
    SIGNUP = 7000, _("INSCRIPTIONS")
    DONATION = 7001, _("DONS")
    SUBSIDY = 7002, _("SUBSIDES")
    MERCH_SALES = 7003, _("VENTE MARCHANDISES")
    INTERESTS = 7512, _("PRODUITS BANCAIRES")


class OperationValidationQuerySet(models.QuerySet):
    def open(self):
        "Open items: placeholders not yet settled by an imported bank operation."
        return self.filter(operation__isnull=True)

    def settled(self):
        return self.filter(operation__isnull=False)

    def payables(self):
        "Open items for money we still have to pay out."
        return self.open().filter(amount__lt=0)


class OperationValidation(models.Model):
    "Each operation should be validated, this is done by validating the operation against another event in the db"

    operation = models.ForeignKey(
        "Operation", null=True, blank=True, on_delete=models.CASCADE
    )
    # If there is a single justification, this will be equal to the operation,
    # but we can imagine that an operation is justified by multiple events.
    amount = models.DecimalField(
        max_digits=11, decimal_places=2, verbose_name=_("montant")
    )
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=False
    )
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    event = GenericForeignKey(
        "content_type",
        "object_id",
    )
    event = GenericForeignKey()
    validation_type = models.IntegerField(
        choices=[
            ("Expenses", ExpenditureChoices.choices),
            ("Incomes", IncomeChoices.choices),
        ],
        null=True,
        blank=True,
        verbose_name=_("justification"),
    )
    # Open-item (placeholder) metadata: when the item is created before the
    # bank operation exists, these describe the expected settlement.
    due_date = models.DateField(null=True, blank=True, verbose_name=_("échéance"))
    expected_iban = models.CharField(max_length=34, blank=True, default="")
    expected_counterparty_name = models.CharField(
        max_length=255, blank=True, default=""
    )

    objects = OperationValidationQuerySet.as_manager()

    @property
    def is_open(self):
        return self.operation_id is None

    def settle(self, operation, user=None, amount=None):
        """Settle this open item against an imported bank operation.

        Without `amount` the whole item is settled. With an `amount` smaller
        than (and of the same sign as) the open amount, the item is split:
        a settled line is created for `amount` and this item stays open for
        the remainder.
        """
        if not self.is_open:
            raise ValueError("This item is already settled.")
        if amount is None or amount == self.amount:
            self.operation = operation
            self.save()
            return self
        if amount == 0 or (amount < 0) != (self.amount < 0):
            raise ValueError("Partial settlement must have the same sign.")
        if abs(amount) > abs(self.amount):
            raise ValueError("Cannot settle more than the open amount.")
        with transaction.atomic():
            self.amount -= amount
            self.save()
            return OperationValidation.objects.create(
                operation=operation,
                amount=amount,
                content_type=self.content_type,
                object_id=self.object_id,
                validation_type=self.validation_type,
                created_by=user or self.created_by,
                due_date=self.due_date,
                expected_iban=self.expected_iban,
                expected_counterparty_name=self.expected_counterparty_name,
            )

    def justification_link(self):
        if event := self.event:
            url_name = "admin:%s_%s_change" % (
                event._meta.app_label,
                event._meta.model_name,
            )
            try:
                change_url = reverse(url_name, args=[event.id])
                return mark_safe('<a href="%s">%s</a>' % (change_url, str(event)))
            except NoReverseMatch:
                pass
        return "-"

    def __str__(self):
        return f"{self.validation_type}-{self.get_validation_type_display()} {self.amount:,.2f}€"


def validate_iban(value):
    try:
        IBAN(value)
    except ValueError as exc:
        raise ValidationError(
            _("%(value)s is not a valid IBAN"),
            params={"value": value},
        ) from exc


class ExpenseReport(models.Model):
    title = models.CharField(max_length=255)
    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=True
    )
    iban = models.CharField(
        verbose_name="IBAN", validators=[validate_iban], max_length=34
    )
    submitted_date = models.DateField(null=True, blank=False)
    signed = models.BooleanField(default=False)
    validated = models.BooleanField(default=False)
    comments = models.TextField(blank=True, default="")
    expenses = GenericRelation(OperationValidation)

    def __str__(self):
        if beneficiary := self.beneficiary:
            if (first_name := beneficiary.first_name) and (
                last_name := beneficiary.last_name
            ):
                user = f"{first_name} {last_name}"
            else:
                user = beneficiary.email
        else:
            user = ""
        return f"{self.title} - {user}"

    @property
    def total(self):
        return sum(self.expenses.values_list("amount", flat=True))

    class Meta:
        verbose_name = "note de frais"
        verbose_name_plural = "notes de frais"
        permissions = [
            ("can_validate", "Can validate expense reports"),
        ]


class Justification(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(blank=True, null=True)
    payment = GenericRelation(OperationValidation)


class BillQuerySet(models.QuerySet):
    def with_amounts(self):
        """Annotate amount (sum of all lines) and remaining (open lines).

        The bill's amount is not stored: its payment lines are the single
        source of truth, like everywhere else in the open-item accounting.
        """
        decimal = models.DecimalField(max_digits=11, decimal_places=2)
        return self.annotate(
            amount=Coalesce(
                -models.Sum("payments__amount"), models.Value(0), output_field=decimal
            ),
            remaining=Coalesce(
                -models.Sum(
                    "payments__amount",
                    filter=models.Q(payments__operation__isnull=True),
                ),
                models.Value(0),
                output_field=decimal,
            ),
        )


class Bill(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(blank=True, null=True)
    date = models.DateField(default=datetime.now)
    category = models.IntegerField(
        choices=ExpenditureChoices.choices,
        null=True,
        blank=True,
        verbose_name=_("catégorie"),
    )
    iban = models.CharField(
        verbose_name="IBAN",
        max_length=34,
        blank=True,
        default="",
        validators=[validate_iban],
    )
    payments = GenericRelation(OperationValidation)

    objects = BillQuerySet.as_manager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "facture"
        verbose_name_plural = "factures"

    def set_amount(self, amount):
        """Create or resize the open item so the bill totals `amount`.

        Only allowed while nothing is settled and at most one line is open;
        after that the payment lines are the source of truth and must be
        edited directly. Also propagates category/IBAN/date to the open item.
        """
        if self.payments.filter(operation__isnull=False).exists():
            raise ValueError(
                "Payments are already settled on this bill: "
                "edit the ventilation lines directly."
            )
        open_items = list(self.payments.filter(operation__isnull=True))
        if len(open_items) > 1:
            raise ValueError("This bill has several open lines: edit them directly.")
        if open_items:
            item = open_items[0]
            item.amount = -amount
            item.validation_type = self.category
            item.due_date = self.date
            item.expected_iban = self.iban
            item.save()
        else:
            self.payments.create(
                operation=None,
                amount=-amount,
                validation_type=self.category,
                due_date=self.date,
                expected_iban=self.iban,
            )


class ApiToken(models.Model):
    """Bearer token for the bill upload API, issued through the device flow.

    Only the SHA-256 of the token is stored; the plaintext is shown once when
    the token is claimed. Deleting the row revokes the token.
    """

    name = models.CharField(max_length=255)
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "jeton API"
        verbose_name_plural = "jetons API"
        ordering = ("-created_at",)

    def __str__(self):
        return self.name

    @staticmethod
    def hash_token(raw_token):
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def issue(cls, name, user):
        "Create a token and return it with its plaintext value."
        raw_token = secrets.token_urlsafe(32)
        token = cls.objects.create(
            name=name, token_hash=cls.hash_token(raw_token), created_by=user
        )
        return token, raw_token


def authenticate_api_token(raw_token):
    """Check a plaintext API token; returns True and stamps last_used_at.

    Accepts issued ApiTokens and, as a fallback, the static
    settings.BILL_UPLOAD_TOKEN.
    """
    from django.utils import timezone
    from django.utils.crypto import constant_time_compare

    if not raw_token:
        return False
    static_token = settings.BILL_UPLOAD_TOKEN
    if static_token and constant_time_compare(raw_token, static_token):
        return True
    token = ApiToken.objects.filter(token_hash=ApiToken.hash_token(raw_token)).first()
    if token:
        token.last_used_at = timezone.now()
        token.save(update_fields=["last_used_at"])
        return True
    return False


class DeviceAuthorization(models.Model):
    """Short-lived request from an external tool waiting for user approval.

    device_code is the secret the tool polls with; user_code is in the URL
    the user opens to approve. The row is deleted once the token is claimed,
    denied or found expired.
    """

    device_code = models.CharField(max_length=64, unique=True, editable=False)
    user_code = models.CharField(max_length=64, unique=True, editable=False)
    client_name = models.CharField(max_length=100, default="LLM assistant")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "autorisation d'appareil"
        verbose_name_plural = "autorisations d'appareil"

    def __str__(self):
        return f"{self.client_name} ({self.created_at:%d/%m/%Y %H:%M})"


class ExpenseFile(models.Model):
    expense_report = models.ForeignKey(
        ExpenseReport, on_delete=models.SET_NULL, null=True
    )
    file = models.FileField(blank=True, null=True)

    class Meta:
        verbose_name = "pièce justificative"
        verbose_name_plural = "pièces justificatives"

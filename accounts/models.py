# Create your models here.

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.datetime_safe import datetime
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _


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


class OperationValidation(models.Model):
    "Each operation should be validated, this is done by validating the operation against another event in the db"

    operation = models.ForeignKey("Operation", null=True, on_delete=models.CASCADE)
    # If there is a single justification, this will be equal to the operation,
    # but we can imagine that an operation is justified by multiple events.
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=False
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    event = GenericForeignKey()
    validation_type = models.IntegerField(
        choices=[
            ("Expenses", ExpenditureChoices.choices),
            ("Incomes", IncomeChoices.choices),
        ],
        null=True,
    )

    def justification_link(self):
        if event := self.event:
            url_name = "admin:%s_%s_change" % (
                event._meta.app_label,
                event._meta.model_name,
            )
            change_url = reverse(url_name, args=[event.id])
            return mark_safe('<a href="%s">%s</a>' % (change_url, str(event)))
        return "-"


#
# class SignupOperationManager(models.Manager):
#
#     @cached_property
#     def content_type(self):
#         return ContentType.objects.get_by_natural_key("signup2022", "bill")
#
#     def get_queryset(self):
#         return super().get_queryset().filter(content_type=self.content_type)
#
#
# class SignupOperation(OperationValidation):
#     objects = SignupOperationManager()
#
#     class Meta:
#         proxy = True
#         verbose_name = "paiement inscriptions 2022"
#         verbose_name_plural = "paiements inscriptions 2022"


class ExpenseReport(models.Model):
    title = models.CharField(max_length=255)
    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=True
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
        return f"{self.submitted_date.year}-{self.title} {user} {self.total}"

    @property
    def total(self):
        return sum(self.expenses.values_list("amount", flat=True))


class Justification(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(blank=True, null=True)
    payment = GenericRelation(OperationValidation)


class Bill(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(blank=True, null=True)
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    date = models.DateField(default=datetime.now)
    payments = GenericRelation(OperationValidation)

    def __str__(self):
        return self.name


class ExpenseFile(models.Model):
    expense_report = models.ForeignKey(
        ExpenseReport, on_delete=models.SET_NULL, null=True
    )
    file = models.FileField(blank=True, null=True)

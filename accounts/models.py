# Create your models here.

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.datetime_safe import datetime
from django.utils.functional import cached_property

from signup2022.models import Signup


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
            ('year', 'number')
        )

    def __str__(self):
        return f"{self.year} {self.number} - {self.amount}€ - {self.counterparty_name}"


class OperationValidation(models.Model):
    "Each operation should be validated, this is done by validating the operation against another event in the db"
    operation = models.ForeignKey("Operation", null=True, on_delete=models.CASCADE)
    # If there is a single justification, this will be equal to the peration,
    # but we can imagine that an operation is justified by multiple events.
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    event = GenericForeignKey()


class SignupOperationManager(models.Manager):

    @cached_property
    def content_type(self):
        return ContentType.objects.get_by_natural_key("signup2022", "bill")

    def get_queryset(self):
        return super().get_queryset().filter(content_type=self.content_type)


class SignupOperation(OperationValidation):
    objects = SignupOperationManager()

    class Meta:
        proxy = True
        verbose_name = "paiement inscriptions 2022"
        verbose_name_plural = "paiements inscriptions 2022"


class ExpenseReport(models.Model):
    title = models.CharField(max_length=255)
    beneficiary = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=False)

class Justification(OperationValidation):
    file = models.FileField(blank=True, null=True)


class Bill(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(blank=True, null=True)
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    date = models.DateField(default=datetime.now)
    payments = GenericRelation(OperationValidation)

    def __str__(self):
        return self.name
from csv import reader

# Create your models here.
from datetime import datetime

from django.conf import settings
from django.db import models


class ExpenseReport(models.Model):
    beneficiary = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=False)
    beneficiary_account = models.TextField()
    total = models.DecimalField(max_digits=11, decimal_places=2)


class Account(models.Model):
    name = models.CharField(max_length=55)
    IBAN = models.CharField(max_length=16)
    current_ballance = models.DecimalField(max_digits=11, decimal_places=2, default=0)


class Operation(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    year = models.IntegerField(default=2022)
    number = models.IntegerField(unique=True)
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

    @staticmethod
    def import_from_bpost_export(filename):
        with open(filename, "r", encoding='utf-8-sig') as csv_file:
            csv_reader = reader(csv_file, delimiter=';')
            _, iban, account_type = next(csv_reader)
            account, _ = Account.objects.get_or_create(IBAN=iban, defaults={
                'name': account_type,
            })
            # remove_headers
            next(csv_reader)
            operations = []
            for row in csv_reader:
                (number, date, description,
                 amount, currency, effective_date,
                 counterparty_IBAN, counterparty_name, *communication,
                 reference, _) = row
                print(number)
                operations.append(Operation(
                    account=account,
                    number=number,
                    date=datetime.strptime(date, "%Y-%m-%d"),
                    description=description,
                    amount=float(amount.replace(',', '.')),
                    currency=currency,
                    effective_date=datetime.strptime(effective_date, "%d/%m/%Y"),
                    counterparty_IBAN=counterparty_IBAN,
                    counterparty_name=counterparty_name,
                    communication='\n'.join(communication),
                    reference=reference))
            Operation.objects.bulk_create(operations)

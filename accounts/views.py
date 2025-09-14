# Create your views here.
from pprint import pprint

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import BooleanField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Round
from django.views.generic import TemplateView

from accounts.models import (
    ExpenditureChoices,
    IncomeChoices,
    Operation,
    OperationValidation,
)


class AccountsDetailView(PermissionRequiredMixin, TemplateView):
    permission_required = "is_superuser"
    template_name = "account_details.html"

    def get_context_data(self, **kwargs):
        movement_details = {
            validation_type: total
            for validation_type, total in OperationValidation.objects.filter(
                operation__date__gte="2025-02-01",
            )
            .values("validation_type")
            .annotate(year_sum=Sum("amount"))
            .values_list("validation_type", "year_sum")
        }
        pprint(movement_details)

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
            .filter(date__year__gte=2024, _justified__isnull=True)
        )
        kwargs["positive_pending_transactions"] = pending_operations.filter(
            amount__gt=0
        ).aggregate(total=Sum("amount"))["total"]
        kwargs["negative_pending_transactions"] = pending_operations.filter(
            amount__lt=0
        ).aggregate(total=Sum("amount"))["total"]
        kwargs["total"] = kwargs["total_incomes"] + kwargs["total_spends"]
        return kwargs


# %%
toto = {
    k: v
    for k, v in Operation.objects.filter(
        date__year__in=[2024, 2025], account__IBAN="BE96001951747205"
    )
    .values("operationvalidation__validation_type")
    .annotate(year_sum=Sum("amount"))
    .values_list("operationvalidation__validation_type", "year_sum")
}

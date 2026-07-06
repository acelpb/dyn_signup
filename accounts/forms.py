from django import forms
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Sum

from accounts.models import (
    Bill as AccountBill,
)
from accounts.models import (
    ExpenditureChoices,
    ExpenseReport,
    IncomeChoices,
    Operation,
    OperationValidation,
)
from signup2023.models import Bill as SignupBill
from signup2023.models import Signup

# class SignupOperationForm(forms.ModelForm):
#     operation = forms.ModelChoiceField(
#         queryset=(
#                 Operation.objects.alias(
#                     justified_amount=Sum('operationvalidation__amount') - F('amount')
#                 ).all().filter(~Q(justified_amount__exact=0))
#                 |
#                 Operation.objects.filter(operationvalidation__isnull=True)
#         ).filter(year=2022).order_by('-number')
#     )
#     participant = forms.ModelChoiceField(queryset=Participant.objects.all().order_by("first_name", "last_name"))
#
#     def full_clean(self):
#         super().full_clean()
#         self.instance.event = self.cleaned_data.pop("participant").signup_group.bill
#
#     class Meta:
#         model = SignupOperation
#         fields = ('operation', 'amount', 'participant')


class LinkToBillForm(forms.Form):
    operations = forms.ModelMultipleChoiceField(queryset=Operation.objects.all())
    bill = forms.ModelChoiceField(queryset=AccountBill.objects.all())

    def save(self):
        bill = self.cleaned_data["bill"]
        with transaction.atomic():
            for operation in self.cleaned_data["operations"]:
                item = (
                    OperationValidation.objects.open()
                    .filter(
                        content_type=ContentType.objects.get_for_model(AccountBill),
                        object_id=bill.id,
                    )
                    .order_by("id")
                    .first()
                )
                if item is None or (operation.amount < 0) != (item.amount < 0):
                    OperationValidation.objects.create(
                        operation=operation, amount=operation.amount, event=bill
                    )
                elif abs(operation.amount) < abs(item.amount):
                    # Installment: settle part of the open item, the rest
                    # stays open.
                    item.settle(operation, amount=operation.amount)
                else:
                    surplus = operation.amount - item.amount
                    item.settle(operation)
                    if surplus:
                        # Keep the operation fully justified even when it
                        # exceeds what was still open on the bill.
                        OperationValidation.objects.create(
                            operation=operation,
                            amount=surplus,
                            event=bill,
                            validation_type=item.validation_type,
                        )


class LinkToExpenseReportForm(forms.Form):
    operation = forms.ModelChoiceField(queryset=Operation.objects.all())
    expense_report = forms.ModelChoiceField(queryset=ExpenseReport.objects.all())

    def clean(self):
        cleaned_data = self.cleaned_data
        expense_report: ExpenseReport = cleaned_data["expense_report"]
        operation = cleaned_data["operation"]
        total = round(
            sum(
                ex.amount
                for ex in expense_report.expenses.filter(operation__isnull=True)
            ),
            2,
        )
        if total != operation.amount:
            self.add_error(
                "operation", "Expense report and operation should cancel each other out"
            )
            self.add_error(
                "expense_report",
                "Expense report and operation should cancel each other out",
            )
            raise ValidationError("NOT WORKING", code="error1")

    def save(self):
        expense_report = self.cleaned_data["expense_report"]
        operation = self.cleaned_data["operation"]
        with transaction.atomic():
            for operation_validation in expense_report.expenses.filter(
                operation__isnull=True
            ):
                operation_validation.settle(operation)


class LinkToSignupForm(forms.Form):
    operations = forms.ModelMultipleChoiceField(queryset=Operation.objects.all())
    signup = forms.ModelChoiceField(
        queryset=Signup.objects.filter(
            year=settings.DYNAMOBILE_LAST_DAY.year,
            validated_at__isnull=False,
            on_hold=False,
            bill__payed_at=None,
        ).order_by("-id")
    )

    def save(self):
        signup = self.cleaned_data["signup"]
        with transaction.atomic():
            for operation in self.cleaned_data["operations"]:
                # Try to find a placeholder OperationValidation for this signup's bill and amount
                placeholder = OperationValidation.objects.filter(
                    operation__isnull=True,
                    amount=operation.amount,
                    content_type=ContentType.objects.get_for_model(SignupBill),
                    object_id=signup.bill.id,
                ).first()

                if placeholder:
                    placeholder.operation = operation
                    placeholder.save()
                else:
                    OperationValidation.objects.create(
                        operation=operation,
                        amount=operation.amount,
                        event=signup.bill,
                        validation_type=IncomeChoices.SIGNUP,
                    )


class BillUploadForm(forms.ModelForm):
    # The amount is not a Bill field: it sizes the bill's open item, the
    # single source of truth for what the bill totals.
    amount = forms.DecimalField(max_digits=11, decimal_places=2, label="montant")

    class Meta:
        model = AccountBill
        fields = ("name", "date", "file", "category", "iban")

    def __init__(self, *args, require_file=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].required = require_file

    def save(self, commit=True):
        bill = super().save(commit=commit)
        if commit:
            bill.set_amount(self.cleaned_data["amount"])
        return bill


def try_create_bill(data, files, require_file=True):
    """Validate and create a Bill, guarding against duplicates.

    Returns a dict with "status" being one of "created" (with "bill",
    annotated with its amount), "invalid" (with "errors") or "duplicate"
    (with "existing_ids").
    """
    form = BillUploadForm(data, files, require_file=require_file)
    if not form.is_valid():
        return {"status": "invalid", "errors": form.errors.get_json_data()}
    duplicates = AccountBill.objects.with_amounts().filter(
        name=form.cleaned_data["name"],
        amount=form.cleaned_data["amount"],
        date=form.cleaned_data["date"],
    )
    if duplicates.exists():
        return {
            "status": "duplicate",
            "existing_ids": list(duplicates.values_list("id", flat=True)),
        }
    bill = form.save()
    return {
        "status": "created",
        "bill": AccountBill.objects.with_amounts().get(pk=bill.pk),
    }


class BillAdminForm(BillUploadForm):
    """Bill admin form: the amount edits the open item, not a field.

    Resizing is blocked once a payment is settled — the ventilation lines
    are then the source of truth.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, require_file=False, **kwargs)
        if self.instance.pk:
            total = self.instance.payments.aggregate(total=Sum("amount"))["total"]
            self.initial["amount"] = -total if total is not None else None

    def clean(self):
        cleaned_data = super().clean()
        if (
            self.instance.pk
            and "amount" in self.changed_data
            and self.instance.payments.filter(operation__isnull=False).exists()
        ):
            self.add_error(
                "amount",
                "Des paiements sont déjà liés : modifiez la ventilation.",
            )
        return cleaned_data

    def save(self, commit=True):
        bill = forms.ModelForm.save(self, commit=commit)
        if commit and self.cleaned_data.get("amount") is not None:
            try:
                bill.set_amount(self.cleaned_data["amount"])
            except ValueError:
                # Settled or multi-line bill: the lines stay the truth, and
                # clean() already blocked any amount change.
                pass
        return bill


class VentilationForm(forms.ModelForm):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        instance = kwargs.get("instance")
        qs = Operation.objects.alias(
            _justified_amount=Sum("operationvalidation__amount") - F("amount")
        ).filter(_justified_amount__isnull=True, year=2022)
        if instance is not None:
            qs |= Operation.objects.filter(id=instance.operation_id)

        self.fields["operation"].queryset = qs.order_by("amount")
        self.fields["operation"].required = False

    class Meta:
        model = OperationValidation
        fields = ("operation", "amount", "validation_type")


class CreateVentilationForm(forms.ModelForm):
    def __init__(self, **kwargs):
        ## Only keep the validation_type choices for the expense categories
        super().__init__(**kwargs)
        self.fields["validation_type"].choices = (
            (k, f"{k} - {v}") for k, v in ExpenditureChoices.choices
        )

    class Meta:
        model = OperationValidation
        fields = ("operation", "validation_type", "amount")

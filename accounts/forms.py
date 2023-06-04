from django import forms
from django.db import transaction
from django.db.models import Sum, F
from django.core.exceptions import ValidationError

from accounts.models import (
    Operation,
    Bill,
    OperationValidation,
    ExpenseReport,
    IncomeChoices,
)
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
    bill = forms.ModelChoiceField(queryset=Bill.objects.all())

    def save(self):
        bill = self.cleaned_data["bill"]
        with transaction.atomic():
            for operation in self.cleaned_data["operations"]:
                OperationValidation.objects.create(
                    operation=operation, amount=operation.amount, event=bill
                )


class LinkToExpenseReportForm(forms.Form):
    operation = forms.ModelChoiceField(queryset=Operation.objects.all())
    expense_report = forms.ModelChoiceField(queryset=ExpenseReport.objects.all())

    def clean(self):
        cleaned_data = self.cleaned_data
        expense_report: ExpenseReport = cleaned_data["expense_report"]
        operation = cleaned_data["operation"]
        total = round(sum(ex.amount for ex in expense_report.expenses.all()), 2)
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
            for operation_validation in expense_report.expenses.all():
                operation_validation.operation = operation
                operation_validation.save()


class LinkToSignupForm(forms.Form):
    operations = forms.ModelMultipleChoiceField(queryset=Operation.objects.all())
    signup = forms.ModelChoiceField(queryset=Signup.objects.all())

    def save(self):
        signup = self.cleaned_data["signup"]
        with transaction.atomic():
            for operation in self.cleaned_data["operations"]:
                OperationValidation.objects.create(
                    operation=operation,
                    amount=operation.amount,
                    event=signup.bill,
                    validation_type=IncomeChoices.SIGNUP,
                )


class VentilationForm(forms.ModelForm):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(self.fields["operation"].queryset)
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

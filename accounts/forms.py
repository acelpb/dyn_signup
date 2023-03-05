from django import forms, db
from django.db import transaction
from django.db.models import Sum, F, Q

from accounts.models import SignupOperation, Operation, Bill, OperationValidation, ExpenseReport
from signup2022.models import Participant, Signup


class SignupOperationForm(forms.ModelForm):
    operation = forms.ModelChoiceField(
        queryset=(
                Operation.objects.alias(
                    justified_amount=Sum('operationvalidation__amount') - F('amount')
                ).all().filter(~Q(justified_amount__exact=0))
                |
                Operation.objects.filter(operationvalidation__isnull=True)
        ).filter(year=2022).order_by('-number')
    )
    participant = forms.ModelChoiceField(queryset=Participant.objects.all().order_by("first_name", "last_name"))

    def full_clean(self):
        super().full_clean()
        self.instance.event = self.cleaned_data.pop("participant").signup_group.bill

    class Meta:
        model = SignupOperation
        fields = ('operation', 'amount', 'participant')


class LinkToBillForm(forms.Form):
    operations = forms.ModelMultipleChoiceField(queryset=Operation.objects.all())
    bill = forms.ModelChoiceField(queryset=Bill.objects.all())

    def save(self):
        bill = self.cleaned_data['bill']
        with transaction.atomic():
            for operation in self.cleaned_data['operations']:
                OperationValidation.objects.create(
                    operation=operation,
                    amount=operation.amount,
                    event=bill
                )


class LinkToSignupForm(forms.Form):
    operations = forms.ModelMultipleChoiceField(queryset=Operation.objects.all())
    signup = forms.ModelChoiceField(queryset=Signup.objects.all())

    def save(self):
        signup = self.cleaned_data['signup']
        with transaction.atomic():
            for operation in self.cleaned_data['operations']:
                OperationValidation.objects.create(
                    operation=operation,
                    amount=operation.amount,
                    event=signup.bill
                )


class VentilationForm(forms.ModelForm):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(self.fields['operation'].queryset)
        instance = kwargs.get('instance')
        qs = Operation.objects.alias(
            _justified_amount=Sum('operationvalidation__amount') - F('amount')
        ).filter(_justified_amount__isnull=True, year=2022)
        if instance is not None:
            qs |= Operation.objects.filter(id=instance.operation_id)

        self.fields['operation'].queryset = qs.order_by('amount')
        self.fields['operation'].required = False

    class Meta:
        model = OperationValidation
        fields = ('operation', 'amount', 'validation_type')

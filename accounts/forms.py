from django import forms
from django.db.models import Sum, F, Q

from accounts.models import SignupOperation, Operation
from signup2022.models import Participant


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
        self.instance.event = self.cleaned_data.pop("participant").signup_group

    class Meta:
        model = SignupOperation
        fields = ('operation', 'amount', 'participant')

from django import forms
from django.forms.models import inlineformset_factory

from .models import Participant, Signup


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = (
            "first_name",
            "last_name",
            "email",
            "birthday",
            "city",
            "country",
        )


ParticipantFormSet = inlineformset_factory(
    Signup, Participant, form=ParticipantForm, min_num=1, extra=1, can_delete=False
)

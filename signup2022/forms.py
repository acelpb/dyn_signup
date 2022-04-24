from django import forms
from django.conf import settings
from django.forms.models import inlineformset_factory

from .models import Participant, Signup, DaySignup


class ParticipantForm(forms.ModelForm):
    vae = forms.ChoiceField(choices=(("", "----"), (True, "oui"), (False, "non")), initial="")

    class Meta:
        model = Participant
        fields = (
            "first_name",
            "last_name",
            "email",
            "birthday",
            "city",
            "country",
            'vae',
        )


ParticipantFormSet = inlineformset_factory(
    Signup, Participant, form=ParticipantForm, min_num=1, extra=0, can_delete=True
)


class DaySignupForm(forms.ModelForm):
    def __init__(self, **kwargs):
        self.base_fields
        super().__init__(**kwargs)

    class Meta:
        model = Participant
        fields = '__all__'
        # fields = [_[1] for _ in settings.DYNAMOBILE_DAYS]


DaySignupFormset = inlineformset_factory(
    Participant, DaySignup, form=DaySignupForm, min_num=1, extra=0, can_delete=False
)

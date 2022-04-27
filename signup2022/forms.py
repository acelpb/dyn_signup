from django import forms
from django.forms.models import inlineformset_factory

from .models import Participant, Signup


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
    first_name = forms.CharField(disabled=True)
    last_name = forms.CharField(disabled=True)

    class Meta:
        model = Participant
        fields = [
            "first_name",
            "last_name",
            "d2022_07_18",
            "d2022_07_19",
            "d2022_07_20",
            "d2022_07_21",
            "d2022_07_22",
            "d2022_07_23",
            "d2022_07_24",
            "d2022_07_25",
        ]


DaySignupFormset = inlineformset_factory(
    Signup, Participant, form=DaySignupForm, min_num=1, extra=0, can_delete=False
)

from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory

from .models import Participant, Signup


class DatePickerInput(forms.DateInput):
    input_type = "date"

    def format_value(self, value):
        if isinstance(value, str):
            return value
        elif isinstance(value, date):
            return value.isoformat()
        else:
            return value


class ParticipantForm(forms.ModelForm):
    birthday = forms.DateField(widget=DatePickerInput())
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


class ParticipantListReviewForm(forms.ModelForm):
    vae = forms.BooleanField(
        label="Dynamobile recommande la prise d'une assurance assistance pour les vélos électriques, "
              "et demande à faire un usage respectueux des infrastructures électriques aux logements.",
        required=False,

    )

    class Meta:
        model = Signup
        fields = ["vae"]

    def clean_vae(self):
        vae_ok = self.cleaned_data['vae']
        if self.instance.has_vae() and not vae_ok:
            self.add_error('vae', ValidationError("Merci d'accepter les conditions propres aux vélo électriques."))
        return vae_ok

    def clean(self):
        if not self.instance.participant_set.filter(birthday__lte=date(2004, 7, 18)).count():
            self.add_error(None, ValidationError("Chaque groupe doit être composé au minimum d'un adulte."))


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

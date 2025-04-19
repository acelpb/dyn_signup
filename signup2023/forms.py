from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory
from django.template.defaultfilters import title

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


def ensure_mixed_case(name: str):
    """Ensure that a name contains mixed case,
    otherwise apply the title filter of Django.
    """
    if name == name.upper() or name == name.lower():
        return title(name)
    else:
        return name


class ParticipantForm(forms.ModelForm):
    birthday = forms.DateField(widget=DatePickerInput())

    class Meta:
        model = Participant
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "birthday",
            "city",
            "country",
        )

    def clean_first_name(self):
        value = self.cleaned_data["first_name"]
        return ensure_mixed_case(value)

    def clean_last_name(self):
        value = self.cleaned_data["last_name"]
        return ensure_mixed_case(value)

    def clean_country(self):
        value = self.cleaned_data["country"]
        return ensure_mixed_case(value)


class ParticipantExtraForm(forms.ModelForm):
    first_name = forms.CharField(label="Prénom", disabled=True)
    last_name = forms.CharField(label="Nom", disabled=True)

    class Meta:
        model = Participant
        fields = (
            "first_name",
            "last_name",
            "vae",
            "extra_activities",
        )


ParticipantFormSet = inlineformset_factory(
    Signup, Participant, form=ParticipantForm, min_num=1, extra=0, can_delete=True
)

ParticipantExtraFormSet = inlineformset_factory(
    Signup, Participant, form=ParticipantExtraForm, min_num=1, extra=0, can_delete=False
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
        vae_ok = self.cleaned_data["vae"]
        if self.instance.has_vae() and not vae_ok:
            self.add_error(
                "vae",
                ValidationError(
                    "Merci d'accepter les conditions propres aux vélo électriques."
                ),
            )
        return vae_ok

    def clean(self):
        if not self.instance.participant_set.filter(
            birthday__lte=date(2004, 7, 18)
        ).count():
            self.add_error(
                None,
                ValidationError(
                    "Chaque groupe doit être composé au minimum d'un adulte."
                ),
            )


class DaySignupForm(forms.ModelForm):
    first_name = forms.CharField(label="Prénom", disabled=True)
    last_name = forms.CharField(label="Nom", disabled=True)

    class Meta:
        model = Participant
        fields = [
            "first_name",
            "last_name",
            "day1",
            "day2",
            "day3",
            "day4",
            "day5",
            "day6",
            "day7",
            "day8",
            "day9",
        ]


DaySignupFormset = inlineformset_factory(
    Signup, Participant, form=DaySignupForm, min_num=1, extra=0, can_delete=False
)

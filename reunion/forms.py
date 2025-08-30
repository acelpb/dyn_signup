from datetime import date

from crispy_bootstrap5.bootstrap5 import FloatingField, Switch
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    Button,
    Column,
    Field,
    Layout,
    Row,
    Submit,
)
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory
from django.template.defaultfilters import title
from django.urls import reverse

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


ParticipantFormSet = inlineformset_factory(
    Signup, Participant, form=ParticipantForm, min_num=1, extra=0, can_delete=True
)


class ParticipantFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = Layout(
            HTML("{% if forloop.first %}{%else%}<hr>{% endif %}"),
            Row(
                Column(
                    FloatingField(
                        "first_name",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    FloatingField(
                        "last_name",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    FloatingField(
                        "email",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    FloatingField(
                        "phone",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    FloatingField(
                        "birthday",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    FloatingField(
                        "city",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    FloatingField(
                        "country",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    Field(
                        "DELETE",
                    ),
                    css_class="col-auto",
                ),
            ),
        )
        self.add_input(
            Button(
                "add_user",
                "Ajouter un participant",
                css_class="btn-secondary",
            )
        )
        self.add_input(Submit("submit", "Page Suivante"))


class ParticipantExtraForm(forms.ModelForm):
    first_name = forms.CharField(label="Prénom", disabled=True)
    last_name = forms.CharField(label="Nom", disabled=True)

    class Meta:
        model = Participant
        fields = (
            "first_name",
            "last_name",
            "is_helping_friday",
            "is_helping_saturday_morning",
            "is_helping_saturday_evening",
        )


ParticipantExtraFormSet = inlineformset_factory(
    Signup, Participant, form=ParticipantExtraForm, min_num=1, extra=0, can_delete=False
)


class ParticipantExtraFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = Layout(
            HTML("{% if forloop.first %}{%else%}<hr>{% endif %}"),
            Row(
                Column(
                    FloatingField(
                        "first_name",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    FloatingField(
                        "last_name",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    Switch(
                        "is_helping_friday",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    Switch(
                        "is_helping_saturday_morning",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    Switch(
                        "is_helping_saturday_evening",
                    ),
                    css_class="col-auto",
                ),
                css_class="g-2",
            ),
        )
        self.add_input(
            Button(
                "cancel",
                "Page précédente",
                css_class="btn-secondary",
                onclick="window.location.href = '{}';".format(reverse("group_edit")),
            )
        )
        self.add_input(Submit("submit", "Page Suivante"))


class ParticipantListReviewForm(forms.ModelForm):
    is_helping_saturday_evening = forms.BooleanField(
        required=False,
    )

    class Meta:
        model = Signup
        fields = ["is_helping_saturday_evening"]

    def clean(self):
        if not self.instance.participants_set.filter(
            birthday__lte=date(
                settings.DYNAMOBILE_FIRST_DAY.year - 18,
                settings.DYNAMOBILE_FIRST_DAY.month,
                settings.DYNAMOBILE_FIRST_DAY.day,
            )
        ).count():
            self.add_error(
                None,
                ValidationError(
                    "Chaque groupe doit être composé au minimum d'un adulte."
                ),
            )

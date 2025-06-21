from datetime import date

from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    Button,
    Column,
    Field,
    Fieldset,
    Layout,
    Row,
    Submit,
)
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory, modelformset_factory
from django.template.defaultfilters import title
from django.urls import reverse

from .models import ExtraParticipantInfo, Participant, Signup


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
            "vae",
            "extra_activities",
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
                    FloatingField(
                        "vae",
                    ),
                    css_class="col-auto",
                ),
                Column(
                    FloatingField(
                        "extra_activities",
                    ),
                    css_class="col-md",
                ),
                css_class="g-2",
            ),
        )
        self.add_input(
            Button(
                "cancel",
                "Page précédente",
                css_class="btn-secondary",
                onclick="window.location.href = '{}';".format(reverse("day_edit")),
            )
        )
        self.add_input(Submit("submit", "Page Suivante"))


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


class DaySignupFormsetHelper(FormHelper):
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
                *(
                    Column(Field(day))
                    for day in [
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
                ),
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


class ExtraParticipantInfoForm(forms.ModelForm):
    participant_name = forms.CharField(
        label="Nom du/de la participant·e", disabled=True
    )
    participant = forms.CharField(
        label="Participant", widget=forms.HiddenInput(), disabled=True
    )

    class Meta:
        model = ExtraParticipantInfo
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        if instance:
            self.fields["participant_name"].initial = (
                instance.participant.first_name + " " + instance.participant.last_name
            )


ExtraParticipantInfoFormSet = modelformset_factory(
    ExtraParticipantInfo,
    form=ExtraParticipantInfoForm,
    min_num=1,
    extra=0,
    can_delete=False,
)


class ExtraParticipantInfoFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = Layout(
            FloatingField(
                "participant_name",
            ),
            Fieldset(
                "{{ participant_name }}",
                "roadbook",
                "participant",
                "activite_21",
                "activite_25",
                "full_address",
                "emergency_contact",
                "share_contact_info_participants",
                "image_rights",
                "road_captain",
                "mechanicien",
                "healthpro",
                "animator",
                "comments",
            ),
        )
        self.add_input(Submit("submit", "Soumettre les informations"))

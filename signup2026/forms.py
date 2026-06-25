from datetime import date

from crispy_bootstrap5.bootstrap5 import FloatingField
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


class BaseParticipantFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        adult_cutoff = date(
            settings.DYNAMOBILE_FIRST_DAY.year - 18,
            settings.DYNAMOBILE_FIRST_DAY.month,
            settings.DYNAMOBILE_FIRST_DAY.day,
        )
        has_adult = any(
            form.cleaned_data.get("birthday") is not None
            and form.cleaned_data["birthday"] <= adult_cutoff
            for form in self.forms
            if not form.cleaned_data.get("DELETE", False)
        )
        if not has_adult:
            raise ValidationError(
                "Chaque groupe doit être composé au minimum d'un adulte."
            )


ParticipantFormSet = inlineformset_factory(
    Signup,
    Participant,
    form=ParticipantForm,
    formset=BaseParticipantFormSet,
    min_num=1,
    extra=0,
    can_delete=True,
)


class ParticipantFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = Layout(
            HTML("{% if forloop.first %}{%else%}<hr>{% endif %}"),
            Row(
                Column(FloatingField("first_name"), css_class="col-auto"),
                Column(FloatingField("last_name"), css_class="col-auto"),
                Column(FloatingField("email"), css_class="col-auto"),
                Column(FloatingField("phone"), css_class="col-auto"),
                Column(FloatingField("birthday"), css_class="col-auto"),
                Column(FloatingField("city"), css_class="col-auto"),
                Column(FloatingField("country"), css_class="col-auto"),
                Column(Field("DELETE"), css_class="col-auto"),
            ),
        )
        self.add_input(
            Button(
                "add_user", "➕ Ajouter un participant", css_class="btn-success btn-lg"
            )
        )
        self.add_input(Submit("submit", "Page Suivante"))


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
                Column(FloatingField("first_name"), css_class="col-auto"),
                Column(FloatingField("last_name"), css_class="col-auto"),
                *(Column(Field(day)) for day in [f"day{i}" for i in range(1, 10)]),
            ),
        )
        self.add_input(
            Button(
                "cancel",
                "Page précédente",
                css_class="btn-secondary",
                onclick="window.location.href = '{}';".format(
                    reverse("signup2026:group_edit")
                ),
            )
        )
        self.add_input(Submit("submit", "Page Suivante"))


class ExtraParticipantInfoForm(forms.ModelForm):
    class Meta:
        model = ExtraParticipantInfo
        fields = "__all__"
        exclude = ["participant"]


class FollowupExtraInfoForm(forms.ModelForm):
    """Post-registration follow-up form filled in by each participant.

    ``takes_car_back`` and ``arrive_day_before`` live on the related
    :class:`Participant`, so they are added as extra fields that are initialised
    from and saved back to the participant.

    The "Proposer votre aide" volunteer roles are hidden (and dropped from the
    form) for minor participants.
    """

    VOLUNTEER_FIELDS = (
        "road_captain",
        "mechanicien",
        "healthpro",
        "animator",
        "tandem_pilot",
    )

    arrive_day_before = forms.BooleanField(
        label="Logement le 16 juillet à Arlon",
        required=False,
    )
    takes_car_back = forms.ChoiceField(
        label=Participant._meta.get_field("takes_car_back").verbose_name,
        choices=Participant.CarBackChoice.choices,
    )

    class Meta:
        model = ExtraParticipantInfo
        fields = (
            "full_address",
            "emergency_contact",
            "july20_loop",
            "image_rights",
            "share_contact_info",
            "road_captain",
            "mechanicien",
            "healthpro",
            "animator",
            "tandem_pilot",
            "comments",
        )
        widgets = {
            "july20_loop": forms.RadioSelect,
        }
        labels = {
            "image_rights": (
                "J'autorise Dynamobile à diffuser des photos ou vidéos sur "
                "lesquelles j'apparais via son site internet et ses canaux de "
                "communication (page facebook)."
            ),
            "share_contact_info": (
                "J'accepte que mes coordonnées (nom, prénom, adresse, numéro de "
                "téléphone) soient partagées avec les autres participant.es de "
                "l'édition 2026."
            ),
            "animator": "Animations (précisez dans les commentaires)",
        }
        help_texts = {
            "july20_loop": "",
        }

    def __init__(self, *args, locked=False, **kwargs):
        super().__init__(*args, **kwargs)
        is_minor = False
        if self.instance and self.instance.pk:
            participant = self.instance.participant
            self.fields["takes_car_back"].initial = participant.takes_car_back
            self.fields["arrive_day_before"].initial = participant.arrive_day_before
            is_minor = participant.age_at_dynamobile_end() < 18
        if is_minor:
            for name in self.VOLUNTEER_FIELDS:
                self.fields.pop(name, None)
        if locked:
            for field in self.fields.values():
                field.disabled = True
        self.helper = self._build_helper(include_volunteer=not is_minor)

    @classmethod
    def _build_helper(cls, include_volunteer):
        helper = FormHelper()
        helper.form_tag = False  # the <form> tag is provided by the template
        # Keep the hidden modelformset ``id`` field, which is not in the layout.
        helper.render_unmentioned_fields = False
        helper.render_hidden_fields = True
        blocks = [
            Field("full_address"),
            Field("emergency_contact"),
            Field("arrive_day_before"),
            Field("takes_car_back"),
            Field("july20_loop"),
            Field("image_rights"),
            Field("share_contact_info"),
        ]
        if include_volunteer:
            blocks += [
                HTML('<p class="fw-bold mb-1">Proposer votre aide</p>'),
                Row(
                    Column(Field("road_captain"), css_class="col-auto"),
                    Column(Field("mechanicien"), css_class="col-auto"),
                    Column(Field("healthpro"), css_class="col-auto"),
                    Column(Field("animator"), css_class="col-auto"),
                    Column(Field("tandem_pilot"), css_class="col-auto"),
                ),
            ]
        blocks.append(Field("comments"))
        helper.layout = Layout(*blocks)
        return helper

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            participant = instance.participant
            participant.takes_car_back = self.cleaned_data["takes_car_back"]
            participant.arrive_day_before = self.cleaned_data["arrive_day_before"]
            participant.save(update_fields=["takes_car_back", "arrive_day_before"])
        return instance


FollowupExtraInfoFormSet = modelformset_factory(
    ExtraParticipantInfo,
    form=FollowupExtraInfoForm,
    extra=0,
    can_delete=False,
)


class ParticipantExtraForm(forms.ModelForm):
    first_name = forms.CharField(label="Prénom", disabled=True)
    last_name = forms.CharField(label="Nom", disabled=True)

    class Meta:
        model = Participant
        fields = (
            "first_name",
            "last_name",
            "vae",
            "arrive_day_before",
            "takes_car_back",
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
                Column(FloatingField("first_name"), css_class="col-auto"),
                Column(FloatingField("last_name"), css_class="col-auto"),
                Column(FloatingField("vae"), css_class="col-auto"),
                Column(Field("arrive_day_before"), css_class="col-auto"),
                Column(Field("takes_car_back"), css_class="col-auto"),
                Column(Field("extra_activities"), css_class="col-auto"),
            ),
        )
        self.add_input(
            Button(
                "cancel",
                "Page précédente",
                css_class="btn-secondary",
                onclick="window.location.href = '{}';".format(
                    reverse("signup2026:group_edit")
                ),
            )
        )
        self.add_input(Submit("submit", "Page Suivante"))

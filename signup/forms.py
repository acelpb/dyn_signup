from django import forms
from django.forms import BaseModelFormSet
from django.forms import inlineformset_factory

from .models import Participant, Signup


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        exclude = ("signup",)


class MultiParticipantForm(BaseModelFormSet):
    model = Participant
    form = ParticipantForm
    extra = 2
    can_order = False
    can_delete = True
    max_num = 15
    validate_max = False
    min_num = 1
    validate_min = False
    absolute_max = 15
    can_delete_extra = True

    def save(self, signup):
        for form in self.forms:
            form.instance.signup = signup
        super().save()

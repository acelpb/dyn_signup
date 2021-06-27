from collections import defaultdict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import inlineformset_factory
from django.urls import reverse_lazy
from django.views.generic import UpdateView, ListView

# Create your views here.
from .models import Signup, Participant, Ballad


class BalladView(ListView):
    template_name = "signup/ballads.html"
    model = Ballad


class ParticpantFormView(LoginRequiredMixin, UpdateView):
    template_name = "signup/particpant.html"
    form_class = inlineformset_factory(Signup, Participant, fields="__all__", can_delete=True, extra=1)

    def get_success_url(self):
        return reverse_lazy("participant_view")

    def get_object(self, queryset=None):
        signup, _ = Signup.objects.get_or_create(user=self.request.user)
        return signup

    def form_valid(self, form):
        new_particpants_per_ballad = defaultdict(list)
        for participant in form.extra_forms:
            if not form.has_changed():
                continue
            new_particpants_per_ballad[participant.cleaned_data['ballad']] += participant

        with transaction.atomic():
            for ballad, new_participants in new_particpants_per_ballad.items():
                remaining_spots = ballad.available()
                if remaining_spots < len(new_participants):
                    if remaining_spots == 0:
                        alert_message = f"I'acceptons plus de nouveau participants pour la ballade: {ballad.title}"
                    else:
                        alert_message = f"Il ne reste plus que {remaining_spots} pour la ballade: {ballad.title}"
                    error = ValidationError(alert_message, code='no_spots_left')
                    form._non_form_errors.append(error)
            if not form.non_form_errors():
                return super().form_valid(form)
        return self.form_invalid(form)


class ParticipantReviewView(ParticpantFormView):
    form_class = inlineformset_factory(Signup, Participant, fields="__all__", can_delete=False, extra=0)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reviewing_form'] = True
        formset = context['form']
        for form in formset.forms:
            for field in form.fields.values():
                field.required = False
                field.widget.attrs['disabled'] = 'disabled'
        return context

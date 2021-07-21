from collections import defaultdict
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import inlineformset_factory
from django.urls import reverse_lazy
from django.views.generic import UpdateView, ListView

# Create your views here.
from .models import Signup, Participant, Ride


class BalladView(ListView):
    template_name = "signup/ballads.html"
    model = Ride


class ParticpantFormView(UpdateView):
    template_name = "signup/particpant.html"
    form_class = inlineformset_factory(Signup, Participant, fields="__all__", can_delete=True, extra=1)

    def get_success_url(self):
        return reverse_lazy("participant_view")

    def get_object(self, queryset=None):
        if self.request.session.get('signup_id'):
            signup = Signup.objects.get(id=self.request.session['signup_id'])
        elif self.request.user.is_authenticated:
            signup, _ = Signup.objects.get_or_create(user=self.request.user)
        else:
            signup = Signup.objects.create()
        self.request.session['signup_id'] = signup.id
        return signup

    def form_valid(self, form):
        new_particpants_per_ballad = defaultdict(list)
        for participant in form.extra_forms:
            if not form.has_changed() or 'ballad' not in participant.cleaned_data:
                continue
            print(1, participant)
            new_particpants_per_ballad[participant.cleaned_data['ballad']].append(participant)

        with transaction.atomic():
            for ballad, new_participants in new_particpants_per_ballad.items():
                remaining_spots = ballad.available()
                print(new_participants)
                print(remaining_spots, len(new_participants))
                if remaining_spots < len(new_participants):
                    if remaining_spots == 0:
                        alert_message = f"Désolé, nous n'acceptons plus de nouveau participants pour la balade: {ballad.title}"
                    else:
                        alert_message = f"Désolé, mais pour cette balade il ne reste que {remaining_spots} pour cette balade: {ballad.title}"
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

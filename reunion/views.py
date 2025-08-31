# Create your views here.
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, UpdateView

from .forms import (
    ParticipantExtraFormSet,
    ParticipantExtraFormSetHelper,
    ParticipantForm,
    ParticipantFormSet,
    ParticipantFormSetHelper,
    ParticipantListReviewForm,
)
from .mixins import SignupStartedMixin
from .models import Participant, Signup


class CreateGroupView(SignupStartedMixin, FormView):
    """Define the list of participants for a group."""

    template_name = "signup/create_group.html"
    success_url = reverse_lazy("reunion:group_extra_info")

    form_class = inlineformset_factory(
        Signup, Participant, form=ParticipantForm, extra=0, can_delete=False
    )

    def get_form(self, form_class=None):
        return ParticipantFormSet(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

    def get_context_data(self, **kwargs):
        messages.info(
            self.request,
            "Formulaire d'inscription pour les retrouvailles 30 ans le 4 octobre 2025.",
        )
        return super().get_context_data(**kwargs, helper=ParticipantFormSetHelper)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class GroupExtraEditView(SignupStartedMixin, FormView):
    template_name = "signup/formset.html"
    success_url = reverse_lazy("reunion:validate")

    def get_form(self, form_class=None):
        return ParticipantExtraFormSet(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

    def get_context_data(self, **kwargs):
        messages.info(self.request, "Proposition d'aide.")
        return super().get_context_data(**kwargs, helper=ParticipantExtraFormSetHelper)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class GroupReviewView(SignupStartedMixin, UpdateView):
    template_name = "reunion/review-participants.html"
    success_url = reverse_lazy("reunion:completed_signup")

    form_class = ParticipantListReviewForm

    def form_valid(self, form):
        from django.utils.timezone import localdate

        signup: Signup = self.object
        signup.validated_at = localdate()
        for participant in signup.participants_set.all():
            age_at_reunion = participant.age_at_reunion()
            if 0 < age_at_reunion <= 6:
                participant.amount_due_calculated = 0
            if 6 < age_at_reunion <= 12:
                participant.amount_due_calculated = 10
            if 12 < age_at_reunion <= 18:
                participant.amount_due_calculated = 15
            if age_at_reunion > 18:
                participant.amount_due_calculated = 25
            participant.save()
        signup.save()
        return HttpResponseRedirect(self.success_url)


class CompletedSignupView(LoginRequiredMixin, DetailView):
    template_name = "reunion/completed-signup.html"
    model = Signup
    context_object_name = "signup"

    def get_object(self, queryset=None):
        return Signup.objects.filter(
            owner=self.request.user,
        ).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["partial_open"] = settings.DYNAMOBILE_START_PARTIAL_SIGNUP
        return context

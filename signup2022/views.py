from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, UpdateView, FormView, DetailView

from .forms import ParticipantFormSet, ParticipantForm, DaySignupFormset, ParticipantListReviewForm
from .mixins import SignupStartedMixin
from .models import Signup, Participant


class HomePage(TemplateView):
    template_name = "signup/index.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["registration_open"] = timezone.now() >= settings.DYNAMOBILE_START_SIGNUP
        kwargs["dynamobile_signup_period_start"] = settings.DYNAMOBILE_START_SIGNUP
        return kwargs


class GroupEditView(SignupStartedMixin, FormView):
    template_name = "signup/particpant.html"
    success_url = '/signup-2'

    form_class = inlineformset_factory(
        Signup, Participant, form=ParticipantForm, extra=0, can_delete=False
    )

    def get_form(self, form_class=None):
        return ParticipantFormSet(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ParticipantEditView(SignupStartedMixin, FormView):
    template_name = "signup/select-days.html"
    success_url = reverse_lazy('completed_signup')

    def get_form(self, form_class=None):
        return DaySignupFormset(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

    def form_valid(self, form):
        form.save()
        signup = self.get_object()
        signup.validated_at = timezone.now()
        signup.save()
        return super().form_valid(form)


class GroupReviewView(SignupStartedMixin, UpdateView):
    template_name = "signup/review-participants.html"
    success_url = reverse_lazy('day_edit')

    form_class = ParticipantListReviewForm

    def form_valid(self, form):
        participants = list(self.get_object().participant_set.all())
        for participant in participants:
            for day, _ in settings.DYNAMOBILE_DAYS:
                participant.d2022_07_18 = True
                participant.d2022_07_19 = True
                participant.d2022_07_20 = True
                participant.d2022_07_21 = True
                participant.d2022_07_22 = True
                participant.d2022_07_23 = True
                participant.d2022_07_24 = True
                participant.d2022_07_25 = True
        self.object.validated_at = timezone.now()
        with transaction.atomic():
            Participant.objects.bulk_update(participants, fields=(
                "d2022_07_18",
                "d2022_07_19",
                "d2022_07_20",
                "d2022_07_21",
                "d2022_07_22",
                "d2022_07_23",
                "d2022_07_24",
                "d2022_07_25",
            ))
            self.object.save()
        return HttpResponseRedirect(self.success_url)


class CompletedSignupView(LoginRequiredMixin, DetailView):
    template_name = "signup/completed-signup.html"
    model = Signup
    context_object_name = "signup"

    def get_object(self, queryset=None):
        return Signup.objects.filter(owner=self.request.user).first()

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, FormView, TemplateView, UpdateView

from .forms import (
    DaySignupFormset,
    DaySignupFormsetHelper,
    ParticipantExtraFormSet,
    ParticipantExtraFormSetHelper,
    ParticipantFormSet,
    ParticipantFormSetHelper,
)
from .mixins import SignupStartedMixin
from .models import Signup


class HomePage(TemplateView):
    template_name = "signup2026/index.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        user = self.request.user
        can_pre_signup = (
            user.is_authenticated
            and user.groups.filter(name="préinscriptions").exists()
        )
        kwargs["registration_open"] = (
            can_pre_signup or timezone.now() >= settings.DYNAMOBILE_START_SIGNUP
        )
        time_remaining = settings.DYNAMOBILE_START_SIGNUP - timezone.now()
        kwargs["hours_remaining"] = int(time_remaining.total_seconds() // 3600)
        kwargs["minutes_remaining"] = int(time_remaining.total_seconds() // 60 % 60)
        kwargs["start_signup"] = settings.DYNAMOBILE_START_SIGNUP
        kwargs["partial_open"] = settings.DYNAMOBILE_START_PARTIAL_SIGNUP
        kwargs["start"] = settings.DYNAMOBILE_FIRST_DAY
        kwargs["end"] = settings.DYNAMOBILE_LAST_DAY
        return kwargs


class CreateGroupView(SignupStartedMixin, FormView):
    template_name = "signup2026/create_group.html"
    success_url = reverse_lazy("signup2026:day_edit")
    form_class = ParticipantFormSet

    def get_form(self, form_class=None):
        return ParticipantFormSet(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, helper=ParticipantFormSetHelper)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class SelectDayView(SignupStartedMixin, FormView):
    template_name = "signup2026/formset.html"
    success_url = reverse_lazy("signup2026:group_extra_info")

    def get_form(self, form_class=None):
        return DaySignupFormset(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, helper=DaySignupFormsetHelper)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class GroupExtraEditView(SignupStartedMixin, FormView):
    template_name = "signup2026/extra-info.html"
    success_url = reverse_lazy("signup2026:review")

    def get_form(self, form_class=None):
        return ParticipantExtraFormSet(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, helper=ParticipantExtraFormSetHelper)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class GroupReviewView(SignupStartedMixin, UpdateView):
    template_name = "signup2026/review-participants.html"
    model = Signup
    fields = []  # No extra fields for now
    success_url = reverse_lazy("signup2026:completed")

    def form_valid(self, form):
        signup = self.get_object()
        signup.validated_at = timezone.now()
        signup.check_if_on_hold()
        signup.save()
        signup.calculate_amounts()
        email_context = {
            "signup": signup,
            "partial_open": settings.DYNAMOBILE_START_PARTIAL_SIGNUP,
        }
        send_mail(
            subject="Votre inscription à dynamobile",
            message=get_template("signup2026/email/email.txt").render(email_context),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[signup.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template("signup2026/email/email.html").render(
                email_context
            ),
        )
        return HttpResponseRedirect(self.success_url)


class CompletedSignupView(LoginRequiredMixin, DetailView):
    template_name = "signup2026/completed-signup.html"
    model = Signup
    context_object_name = "signup"

    def get_object(self, queryset=None):
        return Signup.objects.filter(
            owner=self.request.user,
            year=2026,
        ).first()

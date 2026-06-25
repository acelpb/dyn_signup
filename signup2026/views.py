from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.db.models import Case, Count, Q, Value, When
from django.http import HttpResponseRedirect
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, FormView, TemplateView, UpdateView

from .forms import (
    DaySignupFormset,
    DaySignupFormsetHelper,
    FollowupExtraInfoFormSet,
    FollowupExtraInfoFormSetHelper,
    ParticipantExtraFormSet,
    ParticipantExtraFormSetHelper,
    ParticipantFormSet,
    ParticipantFormSetHelper,
)
from .mixins import SignupStartedMixin
from .models import ExtraParticipantInfo, Participant, Signup


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
        has_vae = any(f.cleaned_data.get("vae") for f in form.forms if f.cleaned_data)
        if has_vae and not self.request.POST.get("vae_popup_confirmed"):
            return self.render_to_response(
                self.get_context_data(form=form, show_vae_modal=True)
            )
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

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["partial_open"] = settings.DYNAMOBILE_START_PARTIAL_SIGNUP
        return kwargs


class FollowupExtraInfoView(LoginRequiredMixin, TemplateView):
    """Post-registration follow-up form.

    Accessible to the logged-in user for every participant they may edit:
    all participants of the group(s) they own, plus the participant whose
    email matches the logged-in user's email. Matching is done on the email
    address of the person logging in.
    """

    template_name = "signup2026/followup-extra-info.html"

    def get_editable_participants(self):
        user = self.request.user
        return (
            Participant.objects.filter(
                signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
                signup_group__validated_at__isnull=False,
                signup_group__cancelled_at__isnull=True,
            )
            .filter(Q(signup_group__owner=user) | Q(email__iexact=user.email))
            .distinct()
        )

    def get_formset(self, data=None):
        participants = list(self.get_editable_participants())
        for participant in participants:
            ExtraParticipantInfo.objects.get_or_create(participant=participant)
        queryset = (
            ExtraParticipantInfo.objects.filter(participant__in=participants)
            .select_related("participant")
            .order_by("participant_id")  # ordre d'inscription
        )
        return FollowupExtraInfoFormSet(data, queryset=queryset)

    def get_context_data(self, **kwargs):
        kwargs.setdefault("helper", FollowupExtraInfoFormSetHelper())
        kwargs.setdefault("formset", self.get_formset())
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        formset = self.get_formset(data=request.POST)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Merci, vos réponses ont été enregistrées.")
            return HttpResponseRedirect(reverse("signup2026:followup_extra_info"))
        return self.render_to_response(self.get_context_data(formset=formset))


class KitchenView(TemplateView):
    template_name = "signup/kitchen.html"

    def get_context_data(self, **context):
        active = Participant.objects.with_age().filter(
            signup_group__validated_at__isnull=False,
            signup_group__on_hold_at__isnull=True,
            signup_group__cancelled_at__isnull=True,
        )
        days = (
            ("day1", "day 1"),
            ("day2", "day 2"),
            ("day3", "day 3"),
            ("day4", "day 4"),
            ("day5", "day 5"),
            ("day6", "day 6"),
            ("day7", "day 7"),
            ("day8", "day 8"),
            ("day9", "day 9"),
        )
        context["days"] = {
            label: {
                k: v
                for k, v in active.filter(
                    **{field: True},
                )
                .values(
                    age_group=Case(
                        When(age__lte=6, then=Value("a0_6")),
                        When(age__lte=12, then=Value("a6_12")),
                        When(age__lt=18, then=Value("a12_18")),
                        default=Value("a18plus"),
                    ),
                )
                .annotate(participants=Count("age_group"))
                .values_list("age_group", "participants")
            }
            for field, label in days
        }

        for _, label in days:
            total = sum(context["days"][label].values())
            context["days"][label]["total"] = total
            context["days"][label]["eaters"] = total - context["days"][label].get(
                "a0_6", 0
            )

        context["total_signups"] = active.count()
        context["total_vae"] = active.filter(vae=True).count()
        context["total_partials"] = active.filter(
            Q(day1=False)
            | Q(day2=False)
            | Q(day3=False)
            | Q(day4=False)
            | Q(day5=False)
            | Q(day6=False)
            | Q(day7=False)
            | Q(day8=False)
            | Q(day9=False)
        ).count()
        participants_this_year = Participant.objects.filter(
            signup_group__validated_at__isnull=False,
        )
        context["total_on_hold"] = participants_this_year.filter(
            signup_group__validated_at__isnull=False,
            signup_group__on_hold_at__isnull=True,
        ).count()
        context["total_on_hold_vae"] = participants_this_year.filter(
            signup_group__on_hold_vae=True
        ).count()
        context["total_on_hold_partial"] = participants_this_year.filter(
            signup_group__on_hold_partial=True
        ).count()

        return super().get_context_data(**context)

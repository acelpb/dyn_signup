from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import (
    AccessMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.db import models
from django.db.models import Case, Count, F, IntegerField, Q, Value, When, Window
from django.db.models.functions import (
    Cast,
    ExtractDay,
    ExtractMonth,
    ExtractYear,
    RowNumber,
)
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, FormView, TemplateView, UpdateView
from django_tables2 import SingleTableView, Table

from .forms import (
    DaySignupFormset,
    DaySignupFormsetHelper,
    ExtraParticipantInfoFormSet,
    ExtraParticipantInfoFormSetHelper,
    ParticipantExtraFormSet,
    ParticipantExtraFormSetHelper,
    ParticipantForm,
    ParticipantFormSet,
    ParticipantFormSetHelper,
    ParticipantListReviewForm,
)
from .mixins import SignupStartedMixin
from .models import ExtraParticipantInfo, Participant, Signup


class HomePage(TemplateView):
    template_name = "signup/index.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["registration_open"] = timezone.now() >= settings.DYNAMOBILE_START_SIGNUP
        time_remaining = settings.DYNAMOBILE_START_SIGNUP - timezone.now()
        kwargs["hours_remaining"] = int(time_remaining.total_seconds() // 3600)
        kwargs["minutes_remaining"] = int(time_remaining.total_seconds() // 60 % 60)
        kwargs["start_signup"] = settings.DYNAMOBILE_START_SIGNUP
        kwargs["partial_open"] = settings.DYNAMOBILE_START_PARTIAL_SIGNUP
        kwargs["start"] = settings.DYNAMOBILE_FIRST_DAY
        kwargs["end"] = settings.DYNAMOBILE_LAST_DAY
        return kwargs


class CreateGroupView(SignupStartedMixin, FormView):
    """Define the list of participants for a group."""

    template_name = "signup/create_group.html"
    success_url = reverse_lazy("day_edit")

    form_class = inlineformset_factory(
        Signup, Participant, form=ParticipantForm, extra=0, can_delete=False
    )

    def get_form(self, form_class=None):
        return ParticipantFormSet(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, helper=ParticipantFormSetHelper)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class GroupExtraEditView(SignupStartedMixin, FormView):
    template_name = "signup/formset.html"
    success_url = reverse_lazy("validate")

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


class SelectDayView(SignupStartedMixin, FormView):
    template_name = "signup/formset.html"
    success_url = reverse_lazy("group_extra_info")

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


class GroupReviewView(SignupStartedMixin, UpdateView):
    template_name = "signup/review-participants.html"
    success_url = reverse_lazy("day_edit")

    form_class = ParticipantListReviewForm

    def form_valid(self, form):
        from django.utils.timezone import localdate

        signup: Signup = self.object
        signup.validated_at = localdate()
        signup.check_if_on_hold()
        signup.save()
        signup.create_bill()
        return HttpResponseRedirect(self.success_url)


class CompletedSignupView(LoginRequiredMixin, DetailView):
    template_name = "signup/completed-signup.html"
    model = Signup
    context_object_name = "signup"

    def get_object(self, queryset=None):
        return Signup.objects.filter(
            owner=self.request.user,
            year=settings.DYNAMOBILE_LAST_DAY.year,
        ).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["partial_open"] = settings.DYNAMOBILE_START_PARTIAL_SIGNUP
        return context


class KitchenView(TemplateView):
    template_name = "signup/kitchen.html"

    def get_context_data(self, **context):
        active = Participant.objects.filter(
            signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
            signup_group__validated_at__isnull=False,
            signup_group__on_hold=False,
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
            signup_group__year=settings.DYNAMOBILE_LAST_DAY.year
        )
        context["total_on_hold"] = participants_this_year.filter(
            signup_group__on_hold=True
        ).count()
        context["total_on_hold_vae"] = participants_this_year.filter(
            signup_group__on_hold_vae=True
        ).count()
        context["total_on_hold_partial"] = participants_this_year.filter(
            signup_group__on_hold_partial=True
        ).count()

        return super().get_context_data(**context)


class PhilippesParticipantListView(PermissionRequiredMixin, TemplateView):
    template_name = "signup/philippes_participant_list.html"
    permission_required = ["is_admin"]

    def get_context_data(self, **context):
        now = timezone.now()
        context["participants"] = (
            Participant.objects.filter(signup_group__validated_at__isnull=False)
            .alias(
                birth_year=ExtractYear("birthday"),
                birth_month=ExtractMonth("birthday"),
                birth_day=ExtractDay("birthday"),
            )
            .annotate(
                age=Value(now.year)
                - F("birth_year")
                - Cast(
                    Q(birth_month__gt=Value(now.month))
                    | Q(
                        birth_month__exact=Value(now.month),
                        birth_day__gte=Value(now.day),
                    ),
                    output_field=IntegerField(),
                )
            )
        )
        return super().get_context_data(**context)


class ParticipantTable(Table):
    class Meta:
        model = Participant
        fields = (
            "rank",
            "signup_group_id",
            "last_name",
            "first_name",
            "day1",
            "day2",
            "day3",
            "day4",
            "day5",
            "day6",
            "day7",
            "day8",
            "day9",
            "vae",
        )
        template_name = "django_tables2/bootstrap5.html"


class AttendanceView(SingleTableView):
    model = Participant
    template_name = "signup/participant_table.html"
    table_class = ParticipantTable

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(**{"d" + self.kwargs["date"].isoformat().replace("-", "_"): True})
            .order_by(
                "last_name",
                "first_name",
            )
        )


class WaitingListView(PermissionRequiredMixin, SingleTableView):
    model = Participant
    template_name = "signup/participant_table.html"
    table_class = ParticipantTable

    def has_permission(self):
        return self.request.user.groups.filter(name="membres ca").exists()

    def get_queryset(self):
        waiting_participants = Participant.objects.filter(
            signup_group__on_hold=True,
            signup_group__cancelled_at=None,
            signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
        )
        return waiting_participants.annotate(
            ranking=models.Case(
                models.When(
                    signup_group__validated_at__lt=settings.DYNAMOBILE_START_PARTIAL_SIGNUP,
                    signup_group__on_hold_partial=False,
                    then=models.Value(1),
                ),
                models.When(
                    signup_group__validated_at__lt=settings.DYNAMOBILE_START_PARTIAL_SIGNUP,
                    signup_group__on_hold_partial=True,
                    then=models.Value(2),
                ),
                default=models.Value(3),
            )
        ).annotate(
            rank=Window(RowNumber(), order_by=["ranking", "signup_group__validated_at"])
        )


class ExtraInfoView(AccessMixin, UpdateView):
    fields = "__all__"

    def get_success_url(self):
        return reverse_lazy("completed_signup")

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated:
            return self.handle_no_permission()
        try:
            self.signup = Signup.objects.get(
                owner=user,
                year=settings.DYNAMOBILE_LAST_DAY.year,
                validated_at__isnull=False,
                cancelled_at__isnull=True,
                on_hold=False,
            )
        except Signup.DoesNotExist:
            self.signup = None
            participants = Participant.objects.filter(
                email=user.email,
                signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
                signup_group__validated_at__isnull=False,
                signup_group__cancelled_at__isnull=True,
                signup_group__on_hold=False,
            )
            if not participants.exists():
                messages.error(
                    request,
                    "Vous ne semblez pas inscrit, avez vous utiliseé la même adresse e-mail que lors de votre inscrition?",
                )
                return HttpResponseRedirect(reverse_lazy("index"))
            else:
                self.participants = participants
        return super().dispatch(request, *args, **kwargs)

    template_name = "signup/extra-info.html"

    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        self.object = None
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        self.object = None
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_form(self):
        kwargs = self.get_form_kwargs()
        kwargs.pop("instance")
        return ExtraParticipantInfoFormSet(**kwargs, queryset=self.get_queryset())

    def get_queryset(self):
        if self.signup is not None:
            for participant in self.signup.participant_set.all():
                ExtraParticipantInfo.objects.get_or_create(participant=participant)

            return ExtraParticipantInfo.objects.filter(
                participant__signup_group_id=self.signup.id
            )
        else:
            for participant in self.participants:
                ExtraParticipantInfo.objects.get_or_create(participant=participant)
            return ExtraParticipantInfo.objects.filter(
                participant__email=self.request.user.email
            )

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs, helper=ExtraParticipantInfoFormSetHelper()
        )

    def form_valid(self, form):
        form.save()
        messages.info(self.request, "Merci d'avoir rempli le formulaire.")
        return super().form_valid(form)

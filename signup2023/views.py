from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Case, When, Value, Count, IntegerField, F, Q
from django.db.models.functions import ExtractDay, ExtractYear, ExtractMonth, Cast
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, UpdateView, FormView, DetailView
from django_tables2 import SingleTableView, Table

from .forms import (
    ParticipantFormSet,
    ParticipantExtraFormSet,
    ParticipantForm,
    DaySignupFormset,
    ParticipantListReviewForm,
    ParticipantExtraForm,
)
from .mixins import SignupStartedMixin
from .models import Signup, Participant


class HomePage(TemplateView):
    template_name = "signup/index.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["registration_open"] = timezone.now() >= settings.DYNAMOBILE_START_SIGNUP
        kwargs["partial_open"] = settings.DYNAMOBILE_START_PARTIAL_SIGNUP
        kwargs["start"] = settings.DYNAMOBILE_FIRST_DAY
        kwargs["end"] = settings.DYNAMOBILE_LAST_DAY
        return kwargs


class CreateGroupView(SignupStartedMixin, FormView):
    """Define the list of participants for a group."""

    template_name = "signup/createg_group.html"
    success_url = reverse_lazy("day_edit")

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


class GroupExtraEditView(SignupStartedMixin, FormView):
    template_name = "signup/particpant.html"
    success_url = reverse_lazy("validate")

    form_class = inlineformset_factory(
        Signup, Participant, form=ParticipantExtraForm, extra=0, can_delete=False
    )

    def get_form(self, form_class=None):
        return ParticipantExtraFormSet(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class SelectDayView(SignupStartedMixin, FormView):
    template_name = "signup/select-days.html"
    success_url = reverse_lazy("group_extra_info")

    def get_form(self, form_class=None):
        return DaySignupFormset(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

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
        return Signup.objects.filter(owner=self.request.user).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["partial_open"] = settings.DYNAMOBILE_START_PARTIAL_SIGNUP
        return context


class KitchenView(TemplateView):
    template_name = "signup/kitchen.html"

    def get_context_data(self, **context):
        days = (
            ("pre_departure", "Veille"),
            *(
                ("d" + day_label.replace("-", "_"), day_label)
                for _, day_label in settings.DYNAMOBILE_DAYS
            ),
        )
        context["days"] = {
            label: {
                k: v
                for k, v in Participant.objects.filter(
                    signup_group__validated_at__isnull=False,
                    signup_group__on_hold=False,
                    signup_group__cancelled_at__isnull=True,
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
            context["days"][label]["eaters"] = total - context["days"][label]["a0_6"]

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
            "last_name",
            "first_name",
            "vae",
        )
        template_name = "django_tables2/bootstrap4.html"


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

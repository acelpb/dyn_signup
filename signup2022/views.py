from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Case, When, Value, Count
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
            self.object.check_if_on_hold()
            self.object.save()
        return HttpResponseRedirect(self.success_url)


class CompletedSignupView(LoginRequiredMixin, DetailView):
    template_name = "signup/completed-signup.html"
    model = Signup
    context_object_name = "signup"

    def get_object(self, queryset=None):
        return Signup.objects.filter(owner=self.request.user).first()


class KitchenView(TemplateView):
    template_name = "signup/kitchen.html"

    def get_context_data(self, **context):
        def _get_x_years_before(x):
            return settings.DYNAMOBILE_LAST_DAY.replace(year=settings.DYNAMOBILE_LAST_DAY.year - x)

        context['days'] = {
            day_formatted: {k: v for k, v in Participant.objects.filter(
                signup_group__validated_at__isnull=False,
                **{'d' + day_formatted.replace('-', '_'): True}
            ).values(age_group=Case(
                When(birthday__gte=_get_x_years_before(6), then=Value('a0_6')),
                When(birthday__gte=_get_x_years_before(12), then=Value('a6_12')),
                When(birthday__gte=_get_x_years_before(18), then=Value('a12_18')),
                default=Value('a18plus')),
            ).annotate(participants=Count("age_group")).values_list('age_group', "participants")
                            }
            for day, day_formatted in settings.DYNAMOBILE_DAYS
        }
        for _, day_formatted in settings.DYNAMOBILE_DAYS:
            context['days'][day_formatted]['total'] = sum(context['days'][day_formatted].values())

        return super().get_context_data(**context)

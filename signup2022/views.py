from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.generic import TemplateView, UpdateView, FormView

from .forms import ParticipantFormSet, ParticipantForm, DaySignupFormset
from .models import Signup, Participant, DaySignup


class HomePage(TemplateView):
    template_name = "signup/index.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["registration_open"] = timezone.now() >= settings.DYNAMOBILE_START_SIGNUP
        kwargs["dynamobile_signup_period_start"] = settings.DYNAMOBILE_START_SIGNUP
        print(settings.DYNAMOBILE_START_SIGNUP)
        return kwargs


class GroupEditView(LoginRequiredMixin, FormView):
    template_name = "signup/particpant.html"
    success_url = '/signup-2'

    form_class = inlineformset_factory(
        Signup, Participant, form=ParticipantForm, extra=0, can_delete=False
    )

    def get_object(self, queryset=None):
        if self.request.session.get('signup_id'):
            signup = Signup.objects.get(id=self.request.session['signup_id'])
        elif self.request.user.is_authenticated:
            signup, _ = Signup.objects.get_or_create(owner=self.request.user)
        else:
            signup = Signup.objects.create()
        self.request.session['signup_id'] = signup.id
        return signup

    def get_form(self, form_class=None):
        return ParticipantFormSet(
            **self.get_form_kwargs(),
            instance=self.get_object(),
        )

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ParticipantEditView(LoginRequiredMixin, FormView):
    template_name = "signup/particpant.html"
    success_url = '/signup-2'

    def get_form(self, form_class=None):
        (signup_group, _) = Signup.objects.get_or_create(owner=self.request.user)
        return DaySignupFormset(
            **self.get_form_kwargs(),
            instance=signup_group.participant_set.first(),
        )

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class GroupReviewView(LoginRequiredMixin, UpdateView):
    template_name = "signup/review-participants.html"
    success_url = '/signup-3'

    form_class = inlineformset_factory(
        Signup, Participant, form=ParticipantForm, extra=0, can_delete=False
    )

    def get_context_data(self, **kwargs):
        print(self.request)
        context = super().get_context_data(**kwargs)
        formset = context['form']
        for form in formset.forms:
            for field in form.fields.values():
                field.required = False
                field.widget.attrs['disabled'] = 'disabled'
        return context

    def get_object(self, queryset=None):
        if self.request.session.get('signup_id'):
            return Signup.objects.get(id=self.request.session['signup_id'])
        else:
            return Signup.objects.get(owner=self.request.user)

    def form_valid(self, form):
        complete_signup = []

        for participant in self.object.participant_set.all():
            for day, _ in settings.DYNAMOBILE_DAYS:
                complete_signup.append(DaySignup(day=day, participant=participant))
        self.object.validated_at = timezone.now()
        with transaction.atomic():
            DaySignup.objects.bulk_create(complete_signup)
            self.object.save()
        return HttpResponseRedirect(self.success_url)

    def form_invalid(self, form):
        return self.form_valid(form)

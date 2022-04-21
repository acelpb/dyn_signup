from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import TemplateView
from django.conf import settings
from .forms import ParticipantFormSet, ParticipantForm
from .models import Signup, Participant


class HomePage(TemplateView):
    template_name = "signup/index.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["registration_open"] = timezone.now() >= settings.DYNAMOBILE_START_SIGNUP
        kwargs["dynamobile_signup_period_start"] = settings.DYNAMOBILE_START_SIGNUP
        print(settings.DYNAMOBILE_START_SIGNUP)
        return kwargs


def create_participant(request):
    (signup_group, _) = Signup.objects.get_or_create(owner=request.user)
    participants = Participant.objects.filter(signup_group=signup_group)
    formset = ParticipantFormSet(request.POST or None)

    if request.method == "POST":
        if formset.is_valid():
            formset.instance = signup_group
            formset.save()
            return redirect("signup-participants")

    context = {
        "formset": formset,
        "participants": participants
    }

    return render(request, "create_participant.html", context)


def create_participant_form(request):
    form = ParticipantForm()
    context = {
        "form": form
    }
    return render(request, "partials/participant_form.html", context)

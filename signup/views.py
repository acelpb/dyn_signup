from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import inlineformset_factory
from django.urls import reverse_lazy
from django.views.generic import UpdateView, ListView

# Create your views here.
from .models import Signup, Participant, Ballad


class BalladView(ListView):
    template_name = "signup/ballads.html"
    model = Ballad

class ParticpantFormView(LoginRequiredMixin, UpdateView):
    template_name = "signup/particpant.html"
    form_class = inlineformset_factory(Signup, Participant, fields="__all__", can_delete=True, extra=1)

    def get_success_url(self):
        return reverse_lazy("participant_view")

    def get_object(self, queryset=None):
        signup, _ = Signup.objects.get_or_create(user=self.request.user)
        return signup

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

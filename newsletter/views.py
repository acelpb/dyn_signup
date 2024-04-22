from django.contrib import messages
from django.views.generic import FormView

from django import forms

from connectors.ovh import MailingList


class SignupToNewsletterForm(forms.Form):
    email = forms.EmailField()
    method = forms.ChoiceField(choices=(
        ('sub', 'S\'inscrire'),
        ('unsub', 'Se désinscrire'),
    ))


# Create your views here.
class SignupToNewsletterView(FormView):
    template_name = "newsletter/signup.html"
    form_class = SignupToNewsletterForm

    def form_valid(self, form):
        # display a successfully subbed message using django messages
        mailing_list = MailingList('newsletter')
        email = form.cleaned_data['email']
        if form.cleaned_data['method'] == 'sub':
            mailing_list.add_participants([email])
            messages.add_message(self.request,
                                 messages.INFO,
                                 "Bienvenue ! Vous êtes désormais inscrit dans la mailing list !")
        else:
            mailing_list.remove_participants([email])
            messages.add_message(self.request,
                                 messages.ERROR,
                                 "Vous êtes bien désinscrit. Vous ne recevrez donc plus de mail de Dynamobile.")

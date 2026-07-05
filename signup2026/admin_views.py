from django import forms, views
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.mixins import AccessMixin
from django.urls import reverse_lazy
from django.utils.functional import cached_property

from connectors.ovh import MailingList
from signup2026.models import Participant, Signup


class AdminRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class SyncEmails(forms.Form):
    sync = forms.ChoiceField(
        choices=(
            ("both", "Add new participants and remove unsubscribed perticipants."),
            ("remove", "Only remove people who have unsubscribed"),
            ("add", "Only add newy subscribed participants"),
        ),
        required=True,
    )


class PreviewEmailForm(forms.Form):
    custom_message = forms.CharField(
        widget=forms.Textarea, required=False, label="Custom message"
    )


class PreviewEmailView(AdminRequiredMixin, views.generic.FormView):
    template_name = "admin/signup2026/signup/preview_email.html"
    form_class = PreviewEmailForm

    @property
    def admin_site(self):
        return admin.site

    @cached_property
    def signup(self):
        return Signup.objects.with_amounts().get(pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        signup = self.signup
        return super().get_context_data(
            **{
                **kwargs,
                "title": f"Preview Email for Signup #{signup.id}",
                "opts": Signup._meta,
                "signup": signup,
                **self.admin_site.each_context(self.request),
            }
        )

    def form_valid(self, form):
        from django.core.mail import send_mail
        from django.template.loader import get_template

        signup = self.signup
        custom_message = form.cleaned_data.get("custom_message")
        context = {"signup": signup, "custom_message": custom_message}

        send_mail(
            subject=f"Information concernant votre inscription n°{signup.id} - Dynamobile",
            message=get_template("signup2026/email/custom_email.txt").render(context),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[signup.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template("signup2026/email/custom_email.html").render(
                context
            ),
        )
        messages.success(self.request, f"Email sent to {signup.owner.email}")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("admin:signup2026_signup_change", args=[self.signup.id])


class SyncMailingListFormView(AdminRequiredMixin, views.generic.FormView):
    template_name = "admin/signups/participants_email_sync.html"
    form_class = SyncEmails
    success_url = reverse_lazy("admin:signup2026_participant_changelist")

    @cached_property
    def mailing_list(self):
        return MailingList(
            f"participants{settings.DYNAMOBILE_LAST_DAY.year}",
            active_emails=Participant.active_emails,
        )

    def get_context_data(self, **kwargs):
        to_remove, to_add = self.mailing_list.check_mailing_list()
        return super().get_context_data(
            **{
                **kwargs,
                "title": "Sync Mailing List",
                "opts": Participant._meta,
                "to_add": to_add,
                "to_remove": to_remove,
            }
        )

    def form_valid(self, form):
        mailing_list = self.mailing_list
        to_remove, to_add = self.mailing_list.check_mailing_list()
        if form.cleaned_data["sync"] in {"both", "add"}:
            if not settings.DEBUG:
                mailing_list.add_participants(to_add)
            messages.add_message(
                self.request,
                messages.INFO,
                "The following participants where added to the mailing list: "
                + ", ".join(to_add),
            )
        if form.cleaned_data["sync"] in {"both", "remove"}:
            if not settings.DEBUG:
                mailing_list.remove_participants(to_remove)
            messages.add_message(
                self.request,
                messages.ERROR,
                "The following participants where removed from the mailing list: "
                + ", ".join(to_remove),
            )
        return super().form_valid(form)

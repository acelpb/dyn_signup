from django import forms, views
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.urls import reverse_lazy
from django.utils.functional import cached_property

from signup2023.models import Participant
from connectors.ovh import MailingList


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


class SyncMailingListFormView(AdminRequiredMixin, views.generic.FormView):
    template_name = "admin/signups/participants_email_sync.html"
    form_class = SyncEmails
    success_url = reverse_lazy("admin:signup2023_participant_changelist")

    @cached_property
    def mailing_list(self):
        return MailingList(f"participants{settings.DYNAMOBILE_LAST_DAY.year}")

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

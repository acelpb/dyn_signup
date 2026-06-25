import ovh
from django.conf import settings


class MailingList:
    def __init__(self, name, active_emails=None):
        self.name = name
        # Callable returning the set of emails that should be on the list.
        # Injected by the caller so the connector stays year/model agnostic.
        self._active_emails = active_emails
        self._ovh = ovh.Client(
            endpoint="ovh-eu",
            application_key=settings.OVH_API_KEY,
            application_secret=settings.OVH_API_SECRET,
            consumer_key=settings.OVH_API_CONSUMER,
        )

    def get_all_members(self):
        return self._ovh.get(
            f"/email/domain/dynamobile.net/mailingList/{self.name}/subscriber"
        )

    def check_mailing_list(self):
        if self._active_emails is None:
            raise ValueError(
                "MailingList was created without an `active_emails` source."
            )
        mailing_list_participants = {x.lower() for x in self.get_all_members()}
        active_participants = self._active_emails()
        to_remove = mailing_list_participants - active_participants
        to_add = active_participants - mailing_list_participants
        return to_remove, to_add

    def remove_participants(self, to_remove):
        for participant in to_remove:
            self._ovh.delete(
                f"/email/domain/dynamobile.net/mailingList/{self.name}/subscriber/{participant}"
            )

    def add_participants(self, new_participants):
        for participant in new_participants:
            if participant:
                self._ovh.post(
                    f"/email/domain/dynamobile.net/mailingList/{self.name}/subscriber/",
                    email=participant,
                )

#%%
import logging

from django.conf import settings
import ovh

from signup2022.models import Participant


class MailingList:

    def __init__(self, name):
        self.name = name
        self._ovh = ovh.Client(
            endpoint='ovh-eu',
            application_key=settings.OVH_API_KEY,
            application_secret=settings.OVH_API_SECRET,
            consumer_key=settings.OVH_API_CONSUMER,
        )

    def get_all_members(self):
        return self._ovh.get(f'/email/domain/dynamobile.net/mailingList/{self.name}/subscriber')


    def check_mailing_list(self):
        mailing_list_participants = set(self.get_all_members())
        mailing_list_participants = {x.lower() for x in mailing_list_participants}
        active_participants = Participant.active_emails()
        to_remove = mailing_list_participants - active_participants
        to_add = active_participants - mailing_list_participants
        return to_remove, to_add

    def remove_participants(self, to_remove):
        for participant in to_remove:
            self._ovh.delete(
                f'/email/domain/dynamobile.net/mailingList/{self.name}/subscriber/{participant}')

    def add_participants(self, new_participants):
        for participant in new_participants:
            if participant:
                self._ovh.post(
                    f'/email/domain/dynamobile.net/mailingList/{self.name}/subscriber/{participant}')

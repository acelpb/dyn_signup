#%%
import logging

from django.conf import settings
import ovh

_logger = logging.getLogger(__name__)

_client = ovh.Client(
    endpoint='ovh-eu',
    application_key=settings.OVH_API_KEY,
    application_secret=settings.OVH_API_SECRET,
    consumer_key=settings.OVH_API_CONSUMER,
)


def check_mailing_list(mailing_list, listed_participants):
    mailing_list_participants = _client.get(f'/email/domain/dynamobile.net/mailingList/{mailing_list}/subscriber')

    to_remove = set(mailing_list_participants) - set(listed_participants)
    send_missing_communications = set(listed_participants) - set(mailing_list_participants)
    return to_remove, send_missing_communications


def remove_participants(mailing_list, to_remove):
    _logger.debug("Removing the following participants %s", to_remove)
    for participant in to_remove:
        _client.delete(
            f'/email/domain/dynamobile.net/mailingList/participants2022/subscriber/{participant}')
        logging.debug("Particpant %s removed", participant)


def add_participants(mailing_list, new_participants):
    _logger.debug("Adding the following participants %s", to_remove)
    for participant in new_participants:
        if participant:
            _client.post(
                f'/email/domain/dynamobile.net/mailingList/participants2022/subscriber/{participant}')
            logging.debug("Particpant %s added", participant)
#%%


#%%
from signup2022.models import Participant, Signup

active_participants = set(Participant.objects.filter(signup_group__validated_at__isnull=False).values_list("email", flat=True))

active_participants |= set(Signup.objects.filter(validated_at__isnull=False).values_list('owner__email', flat=True))

active_participants.remove("")
active_participants = {x.lower() for x in active_participants}
#%%


mailing_list_participants = set(client.get("/email/domain/dynamobile.net/mailingList/participants2022/subscriber"))
mailing_list_participants = {x.lower() for x in mailing_list_participants}
#%%
missing = active_participants - mailing_list_participants
print(missing)

#%%
to_remove = mailing_list_participants - active_participants
print(to_remove)

#%%
for email in to_remove:
    result = client.delete(f'/email/domain/dynamobile.net/mailingList/participants2022/subscriber/{email}')
    print(result)

#%%
for email in to_remove:
    print(email)




"""Admin for the signup2026 app, split by model.

Importing the submodules here runs their @admin.register decorators.
"""

from .extra_info import ExtraInfoRessource, ExtraParticipantInfoAdmin
from .filters import ParticipantPayedFilter, SignupDayFilter, SignupStatusFilter
from .participant import ParticipantAdmin, ParticipantResource, PaymentParticipantAdmin
from .signup import SignupAdmin
from .waiting_list import WaitingListParticipantAdmin, unblock_participant

__all__ = [
    "ExtraInfoRessource",
    "ExtraParticipantInfoAdmin",
    "ParticipantAdmin",
    "ParticipantPayedFilter",
    "ParticipantResource",
    "PaymentParticipantAdmin",
    "SignupAdmin",
    "SignupDayFilter",
    "SignupStatusFilter",
    "WaitingListParticipantAdmin",
    "unblock_participant",
]

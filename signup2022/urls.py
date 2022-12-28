from django.urls import path, register_converter

from . import converters
from . import views

register_converter(converters.DateConverter, 'yyyy-mm-dd')

urlpatterns = [
    path("", views.HomePage.as_view(), name="index"),
    path("signup-1/", views.GroupEditView.as_view(), name="group_edit"),
    path("signup-2/", views.GroupReviewView.as_view(), name="participant_review"),
    path("signup-3/", views.ParticipantEditView.as_view(), name="day_edit"),
    path("review/", views.CompletedSignupView.as_view(), name="completed_signup"),
    path("kitchen/", views.KitchenView.as_view(), name="kitchen"),
    path("_secret_participants/", views.PhilippesParticipantListView.as_view(), name="secret"),
    path("presences/<yyyy-mm-dd:date>", views.AttendanceView.as_view(), name="attendance"),
]

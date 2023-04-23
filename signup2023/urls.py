from django.urls import path, register_converter

from . import converters
from . import views

register_converter(converters.DateConverter, "yyyy-mm-dd")

urlpatterns = [
    path("", views.HomePage.as_view(), name="index"),
    path("participants/", views.CreateGroupView.as_view(), name="group_edit"),
    path("select_days/", views.SelectDayView.as_view(), name="day_edit"),
    path("extra_info/", views.GroupExtraEditView.as_view(), name="group_extra_info"),
    path("validate/", views.GroupReviewView.as_view(), name="validate"),
    path("review/", views.CompletedSignupView.as_view(), name="completed_signup"),
    path("kitchen/", views.KitchenView.as_view(), name="kitchen"),
    path(
        "_secret_participants/",
        views.PhilippesParticipantListView.as_view(),
        name="secret",
    ),
    path(
        "presences/<yyyy-mm-dd:date>", views.AttendanceView.as_view(), name="attendance"
    ),
]

from django.urls import path

from .views import HomePage, GroupEditView, GroupReviewView, ParticipantEditView

urlpatterns = [
    path("", HomePage.as_view(), name="index"),
    path("signup-1/", GroupEditView.as_view(), name="group-edit"),
    path("signup-2/", GroupReviewView.as_view(), name="participant-review"),
    path("signup-3/", ParticipantEditView.as_view(), name="day-edit"),
    # path("review/", ParticipantReviewView.as_view())
]

from django.urls import path

from .views import ParticpantFormView, BalladView, ParticipantReviewView

urlpatterns = [
    path("", BalladView.as_view(), name="ballad_list"),
    path("review", ParticipantReviewView.as_view(), name="participant_view"),
    path("submit", ParticpantFormView.as_view(), name="participant_form"),
]

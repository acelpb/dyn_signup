from django.urls import path

from .views import HomePage, GroupEditView, GroupReviewView, ParticipantEditView, CompletedSignupView, KitchenView

urlpatterns = [
    path("", HomePage.as_view(), name="index"),
    path("signup-1/", GroupEditView.as_view(), name="group_edit"),
    path("signup-2/", GroupReviewView.as_view(), name="participant_review"),
    path("signup-3/", ParticipantEditView.as_view(), name="day_edit"),
    path("review/", CompletedSignupView.as_view(), name="completed_signup"),
    path("kitchen/", KitchenView.as_view(), name="kitchen"),
]

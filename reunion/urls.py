from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomePage.as_view(), name="index"),
    path("participants/", views.CreateGroupView.as_view(), name="group_edit"),
    path("extra_info/", views.GroupExtraEditView.as_view(), name="group_extra_info"),
    path("validate/", views.GroupReviewView.as_view(), name="validate"),
    path("review/", views.CompletedSignupView.as_view(), name="completed_signup"),
]

from django.urls import path

from . import views

app_name = "signup2026"

urlpatterns = [
    path("", views.HomePage.as_view(), name="home"),
    path("group/", views.CreateGroupView.as_view(), name="group_edit"),
    path("days/", views.SelectDayView.as_view(), name="day_edit"),
    path("extra/", views.GroupExtraEditView.as_view(), name="group_extra_info"),
    path("review/", views.GroupReviewView.as_view(), name="review"),
    path("completed/", views.CompletedSignupView.as_view(), name="completed"),
]

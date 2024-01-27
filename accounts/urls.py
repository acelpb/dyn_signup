from django.urls import path

from .views import AccountsDetailView

urlpatterns = [path("accountDetails", AccountsDetailView.as_view())]

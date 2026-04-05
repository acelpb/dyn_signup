from django.urls import path

from .views import AnnualAccountsView

urlpatterns = [
    path("annual/<int:year>/", AnnualAccountsView.as_view(), name="annual_accounts"),
]

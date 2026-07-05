from django.urls import path

from .mcp import McpServerView
from .views import (
    AnnualAccountsView,
    BillUploadAPIView,
    CreateApiTokenView,
    DeviceAuthApproveView,
    DeviceAuthStartView,
    DeviceAuthTokenView,
    PendingPaymentsView,
)

urlpatterns = [
    path("annual/<int:year>/", AnnualAccountsView.as_view(), name="annual_accounts"),
    path("payments/pending/", PendingPaymentsView.as_view(), name="pending_payments"),
    path("api/bills/", BillUploadAPIView.as_view(), name="api_bill_upload"),
    path("api/auth/device/", DeviceAuthStartView.as_view(), name="device_auth_start"),
    path(
        "api/auth/device/token/",
        DeviceAuthTokenView.as_view(),
        name="device_auth_token",
    ),
    path(
        "device/approve/<str:user_code>/",
        DeviceAuthApproveView.as_view(),
        name="device_auth_approve",
    ),
    path("tokens/new/", CreateApiTokenView.as_view(), name="api_token_create"),
    path("mcp/<str:token>/", McpServerView.as_view(), name="mcp_server"),
]

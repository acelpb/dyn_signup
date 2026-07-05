from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from django.utils.timezone import localdate
from django_object_actions import action

from reunion.admin import SignupAminMixin

from ..admin_views import PreviewEmailView
from ..models import Signup
from .inlines import (
    ParticipantDaysInline,
    ParticipantInfoInline,
)


@admin.register(Signup)
class SignupAdmin(SignupAminMixin, admin.ModelAdmin):
    """Signup lifecycle (validate, hold, cancel); payments live in
    PaymentSignupAdmin."""

    inlines = [ParticipantInfoInline, ParticipantDaysInline]

    change_actions = (
        "validate",
        "recalculate_amounts",
        "validate_signup",
        "cancel_signup",
        "put_on_hold_signup",
        "preview_email",
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/preview-email/",
                self.admin_site.admin_view(PreviewEmailView.as_view()),
                name="signup2026_signup_preview_email",
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        return super().get_queryset(request).with_amounts()

    def get_change_actions(self, request, object_id, form_url):
        actions = list(super().get_change_actions(request, object_id, form_url) or [])
        actions.append("preview_email")
        return actions

    @action(description="Preview & Send Email")
    def preview_email(self, request, obj):
        return redirect("admin:signup2026_signup_preview_email", pk=obj.pk)

    def validate(self, request, obj):
        obj.validated_at = localdate()
        obj.calculate_amounts()
        self.message_user(request, "Amounts calculated and signup validated.")

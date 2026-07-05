from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from django.utils.timezone import localdate
from django_object_actions import action

from reunion.admin import SignupAminMixin

from ..admin_views import PreviewEmailView
from ..models import Signup
from .filters import PayedFilter, SignupStatusFilter
from .inlines import (
    ParticipantDaysInline,
    ParticipantInfoInline,
    ParticipantPaymentsInline,
    SignupPaymentsInline,
)


@admin.register(Signup)
class SignupAdmin(SignupAminMixin, admin.ModelAdmin):
    """Signup lifecycle (validate, hold, cancel) and payment follow-up."""

    inlines = [
        ParticipantInfoInline,
        ParticipantDaysInline,
        ParticipantPaymentsInline,
        SignupPaymentsInline,
    ]

    list_display = (
        "id",
        "owner",
        "status",
        "amount_due_total",
        "amount_payed_total",
        "balance",
        "is_payed",
        "payment_confirmation_sent_at",
    )
    list_filter = (SignupStatusFilter, PayedFilter)
    search_fields = ("owner__first_name", "owner__last_name", "owner__email")

    readonly_fields = (
        "owner",
        "balance",
        "payment_confirmation_sent_at",
        "amount_due_total",
        "amount_payed_total",
    )

    change_actions = (
        "validate",
        "recalculate_amounts",
        "validate_signup",
        "cancel_signup",
        "put_on_hold_signup",
        "preview_email",
        "send_payment_confirmation",
        "accept_as_donation",
        "offer_refund",
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

    @action(description="Send payment confirmation")
    def send_payment_confirmation(self, request, signup):
        signup.send_payment_confirmation_mail()
        self.message_user(
            request, f"Payment confirmation sent to {signup.owner.email}."
        )
        return redirect("admin:signup2026_signup_change", signup.id)

    @action(description="Accept excess as donation")
    def accept_as_donation(self, request, signup):
        try:
            excess = signup.accept_excess_as_donation(request.user)
        except ValueError as e:
            self.message_user(request, str(e), level="error")
            return
        self.message_user(
            request, f"Converted {excess}€ to donation. Balance is now 0."
        )
        return redirect("admin:signup2026_signup_change", signup.id)

    @action(description="Offer refund")
    def offer_refund(self, request, signup):
        try:
            excess = signup.offer_refund(request.user)
        except ValueError as e:
            self.message_user(request, str(e), level="error")
            return
        self.message_user(
            request, f"Refund placeholder of {excess}€ created and offer recorded."
        )
        return redirect("admin:signup2026_signup_change", signup.id)

    def validate(self, request, obj):
        obj.validated_at = localdate()
        obj.calculate_amounts()
        self.message_user(request, "Amounts calculated and signup validated.")

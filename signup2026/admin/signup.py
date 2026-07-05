from django.contrib import admin, messages
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
    SignupPaymentsInline,
)


@admin.register(Signup)
class SignupAdmin(SignupAminMixin, admin.ModelAdmin):
    inlines = [ParticipantInfoInline, ParticipantDaysInline, SignupPaymentsInline]

    change_actions = (
        "validate",
        "recalculate_amounts",
        "validate_signup",
        "cancel_signup",
        "put_on_hold_signup",
        "send_payment_confirmation",
        "accept_as_donation",
        "offer_refund",
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
        if object_id is not None:
            signup = Signup.objects.with_amounts().get(pk=object_id)
            if signup.validated_at is not None:
                actions.append("send_payment_confirmation")
            if signup.balance is not None and signup.balance < 0:
                actions.append("accept_as_donation")
                actions.append("offer_refund")
        return actions

    @action(description="Preview & Send Email")
    def preview_email(self, request, obj):
        return redirect("admin:signup2026_signup_preview_email", pk=obj.pk)

    def validate(self, request, obj):
        obj.validated_at = localdate()
        obj.calculate_amounts()
        self.message_user(request, "Amounts calculated and signup validated.")

    @action(description="Send payment confirmation")
    def send_payment_confirmation(self, request, signup):
        signup.send_payment_confirmation_mail()
        messages.success(request, f"Payment confirmation sent to {signup.owner.email}.")
        return redirect("admin:signup2026_signup_change", signup.id)

    @action(description="Accept excess as donation")
    def accept_as_donation(self, request, signup):
        try:
            excess = signup.accept_excess_as_donation(request.user)
        except ValueError as e:
            messages.error(request, str(e))
            return
        messages.success(request, f"Converted {excess}€ to donation. Balance is now 0.")
        return redirect("admin:signup2026_signup_change", signup.id)

    @action(description="Offer refund")
    def offer_refund(self, request, signup):
        try:
            excess = signup.offer_refund(request.user)
        except ValueError as e:
            messages.error(request, str(e))
            return
        messages.success(
            request, f"Refund placeholder of {excess}€ created and offer recorded."
        )
        return redirect("admin:signup2026_signup_change", signup.id)

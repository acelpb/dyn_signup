from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone
from django_object_actions import DjangoObjectActions, action

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
class SignupAdmin(DjangoObjectActions, admin.ModelAdmin):
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
        "is_payed",
        "amount_due_total",
        "amount_payed_total",
        "balance",
        "payment_confirmation_sent_at",
    )
    list_filter = (SignupStatusFilter, PayedFilter)
    search_fields = ("owner__first_name", "owner__last_name", "owner__email")
    autocomplete_fields = ["owner"]

    fields = (
        "owner",
        "status",
        "balance",
        "validated_at",
        "on_hold_at",
        "cancelled_at",
        "payment_confirmation_sent_at",
        "comments",
    )
    readonly_fields = (
        "status",
        "owner",
        "balance",
        "validated_at",
        "cancelled_at",
        "on_hold_at",
        "payment_confirmation_sent_at",
        "amount_due_total",
        "amount_payed_total",
    )

    change_actions = (
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

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return (
                "status",
                "balance",
            )
        else:
            return self.readonly_fields

    def get_change_actions(self, request, object_id, form_url):
        if object_id is None:
            return []

        signup = Signup.objects.with_amounts().get(pk=object_id)
        actions = []

        if signup.status == "waiting payment" or signup.status == "payed":
            actions.extend(
                [
                    "cancel_signup",
                    "put_on_hold_signup",
                    "recalculate_amounts",
                ]
            )
        elif signup.status == "on hold":
            actions.extend(
                [
                    "validate_signup",
                    "cancel_signup",
                ]
            )
        else:
            actions.append("validate_signup")

        actions.append("preview_email")

        if signup.status == "payed":
            actions.append("send_payment_confirmation")

        if signup.balance is not None and signup.balance < 0:
            actions.extend(["accept_as_donation", "offer_refund"])

        return actions

    @action(description="Recalculate amounts")
    def recalculate_amounts(self, request, signup):
        signup.calculate_amounts()
        messages.success(request, "Amounts have been recalculated.")
        return redirect("admin:signup2026_signup_change", signup.id)

    @action(description="validate")
    def validate_signup(self, request, signup):
        if signup.validated_at:
            messages.warning(request, "This signup was already validated.")
        signup.validated_at = timezone.now()
        signup.calculate_amounts()
        signup.on_hold_at = None  # Remove on-hold status
        signup.cancelled_at = None  # Remove cancelled status
        signup.cancelled_reason = None
        signup.comments = (
            signup.comments or ""
        ) + f"\nSignup validated by {request.user.username}.\n\n"
        signup.save()
        return redirect("admin:signup2026_signup_change", signup.id)

    @action(description="cancel signup")
    def cancel_signup(self, request, signup):
        signup.cancelled_at = timezone.now()
        signup.comments = (
            signup.comments or ""
        ) + f"Signup cancelled by {request.user.username}."
        signup.save()
        messages.success(request, f"Signup #{signup.id} has been cancelled.\n\n")
        return redirect("admin:signup2026_signup_changelist")

    @action(description="Put signup on hold")
    def put_on_hold_signup(self, request, signup):
        signup.on_hold_at = timezone.now()
        signup.cancelled_at = None  # Remove cancelled status
        signup.comments = (
            signup.comments or ""
        ) + f"Signup put on hold by {request.user.username}.\n\n"
        signup.save()
        messages.success(request, f"Signup #{signup.id} has been put on hold.")
        return redirect("admin:signup2026_signup_change", signup.id)

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

    def status(self, obj: Signup):
        return obj.status

    status.admin_order_field = "status"
    status.short_description = "Status"

    def is_payed(self, obj: Signup):
        return obj.is_payed

    is_payed.admin_order_field = "is_payed"
    is_payed.boolean = True
    is_payed.short_description = "Payed"

    def amount_due(self, obj: Signup):
        return obj.amount_due

    amount_due.admin_order_field = "amount_due"
    amount_due.short_description = "amount due remaining"

    def amount_payed_total(self, obj: Signup):
        return obj.amount_payed_total

    def amount_due_total(self, obj: Signup):
        return obj.amount_due_total

    def balance(self, obj: Signup):
        return obj.balance

    balance.admin_order_field = "balance"
    balance.short_description = "Balance"

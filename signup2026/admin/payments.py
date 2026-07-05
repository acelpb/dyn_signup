from copy import copy

from django.conf import settings
from django.contrib import admin, messages
from django.shortcuts import redirect
from django_object_actions import DjangoObjectActions, action

from reunion.admin import PaymentInline

from ..models import Participant, PaymentParticipant, PaymentSignup, Signup
from .filters import PayedFilter
from .inlines import SignupPaymentsInline


@admin.register(PaymentSignup)
class PaymentSignupAdmin(DjangoObjectActions, admin.ModelAdmin):
    """Payment follow-up per signup: balance, confirmation, donation/refund."""

    inlines = [SignupPaymentsInline]
    list_display = (
        "id",
        "owner",
        "amount_due_total",
        "amount_payed_total",
        "balance",
        "is_payed",
        "payment_confirmation_sent_at",
    )
    list_filter = (PayedFilter,)
    search_fields = ("owner__first_name", "owner__last_name", "owner__email")
    fields = ("owner", "balance", "payment_confirmation_sent_at", "comments")
    readonly_fields = ("owner", "balance", "payment_confirmation_sent_at")

    change_actions = (
        "send_payment_confirmation",
        "accept_as_donation",
        "offer_refund",
    )

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        # Cancelled and on-hold signups stay visible: money may already have
        # moved and still need a refund or donation.
        return (
            super()
            .get_queryset(request)
            .filter(
                validated_at__isnull=False,
                year=settings.DYNAMOBILE_LAST_DAY.year,
            )
            .select_related("owner")
            .with_amounts()
        )

    def get_change_actions(self, request, object_id, form_url):
        actions = []
        if object_id is None:
            return actions
        signup = Signup.objects.with_amounts().get(pk=object_id)
        if signup.validated_at is not None:
            actions.append("send_payment_confirmation")
        if signup.balance is not None and signup.balance < 0:
            actions.append("accept_as_donation")
        # A participant can be overpaid even when the signup nets to zero
        # or more, so the refund action is gated per participant.
        if signup.participants_set.with_amounts().filter(balance__lt=0).exists():
            actions.append("offer_refund")
        return actions

    @admin.display(description="Total dû", ordering="amount_due_total")
    def amount_due_total(self, obj):
        return obj.amount_due_total

    @admin.display(description="Total payé", ordering="amount_payed_total")
    def amount_payed_total(self, obj):
        return obj.amount_payed_total

    @admin.display(description="Balance", ordering="balance")
    def balance(self, obj):
        return obj.balance

    @admin.display(boolean=True, description="Payé", ordering="balance")
    def is_payed(self, obj):
        if obj.balance is None:
            return None
        return obj.balance <= 0

    @action(description="Send payment confirmation")
    def send_payment_confirmation(self, request, signup):
        signup.send_payment_confirmation_mail()
        messages.success(request, f"Payment confirmation sent to {signup.owner.email}.")
        return redirect("admin:signup2026_paymentsignup_change", signup.id)

    @action(description="Accept excess as donation")
    def accept_as_donation(self, request, signup):
        try:
            excess = signup.accept_excess_as_donation(request.user)
        except ValueError as e:
            messages.error(request, str(e))
            return
        messages.success(request, f"Converted {excess}€ to donation. Balance is now 0.")
        return redirect("admin:signup2026_paymentsignup_change", signup.id)

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
        return redirect("admin:signup2026_paymentsignup_change", signup.id)


@admin.register(PaymentParticipant)
class PaymentParticipantAdmin(admin.ModelAdmin):
    """Payment follow-up per participant: balance, payed status, payments."""

    list_display = (
        "id",
        "signup_group",
        "first_name",
        "last_name",
        "amount_due_calculated",
        "balance",
        "is_payed",
    )

    ordering = ("signup_group", "id")
    list_filter = (PayedFilter,)
    list_editable = ("amount_due_calculated",)
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "signup_group__owner__email",
    )

    autocomplete_fields = ("signup_group",)
    fields = (
        "signup_group",
        "first_name",
        "last_name",
        "amount_due_calculated",
        "balance",
    )
    readonly_fields = ("balance",)

    inlines = [PaymentInline]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # Point the signup_group widget links (view/change icons) at the
        # payment admin (PaymentSignup) instead of the lifecycle SignupAdmin.
        if db_field.name == "signup_group":
            db_field = copy(db_field)
            db_field.remote_field = copy(db_field.remote_field)
            db_field.remote_field.model = PaymentSignup
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(
                signup_group__on_hold_at__isnull=True,
                signup_group__validated_at__isnull=False,
                signup_group__cancelled_at__isnull=True,
                signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
            )
            .select_related("signup_group")
            .with_amounts()
        )

    @admin.display(boolean=True, description="Payé", ordering="balance")
    def is_payed(self, obj: Participant):
        # No amount due computed yet -> unknown (renders the grey "?" icon).
        if obj.balance is None:
            return None
        return obj.balance <= 0

    @admin.display(description="Balance", ordering="balance")
    def balance(self, obj: Participant):
        # No amount due computed yet -> unknown (renders the grey "?" icon).
        if obj.balance is None:
            return None
        return obj.balance

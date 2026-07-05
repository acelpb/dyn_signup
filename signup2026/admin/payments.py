from copy import copy

from django.conf import settings
from django.contrib import admin

from reunion.admin import PaymentInline

from ..models import Participant, PaymentParticipant, Signup
from .filters import PayedFilter


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
        # lifecycle SignupAdmin.
        if db_field.name == "signup_group":
            db_field = copy(db_field)
            db_field.remote_field = copy(db_field.remote_field)
            db_field.remote_field.model = Signup
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

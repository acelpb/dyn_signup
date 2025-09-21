# Python
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.urls import reverse
from django.utils.safestring import mark_safe
from import_export.admin import ExportMixin

from accounts.models import OperationValidation

from .models import (
    CancelledParticipant,
    Participant,
    Signup,
    UnconfirmedParticipant,
    ValidatedParticipant,
)


class PaymentInline(GenericTabularInline):
    model = OperationValidation
    extra = 0
    ct_field_name = "content_type"
    id_field_name = "object_id"

    def get_formset(self, request, obj=None, **kwargs):
        self.fields = ("operation", "amount")
        return super().get_formset(request, obj, **kwargs)

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ParticipantInline(admin.TabularInline):
    model = Participant
    fk_name = "signup"
    extra = 0
    can_delete = True
    show_change_link = True
    fields = ("first_name", "last_name", "amount_due_remaining", "is_payed")
    readonly_fields = ("amount_due", "amount_due_remaining")


@admin.register(Signup)
class SignupAmin(admin.ModelAdmin):
    inlines = [ParticipantInline]
    search_fields = ("owner__first_name", "owner__last_name", "owner__email")
    autocomplete_fields = ["owner"]
    list_display = ("id", "owner", "status", "is_payed", "amount_due")

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


@admin.register(Participant)
class ParticipantAmin(admin.ModelAdmin):
    inlines = [PaymentInline]
    autocomplete_fields = ["signup"]
    readonly_fields = ("amount_due_calculated",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "signup",
                    "first_name",
                    "last_name",
                    "is_payed",
                    "email",
                    "phone",
                    "birthday",
                    "city",
                    "country",
                    "is_helping_friday",
                    "is_helping_saturday_morning",
                    "is_helping_saturday_evening",
                    "comments",
                )
            },
        ),
    )


# Admin classes that now rely on the proxy models' default managers
@admin.register(ValidatedParticipant)
class ValidatedParticipantAdmin(ExportMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "email",
        "signup_link",
        "is_helping_friday",
        "is_helping_saturday_morning",
        "is_helping_saturday_evening",
        "is_payed",
    )
    search_fields = ("first_name", "last_name", "email")
    list_filter = (
        "is_helping_friday",
        "is_helping_saturday_morning",
        "is_helping_saturday_evening",
        "is_payed",
    )
    inlines = [PaymentInline]

    def signup_link(self, obj):
        signup: Signup = obj.signup
        link = "<a href={}>{}</a>".format(
            reverse(
                "admin:{}_{}_change".format(
                    signup._meta.app_label, signup._meta.model_name
                ),
                args=(obj.signup_id,),
            ),
            str(signup),
        )
        return mark_safe(link)

    signup_link.short_description = "Signup"


@admin.register(UnconfirmedParticipant)
class UnconfirmedParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "email", "signup", "signup_status")
    search_fields = ("first_name", "last_name", "email")

    def signup_status(self, obj):
        return obj.signup.status

    signup_status.short_description = "Signup status"


@admin.register(CancelledParticipant)
class CancelledParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "email",
        "signup",
        "signup_status",
        "participant_cancelled",
        "signup_cancelled",
    )
    search_fields = ("first_name", "last_name", "email")

    def signup_status(self, obj):
        return obj.signup.status

    signup_status.short_description = "Signup status"

    def participant_cancelled(self, obj):
        return obj.cancelled_at is not None

    participant_cancelled.boolean = True
    participant_cancelled.short_description = "Participant cancelled"

    def signup_cancelled(self, obj):
        return obj.signup.cancelled_at is not None

    signup_cancelled.boolean = True
    signup_cancelled.short_description = "Signup cancelled"

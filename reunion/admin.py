from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.contenttypes.admin import GenericTabularInline
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_object_actions import DjangoObjectActions, action
from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field

from accounts.models import OperationValidation

from .models import (
    Participant,
    Signup,
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
    fields = ("first_name", "last_name", "birthday", "amount_due_remaining", "is_payed")
    readonly_fields = ("amount_due_remaining", "is_payed")

    def amount_due_remaining(self, obj: Participant):
        return obj.amount_due_remaining

    amount_due_remaining.admin_order_field = "amount_due_remaining"
    amount_due_remaining.short_description = "amount due remaining"

    def is_payed(self, obj: Participant):
        return obj.is_payed

    is_payed.admin_order_field = "is_payed"
    is_payed.boolean = True
    is_payed.short_description = "Payed"


class CanBePayedAdminMixin(admin.ModelAdmin):
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


@admin.register(Signup)
class SignupAmin(DjangoObjectActions, CanBePayedAdminMixin, admin.ModelAdmin):
    inlines = [ParticipantInline]
    search_fields = ("owner__first_name", "owner__last_name", "owner__email")
    autocomplete_fields = ["owner"]
    list_display = ("id", "owner", "status", "is_payed", "amount_due")
    fields = (
        "owner",
        "status",
        "amount_due",
        "validated_at",
        "on_hold_at",
        "cancelled_at",
        "comments",
    )
    readonly_fields = (
        "status",
        "amount_due",
        "validated_at",
        "cancelled_at",
        "on_hold_at",
    )

    change_actions = (
        "recalculate_amounts",
        "validate_signup",
        "cancel_signup",
        "put_on_hold_signup",
    )

    def get_change_actions(self, request, object_id, form_url):
        if object_id is not None:
            signup = Signup.objects.get(pk=object_id)
            if signup.status == "waiting payment" or signup.status == "payed":
                return [
                    "cancel_signup",
                    "put_on_hold_signup",
                    "recalculate_amounts",
                ]
            elif signup.status == "on hold":
                return [
                    "validate_signup",
                    "cancel_signup",
                ]
            else:
                return [
                    "validate_signup",
                ]

    @action(description="Recalculate amounts")
    def recalculate_amounts(self, request, signup):
        signup.calculate_amounts()
        messages.success(request, "Amounts have been recalculated.")
        return redirect("admin:reunion_signup_change", signup.id)

    @action(description="validate")
    def validate_signup(self, request, signup):
        if signup.validated_at:
            messages.warning(request, "This signup was already validated.")
        signup.validated_at = timezone.now()
        signup.calculate_amounts()
        signup.on_hold_at = None  # Remove on-hold status
        signup.cancelled_at = None  # Remove cancelled status
        signup.cancelled_reason = None
        signup.comments += f"Signup validated by {request.user.username}.\n\n"
        signup.save()
        return redirect("admin:reunion_signup_change", signup.id)

    @action(description="cancel signup")
    def cancel_signup(self, request, signup):
        signup.cancelled_at = timezone.now()
        signup.comments += f"Signup cancelled by {request.user.username}."
        signup.save()
        messages.success(request, f"Signup #{signup.id} has been cancelled.\n\n")
        return redirect("admin:reunion_signup_changelist")

    @action(description="Put signup on hold")
    def put_on_hold_signup(self, request, signup):
        signup.on_hold_at = timezone.now()
        signup.cancelled_at = None  # Remove cancelled status
        signup.comments += f"Signup put on hold by {request.user.username}.\n\n"
        signup.save()
        messages.success(request, f"Signup #{signup.id} has been put on hold.")
        return redirect("admin:reunion_signup_change", signup.id)

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


class StatusFilter(SimpleListFilter):
    title = _("Status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            (None, _("Validated")),
            ("payed", _("Payed")),
            ("payment_needed", _("Awaiting payment")),
            ("pending", _("Pending validation")),
            ("on hold", _("On hold")),
            ("cancelled", _("Cancelled")),
            ("all", _("Absolument tout")),
        )

    def queryset(self, request, queryset):
        filters = {
            None: {"status__in": ["waiting payment", "payed"]},
            "payed": {"is_payed": True},
            "payment_needed": {"status": "waiting payment"},
            "pending": {"status": "pending"},
            "on hold": {"status": "on hold"},
            "cancelled": {"status": "cancelled"},
            "all": {},
        }
        return queryset.distinct().filter(**filters[self.value()])


class ParticipantResource(resources.ModelResource):
    age = Field(attribute="age", column_name="age")

    class Meta:
        model = Participant
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "age",
            "city",
            "country",
            "is_helping_friday",
            "is_helping_saturday_morning",
            "is_helping_saturday_evening",
            "comments",
        )


@admin.register(Participant)
class ParticipantAmin(ExportMixin, CanBePayedAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "signup_link",
        "status",
        "amount_due",
        "is_payed",
        "email",
        "is_payed",
    )
    list_filter = (StatusFilter,)

    search_fields = ("first_name", "last_name", "email")
    inlines = [PaymentInline]
    autocomplete_fields = ["signup"]
    readonly_fields = ("is_payed", "amount_due", "amount_due_calculated")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "signup",
                    "first_name",
                    "last_name",
                    "amount_due",
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

    resource_classes = [ParticipantResource]

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

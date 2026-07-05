from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.contenttypes.admin import GenericTabularInline
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
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


class SignupAdmin(admin.ModelAdmin):
    search_fields = ("owner__first_name", "owner__last_name", "owner__email")
    list_display = ("id", "owner", "created_at", "validated_at")


class ParticipantAmin(ExportMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "signup_link",
        "status",
        "age",
        "amount_due_remaining",
        "is_payed",
        "email",
        "is_payed",
    )
    list_filter = (StatusFilter,)

    search_fields = ("first_name", "last_name", "email")
    inlines = [PaymentInline]
    autocomplete_fields = ["signup"]
    readonly_fields = (
        "is_payed",
        "amount_due_remaining",
        "amount_due_calculated",
        "amount_due_remaining",
        "age",
        "amount_due",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "signup",
                    "first_name",
                    "last_name",
                    "amount_due",
                    "amount_due_modified",
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

    def age(self, obj: Participant):
        return obj.age

    age.admin_order_field = "age"
    age.short_description = "Age"

    def status(self, obj: Participant):
        return obj.status

    status.admin_order_field = "status"
    status.short_description = "Status"

    def is_payed(self, obj: Participant):
        return obj.is_payed

    is_payed.admin_order_field = "is_payed"
    is_payed.boolean = True
    is_payed.short_description = "Payed"

    def amount_due(self, obj: Participant):
        return obj.amount_due

    amount_due.admin_order_field = "amount_due"
    amount_due.short_description = "amount due"

    def amount_due_remaining(self, obj: Participant):
        return obj.amount_due_remaining

    amount_due_remaining.admin_order_field = "amount_due_remaining"
    amount_due_remaining.short_description = "amount due remaining"


admin.site.register(Signup, SignupAdmin)
admin.site.register(Participant, ParticipantAmin)

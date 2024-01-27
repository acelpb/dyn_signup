from django.contrib.admin import TabularInline
from django.contrib.contenttypes.admin import GenericTabularInline

from accounts.forms import VentilationForm
from accounts.models import OperationValidation, ExpenseFile


class PaymentInline(GenericTabularInline):
    verbose_name = "ventilation"
    verbose_name_plural = "ventilation"
    form = VentilationForm
    model = OperationValidation
    extra = 0
    ct_field_name = "content_type"
    id_field_name = "object_id"
    can_delete = False
    can_edit = False

    def has_view_permission(self, request, obj=None):
        return True


class ExpenseFileInline(TabularInline):
    verbose_name = "pièce lié"
    verbose_name_plural = "pièces liés"
    model = ExpenseFile
    can_delete = False
    can_edit = False
    extra = 0

    def has_view_permission(self, request, obj=None):
        return True


class JustificationInline(TabularInline):
    verbose_name = "Justificatif lié"
    verbose_name_plural = "Justificatifs liés"
    model = OperationValidation
    extra = 0
    fields = (
        "justification_link",
        "amount",
        "validation_type",
    )
    readonly_fields = (
        "justification_link",
        "amount",
        "validation_type",
    )
    can_delete = False
    can_edit = False

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        if obj is None:
            return True
        else:
            return False

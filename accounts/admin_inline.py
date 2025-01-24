from django.contrib.admin import TabularInline
from django.contrib.contenttypes.admin import GenericTabularInline, GenericStackedInline

from accounts.forms import VentilationForm, CreateVentilationForm
from accounts.models import OperationValidation, ExpenseFile


class PaymentInline(GenericStackedInline):
    hidden_fields = ["content_type", "object_id", "operation"]
    verbose_name = ""
    verbose_name_plural = "ventilation"
    form = CreateVentilationForm
    model = OperationValidation
    extra = 0
    ct_field_name = "content_type"
    id_field_name = "object_id"
    can_delete = True
    can_edit = True

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        if obj is None:
            return True
        else:
            return False


class ExpenseFileInline(TabularInline):
    verbose_name = "pièce lié"
    verbose_name_plural = "pièces liés"
    model = ExpenseFile
    can_delete = True
    can_edit = True
    extra = 1

    def has_view_permission(self, request, obj=None):
        return True


class JustificationInline(TabularInline):
    verbose_name = "Justificatif lié"
    verbose_name_plural = "Justificatifs liés"
    model = OperationValidation
    extra = 1
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

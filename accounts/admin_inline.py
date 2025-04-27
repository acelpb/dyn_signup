from django.contrib.admin import TabularInline
from django.contrib.contenttypes.admin import GenericStackedInline

from accounts.forms import CreateVentilationForm
from accounts.models import ExpenseFile, OperationValidation


class PaymentInline(GenericStackedInline):
    verbose_name = ""
    verbose_name_plural = "ventilation"
    form = CreateVentilationForm
    model = OperationValidation
    extra = 0
    ct_field_name = "content_type"
    id_field_name = "object_id"

    def get_formset(self, request, obj=None, **kwargs):
        if request.user.is_superuser:
            self.exclude = ()
        else:
            self.exclude = ("content_type", "object_id", "operation")
        return super().get_formset(request, obj, **kwargs)

    def has_view_permission(self, request, obj=None):
        return True


class ExpenseFileInline(TabularInline):
    model = ExpenseFile
    can_delete = True
    can_edit = True
    extra = 1

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        if obj is None or (hasattr(obj, "validated") and obj.validated is False):
            return True
        else:
            return False

    def has_delete_permission(self, request, obj=None):
        if obj is None or (hasattr(obj, "validated") and obj.validated is False):
            return True
        else:
            return False

    def has_change_permission(self, request, obj=None):
        if obj is None or (hasattr(obj, "validated") and obj.validated is False):
            return True
        else:
            return False


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

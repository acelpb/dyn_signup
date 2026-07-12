from django import forms
from django.contrib.admin import TabularInline
from django.contrib.contenttypes.admin import GenericStackedInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet

from accounts.forms import CreateVentilationForm
from accounts.models import Bill, ExpenseFile, OperationValidation


class PaymentFormSet(BaseGenericInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.deleted_forms:
            if form.instance.pk and form.instance.operation_id:
                raise forms.ValidationError(
                    "Une ligne déjà réglée ne peut pas être supprimée."
                )


class PaymentInline(GenericStackedInline):
    verbose_name = ""
    verbose_name_plural = "ventilation"
    form = CreateVentilationForm
    formset = PaymentFormSet
    model = OperationValidation
    extra = 0
    ct_field_name = "content_type"
    id_field_name = "object_id"
    # Settling happens through the settle endpoints, never by editing the
    # operation directly; it is only displayed.
    readonly_fields = ("operation",)

    @staticmethod
    def _locked(obj):
        """Ventilation is locked once the parent no longer accepts edits.

        A bill stays editable until it is fully paid; an expense report
        until it is validated.
        """
        if obj is None:
            return False
        if isinstance(obj, Bill):
            return obj.is_paid
        return bool(getattr(obj, "validated", False))

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return not self._locked(obj)

    def has_delete_permission(self, request, obj=None):
        return not self._locked(obj)

    def has_change_permission(self, request, obj=None):
        return not self._locked(obj)


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
    extra = 0
    fields = (
        "justification_link",
        "content_type",
        "object_id",
        "amount",
        "validation_type",
    )
    readonly_fields = ("justification_link",)
    can_delete = False
    can_add = True

    def has_view_permission(self, request, obj=None):
        return True

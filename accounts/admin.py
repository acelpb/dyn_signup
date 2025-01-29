from datetime import datetime

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db.models import BooleanField, ExpressionWrapper, F, Q, Sum

from .admin_inline import ExpenseFileInline, PaymentInline

# Register your models here.
from .admin_operation import OperationAdmin
from .models import (
    Account,
    Bill,
    ExpenseReport,
    Operation,
    OperationValidation,
)

admin.site.register(Operation, OperationAdmin)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "IBAN")


@admin.register(OperationValidation)
class OperationValidationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "operation",
        "amount",
        "validation_type",
        "content_type",
    )

    list_filter = (("operation", admin.EmptyFieldListFilter), "validation_type")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ["operation", "amount", "event"]
        else:
            return super().get_readonly_fields(request, obj)


# @admin.register(SignupOperation)
# class InscriptionValidationAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'operation',
#         'amount',
#         'signup_group',
#     )
#
#     def get_readonly_fields(self, request, obj=None):
#         if obj:
#             return ['operation', 'amount', 'event']
#         else:
#             return super().get_readonly_fields(request, obj)
#
#     def get_form(self, request, obj=None, change=False, **kwargs):
#         return SignupOperationForm
#
#     def signup_group(self, instance):
#         return instance.object_id


# @admin.register(Justification)
class JustificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "file",
    )
    inlines = [PaymentInline]

    pass


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("date", "name", "file", "amount", "remaining_to_pay", "payed")

    inlines = [PaymentInline]

    ordering = ("-date",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.alias(payed_amount=Sum("payments__amount") + F("amount")).annotate(
            _payed=ExpressionWrapper(
                Q(payed_amount__exact=0), output_field=BooleanField()
            )
        )

    def remaining_to_pay(self, inst):
        return inst.amount + sum(
            p.amount for p in inst.payments.filter(operation__isnull=False)
        )

    def payed(self, inst):
        return inst._payed

    payed.boolean = True
    payed.admin_order_field = "_payed"


@admin.register(ExpenseReport)
class ExpenseReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "submitted_date",
        "beneficiary",
        "iban",
        "total",
        "remaining_to_pay",
        "signed",
        "validated",
    )
    list_filter = ("submitted_date", "signed", "validated")
    readonly_fields = ("total",)
    fields = (
        "total",
        "iban",
        "comments",
    )
    inlines = [PaymentInline, ExpenseFileInline]

    def remaining_to_pay(self, obj):
        remaining_to_pay = OperationValidation.objects.filter(
            operation__isnull=True,
            content_type=ContentType.objects.get_for_model(obj),
            object_id=obj.id,
        ).aggregate(remaining_to_pay=Sum("amount"))["remaining_to_pay"]
        if remaining_to_pay is not None:
            return f"{remaining_to_pay:.2f} €"
        return None

    def get_fields(self, request, obj=None):
        if request.user.is_superuser or request.user.has_perm("accounts.can_validate"):
            return (self.fields[0], "beneficiary", "validated", self.fields[1:])
        else:
            return self.fields

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            # Only set added_by during the first save.
            obj.beneficiary = request.user
            obj.submitted_date = datetime.now()
            current_year = datetime.now().year
            expense_number = (
                ExpenseReport.objects.filter(submitted_date__year=current_year).count()
                + 1
            )
            obj.title = f"{current_year}-{expense_number:04}"
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(Q(beneficiary=request.user))

    def has_change_permission(self, request, obj=None):
        if obj:
            if obj.validated:
                return False
            if obj.beneficiary == request.user or request.user.is_superuser:
                return True
        return False

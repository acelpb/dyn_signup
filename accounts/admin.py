from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Sum, Q, BooleanField, ExpressionWrapper

from .admin_inline import PaymentInline, ExpenseFileInline
from .models import (
    OperationValidation,
    Bill,
    ExpenseReport,
    Account,
    Operation,
)

# Register your models here.
from .admin_operation import OperationAdmin

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
        "total",
        "remaining_to_pay",
        "signed",
        "validated",
    )
    list_filter = ("submitted_date", "signed", "validated")
    fields = (
        "title",
        "beneficiary",
        "submitted_date",
        "signed",
        "validated",
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

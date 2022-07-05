from django.contrib import admin
from django.db.models import F, Sum, Q, BooleanField, ExpressionWrapper, Value, DecimalField

from .models import Operation, OperationValidation, Account


# Register your models here.

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'IBAN')


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "date",
        "description",
        "amount",
        "counterparty_IBAN",
        "counterparty_name",
        "communication",
        "reference",
        'justified',
    )
    ordering = ("-year", '-number')

    date_hierarchy = "date"
    list_filter = ("year", 'account__name')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.alias(justified_amount=Sum('operationvalidation__amount') - F('amount')).annotate(
            _justified=ExpressionWrapper(Q(justified_amount__exact=0), output_field=BooleanField())
        )

    def justified(self, inst):
        return inst._justified
    justified.boolean = True
    justified.admin_order_field = '_justified'

    def has_change_permission(self, request, obj=None, **kwargs):
        if obj is None:
            return False
        else:
            return False


@admin.register(OperationValidation)
class OperationValidationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'operation',
        'amount',
        'content_type',
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['operation', 'amount', 'event']
        else:
            return super().get_readonly_fields(request, obj)

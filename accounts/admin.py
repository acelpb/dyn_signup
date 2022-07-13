from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import F, Sum, Q, BooleanField, ExpressionWrapper
from import_export.admin import ImportMixin

from .format import BPostCSV
from .forms import SignupOperationForm
from .models import Operation, Account, OperationValidation, SignupOperation
# Register your models here.
from .resource import OperationResource


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'IBAN')


class JustifiedFilter(SimpleListFilter):
    title = "Opération vérifiée"
    parameter_name = "justified"  # you can put anything here

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ("valid", "✓"),
            ("unkown", "?"),
            ("invalid", "❌"),
        ]

    def queryset(self, request, queryset):
        filters = {
            "valid": {'_justified': True},
            "unkown": {'_justified__isnull': True},
            "invalid": {'_justified': False},
            None: {},
        }
        return queryset.distinct().filter(**filters[self.value()])


@admin.register(Operation)
class OperationAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = OperationResource

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
    list_filter = ("year", 'account__name', JustifiedFilter)

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
            return super().has_change_permission(request, **kwargs)
        else:
            return False

    def get_import_formats(self):
        return [BPostCSV]


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


@admin.register(SignupOperation)
class InscriptionValidationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'operation',
        'amount',
        'signup_group',
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['operation', 'amount', 'event']
        else:
            return super().get_readonly_fields(request, obj)

    def get_form(self, request, obj=None, change=False, **kwargs):
        return SignupOperationForm

    def signup_group(self, instance):
        return instance.object_id

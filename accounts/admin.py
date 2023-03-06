from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter, TabularInline
from django.contrib.contenttypes.admin import GenericTabularInline
from django.db.models import F, Sum, Q, BooleanField, ExpressionWrapper, Func
from django.db.models.functions import Round
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from import_export.admin import ImportMixin

from .admin_custom_views import LinkToBillView, LinkToSignupView
from .format import BPostCSV
from .forms import SignupOperationForm, VentilationForm
from .models import Operation, Account, OperationValidation, SignupOperation, Bill, ExpenseReport, Justification, ExpenseFile
# Register your models here.
from .resource import OperationResource


class PaymentInline(GenericTabularInline):
    verbose_name = "ventilation"
    verbose_name_plural = "ventilation"
    form = VentilationForm
    model = OperationValidation
    extra = 3
    ct_field_name = 'content_type'
    id_field_name = 'object_id'
    can_delete = False
    can_edit = False

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj):
        if obj is None:
            return True
        else:
            return False


class ExpenseFileInline(TabularInline):
    verbose_name = "pièce lié"
    verbose_name_plural = "pièces liés"
    model = ExpenseFile
    can_delete = False
    can_edit = False

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        if obj is None:
            return True
        else:
            return False


class JustificationInline(TabularInline):
    verbose_name = "Justificatif lié"
    verbose_name_plural = "Justificatifs liés"
    model = OperationValidation
    extra = 0
    readonly_fields = ('operation', 'amount',)
    can_delete = False
    can_edit = False

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        if obj is None:
            return True
        else:
            return False


# @admin.register(Account)
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
        'justified_amount',
    )
    ordering = ("-year", '-number')
    search_fields = ["counterparty_IBAN", "counterparty_name", "communication"]

    date_hierarchy = "date"
    list_filter = ("year", 'account__name', JustifiedFilter)

    actions = ["link_selected_operations_to_bill",
               "link_selected_operations_to_signup",
               "cancel_each_other_out",
               ]

    @admin.action(description='Link selected operations to bill')
    def link_selected_operations_to_bill(self, request, queryset):
        selected = queryset.values_list('pk', flat=True)
        return HttpResponseRedirect(
            reverse('admin:accounts_operation_link_to_bill') + '?operations=%s' % (
                ','.join(str(pk) for pk in selected),
            )
        )

    @admin.action(description="Annule l'un l'autre")
    def cancel_each_other_out(self, request, queryset):
        try:
            first, second = queryset.all()
        except ValueError:
            messages.add_message(request, messages.ERROR, "Select exactly two operations")
            return HttpResponseRedirect(reverse("admin:accounts_operation_changelist"))

        if first.amount != -second.amount:
            messages.add_message(request, messages.ERROR, "Select only operations that cancel each other.")
            return HttpResponseRedirect(reverse("admin:accounts_operation_changelist"))

        OperationValidation.objects.create(
            operation=first,
            created_by=request.user,
            event=second,
            amount=first.amount,
        )
        OperationValidation.objects.create(
            operation=second,
            created_by=request.user,
            event=first,
            amount=second.amount,
        )
        return HttpResponseRedirect(reverse("admin:accounts_operation_changelist"))

    @admin.action(description='Link selected operations to signup')
    def link_selected_operations_to_signup(self, request, queryset):
        selected = queryset.values_list('pk', flat=True)
        return HttpResponseRedirect(
            reverse('admin:accounts_operation_link_to_signup') + '?operations=%s' % (
                ','.join(str(pk) for pk in selected),
            )
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.alias(_justified_amount=Round(
            Sum('operationvalidation__amount') - F('amount'), 2)
        ).annotate(
            _justified_amount=F('_justified_amount'),
            _justified=ExpressionWrapper(Q(_justified_amount__exact=0), output_field=BooleanField())
        )

    def justified_amount(self, inst):
        return inst._justified_amount

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

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('link_to_bill/',
                 self.admin_site.admin_view(LinkToBillView.as_view()),
                 name='%s_%s_link_to_bill' % self.get_model_info()),
            path('link_to_signup/',
                 self.admin_site.admin_view(LinkToSignupView.as_view()),
                 name='%s_%s_link_to_signup' % self.get_model_info()),
        ]
        return my_urls + urls


@admin.register(OperationValidation)
class OperationValidationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'operation',
        'amount',
        'validation_type',
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


# @admin.register(Justification)
class JustificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'file',)
    inlines = [PaymentInline]

    pass


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('date', 'name', 'file', 'remaining_to_pay', 'payed')

    inlines = [PaymentInline]

    ordering = ('-date',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.alias(payed_amount=Sum('payments__amount') + F('amount')).annotate(
            _payed=ExpressionWrapper(Q(payed_amount__exact=0), output_field=BooleanField())
        )

    def remaining_to_pay(self, inst):
        return inst.amount + sum(p.amount for p in inst.payments.all())

    def payed(self, inst):
        return inst._payed

    payed.boolean = True
    payed.admin_order_field = '_payed'


@admin.register(ExpenseReport)
class ExpenseReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'submitted_date', 'beneficiary', 'total')
    fields = ('title', 'beneficiary', 'submitted_date', 'signed', 'validated', 'comments')
    inlines = [PaymentInline, ExpenseFileInline]

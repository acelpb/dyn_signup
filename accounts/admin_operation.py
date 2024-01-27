from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.db.models import Sum, F, ExpressionWrapper, Q, BooleanField
from django.db.models.functions import Round
from django.http import HttpResponseRedirect
from django.urls import reverse, path
from import_export.admin import ImportMixin

from accounts.admin_custom_views import (
    LinkToBillView,
    LinkToSignupView,
    LinkToExpenseReportView,
)
from accounts.admin_inline import JustificationInline
from accounts.format import BPostCSV, FortisCSV
from accounts.models import OperationValidation, ExpenditureChoices, IncomeChoices
from accounts.resource import OperationResource


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
            "valid": {"_justified": True},
            "unkown": {"_justified__isnull": True},
            "invalid": {"_justified": False},
            None: {},
        }
        return queryset.distinct().filter(**filters[self.value()])


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
        "justified",
        "justified_amount",
    )
    ordering = ("-year", "-number")
    search_fields = ["counterparty_IBAN", "counterparty_name", "communication"]
    date_hierarchy = "date"
    list_filter = ("year", "account__name", JustifiedFilter)

    inlines = [JustificationInline]

    actions = [
        "link_selected_operations_to_bill",
        "link_selected_operations_to_signup",
        "action_bank_fee",
        "cancel_each_other_out",
        "link_expense",
    ]

    @admin.action(description="Link selected operations to bill")
    def link_selected_operations_to_bill(self, request, queryset):
        selected = queryset.values_list("pk", flat=True)
        return HttpResponseRedirect(
            reverse("admin:accounts_operation_link_to_bill")
            + "?operations=%s" % (",".join(str(pk) for pk in selected),)
        )

    @admin.action(description="Link selected operation to expense note")
    def link_expense(self, request, queryset):
        selected = queryset.values_list("pk", flat=True)
        if len(selected) != 1:
            messages.add_message(
                request, messages.ERROR, "Can only annotate one operation at a time."
            )
            return HttpResponseRedirect(reverse("admin:accounts_operation_changelist"))

        return HttpResponseRedirect(
            reverse("admin:accounts_operation_link_to_expense")
            + "?operation=%s" % selected[0]
        )

    @admin.action(description="Annule l'un l'autre")
    def cancel_each_other_out(self, request, queryset):
        try:
            first, second = queryset.all()
        except ValueError:
            messages.add_message(
                request, messages.ERROR, "Select exactly two operations"
            )
            return HttpResponseRedirect(reverse("admin:accounts_operation_changelist"))

        if first.amount != -second.amount:
            messages.add_message(
                request,
                messages.ERROR,
                "Select only operations that cancel each other.",
            )
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

    @admin.action(description="Link selected operations to signup")
    def link_selected_operations_to_signup(self, request, queryset):
        selected = queryset.values_list("pk", flat=True)
        return HttpResponseRedirect(
            reverse("admin:accounts_operation_link_to_signup")
            + "?operations=%s" % (",".join(str(pk) for pk in selected),)
        )

    @admin.action(description="Mark as bank fees")
    def action_bank_fee(self, request, queryset):
        for operation in queryset:
            OperationValidation.objects.create(
                operation=operation,
                created_by=request.user,
                amount=operation.amount,
                validation_type=ExpenditureChoices.BANK_FEES
                if operation.amount < 0
                else IncomeChoices.INTERESTS,
            )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(year__gte="2023")
        return qs.alias(
            _justified_amount=Round(Sum("operationvalidation__amount") - F("amount"), 2)
        ).annotate(
            _justified_amount=F("_justified_amount"),
            _justified=ExpressionWrapper(
                Q(_justified_amount__exact=0), output_field=BooleanField()
            ),
        )

    def justified_amount(self, inst):
        return inst._justified_amount

    def justified(self, inst):
        return inst._justified

    justified.boolean = True
    justified.admin_order_field = "_justified"

    def has_change_permission(self, request, obj=None, **kwargs):
        if obj is None:
            return super().has_change_permission(request, **kwargs)
        else:
            return False

    def get_import_formats(self):
        return [BPostCSV, FortisCSV]

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "link_to_bill/",
                self.admin_site.admin_view(LinkToBillView.as_view()),
                name="%s_%s_link_to_bill" % self.get_model_info(),
            ),
            path(
                "link_to_signup/",
                self.admin_site.admin_view(LinkToSignupView.as_view()),
                name="%s_%s_link_to_signup" % self.get_model_info(),
            ),
            path(
                "link_to_expense/",
                self.admin_site.admin_view(LinkToExpenseReportView.as_view()),
                name="%s_%s_link_to_expense" % self.get_model_info(),
            ),
        ]
        return my_urls + urls

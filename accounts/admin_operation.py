import re

from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.db import transaction
from django.db.models import BooleanField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Round
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from import_export.admin import ImportMixin

from accounts.admin_custom_views import (
    LinkToBillView,
    LinkToExpenseReportView,
    LinkToSignupView,
)
from accounts.admin_inline import JustificationInline
from accounts.format import BPostCSV, FortisCSV
from accounts.models import (
    Bill,
    ExpenditureChoices,
    ExpenseReport,
    IncomeChoices,
    Operation,
    OperationValidation,
)
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
    inlines = [JustificationInline]
    resource_class = OperationResource

    list_display = (
        "number",
        "date",
        "description",
        "amount",
        "counterparty_IBAN",
        "counterparty_name",
        "communication_",
        "reference",
        "justified",
        "justified_amount",
    )
    ordering = ("-year", "-number")
    search_fields = ["counterparty_IBAN", "counterparty_name", "communication"]
    fields = (
        "amount",
        "currency",
        "justified",
        "account",
        "date",
        "description",
        "effective_date",
        "counterparty_IBAN",
        "counterparty_name",
        "communication_",
        "reference",
    )
    readonly_fields = (
        "account",
        "date",
        "description",
        "amount",
        "currency",
        "effective_date",
        "counterparty_IBAN",
        "counterparty_name",
        "communication_",
        "reference",
        "justified",
    )

    date_hierarchy = "date"
    list_filter = ("year", "account__name", JustifiedFilter)

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
            path(
                "<int:operation_id>/link-to-signup/<int:signup_id>/",
                self.admin_site.admin_view(self.link_to_signup_view),
                name="accounts_operation_link_to_signup",
            ),
            path(
                "<int:operation_id>/link-to-reunion/<int:reunion_id>/",
                self.admin_site.admin_view(self.link_to_reunion_view),
                name="accounts_operation_link_to_reunion",
            ),
            path(
                "<int:operation_id>/link-to-expensereport/<int:expense_report_id>/",
                self.admin_site.admin_view(self.link_to_expensereport_view),
                name="accounts_operation_link_to_expense_report",
            ),
        ]
        return my_urls + urls

    def communication_(self, obj):
        if obj.operationvalidation_set.exists():
            return obj.communication
        if match := re.search(r"reunion[-_ ]*(\d+)", obj.communication, re.IGNORECASE):
            print(match)
            from reunion.models import Signup as ReunionSignup

            reunion_id = ReunionSignup.objects.get(id=match.group(1)).id
            url = reverse(
                "admin:accounts_operation_link_to_reunion", args=[obj.id, reunion_id]
            )
            return format_html(
                '<p>{}</p><a class="button" href="{}">Link to reunion #{}</a>',
                obj.communication,
                url,
                reunion_id,
            )

        match = re.search(r"(\d\d\d\d-\d\d\d\d)", obj.communication, re.IGNORECASE)
        if match:
            expense_report_title = match.group(0)
            try:
                expense_report_id = ExpenseReport.objects.get(
                    title=expense_report_title
                ).id
                url = reverse(
                    "admin:accounts_operation_link_to_expense_report",
                    args=[obj.id, expense_report_id],
                )
                return format_html(
                    '<p>{}</p><a class="button" href="{}">Link to NF {}</a>',
                    obj.communication,
                    url,
                    expense_report_title,
                )
            except Bill.DoesNotExist:
                print("erreur")
                pass

        # Vérifier si la communication contient le motif "inscription +(\d+-"
        match = re.search(r"(inscription +)?(\d+)", obj.communication, re.IGNORECASE)
        if match:
            # Extraire l'ID depuis le motif
            signup_id = match.group(2)
            # Créer un lien ou bouton HTML pour l'action
            url = reverse(
                "admin:accounts_operation_link_to_signup", args=[obj.id, signup_id]
            )
            return format_html(
                '<p>{}</p><a class="button" href="{}">Link to #{}</a>',
                obj.communication,
                url,
                signup_id,
            )

        return obj.communication

    communication_.name = "communication"
    communication_.short_description = "communication"

    def link_to_signup_view(self, request, operation_id, signup_id):
        from signup2023.models import Signup

        # Récupérer l'opération
        operation = get_object_or_404(Operation, id=operation_id)
        # Récupérer l'entité Signup
        signup = get_object_or_404(Signup, id=signup_id)
        if signup.validated_at is None:
            messages.error(request, f"Signup {signup_id} is not validated")
            raise Http404("Signup is not validated")
        if signup.on_hold:
            messages.error(request, f"Signup {signup_id} is on hold.")
            raise Http404("Signup is on hold.")
        # Ajouter la logique pour lier les deux entités (exemple)
        OperationValidation.objects.create(
            operation=operation,
            amount=operation.amount,
            event=signup.bill,
            validation_type=IncomeChoices.SIGNUP,
        )
        # Ajout d'un message de succès
        messages.success(
            request,
            f"L’opération {operation_id} a été liée à l’inscription {signup_id}.",
        )
        return redirect("admin:accounts_operation_changelist")

    def link_to_reunion_view(self, request, operation_id, reunion_id):
        from reunion.models import Signup as ReunionSignup

        # Récupérer l'opération
        operation = get_object_or_404(Operation, id=operation_id)
        # Récupérer l'entité Signup
        reunion_signup = get_object_or_404(ReunionSignup, id=reunion_id)
        if reunion_signup.validated_at is None:
            messages.error(request, f"Reunion signup {reunion_id} is not validated")
            raise Http404("Signup is not validated")
        if reunion_signup.on_hold_at is not None:
            messages.error(request, f"Reunion signup {reunion_id} is on hold.")
            raise Http404("Signup is on hold.")

        amount = operation.amount

        for participant in reunion_signup.participants_set.all():
            if participant.amount_due <= amount:
                OperationValidation.objects.create(
                    operation=operation,
                    amount=participant.amount_due,
                    event=participant,
                    validation_type=IncomeChoices.SIGNUP,
                )
                participant.is_payed = True
                participant.amount_payed = participant.amount_due
                amount -= participant.amount_due
                participant.save()
            else:
                OperationValidation.objects.create(
                    operation=operation,
                    amount=amount,
                    event=participant,
                    validation_type=IncomeChoices.SIGNUP,
                )
                participant.amount_payed = amount
                amount = 0
                messages.error(
                    request,
                    f"Signup to reunion {reunion_id} not entirely payed!.",
                )
                break

        messages.success(
            request,
            f"Signup to reunion {reunion_id} correctly linked to operation {operation_id}.",
        )
        return redirect("admin:accounts_operation_changelist")

    def link_to_expensereport_view(self, request, operation_id, expense_report_id):
        # Récupérer l'opération
        operation = get_object_or_404(Operation, id=operation_id)
        # Récupérer l'entité Signup
        expense_report = get_object_or_404(ExpenseReport, id=expense_report_id)

        if expense_report.validated is False:
            messages.error(
                request, f"ExpenseReport {expense_report.title} is not validated"
            )
            raise Http404("ExpenseReport is not validated")

        expenses = expense_report.expenses.filter(operation_id=None)
        total = round(sum(ex.amount for ex in expenses), 2)
        if total != operation.amount:
            messages.error(
                request, f"ExpenseReport {expense_report.title} total does not match"
            )
            raise Http404("ExpenseReport total does not match.")

        with transaction.atomic():
            for operation_validation in expenses:
                operation_validation.operation = operation
                operation_validation.save()

        # Ajout d'un message de succès
        messages.success(
            request,
            f"L’opération {operation_id} a été liée à la note de frais {expense_report.title}.",
        )
        return redirect("admin:accounts_operation_changelist")

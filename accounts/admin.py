from datetime import datetime

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db.models import BooleanField, ExpressionWrapper, F, Q, Sum
from django.urls import reverse
from django.utils.html import format_html

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
        "event_link",
    )

    list_filter = (("operation", admin.EmptyFieldListFilter), "validation_type")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ["operation", "amount", "event_link"]
        else:
            return super().get_readonly_fields(request, obj)

    def event_link(self, obj):
        event = getattr(obj, "event", None)
        if not event:
            return "-"
        url = reverse(
            f"admin:{event._meta.app_label}_{event._meta.model_name}_change",
            args=[event.pk],
        )
        return format_html('<a href="{}">{}</a>', url, str(event))

    event_link.short_description = "Payment purpose"


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
        "validated",
    )
    list_filter = ("submitted_date", "signed", "validated")
    readonly_fields = ("total",)
    autocomplete_fields = ["beneficiary"]
    fields = (
        "total",
        "iban",
        "comments",
    )
    inlines = [PaymentInline, ExpenseFileInline]

    actions = ["merge"]

    @admin.action(description="Merge expense reports")
    def merge(self, request, queryset):
        if queryset.count() < 2:
            self.message_user(request, "Please select at least two expense reports.")
            return

        else:
            expense_reports = queryset.order_by("submitted_date", "id")
            first_expense_report = expense_reports[0]
            for expense_report in expense_reports[1:]:
                expense_report.expenses.update(object_id=first_expense_report.id)
                expense_report.expensefile_set.all().update(
                    expense_report_id=first_expense_report.id
                )
                first_expense_report.comments += f"\n{expense_report.comments}"
                expense_report.delete()
            first_expense_report.save()

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

    def response_add(self, request, obj, post_url_continue=None):
        self._email_treasurers(request, obj)
        return super().response_add(request, obj, post_url_continue)

    def _email_treasurers(self, request, obj: ExpenseReport):
        group = Group.objects.filter(name="Trésorier").first()
        if not group:
            self.message_user(
                request,
                "No 'Trésorier' group found. No email sent.",
                level=messages.WARNING,
            )
            return

        emails = (
            group.user_set.filter(is_active=True)
            .exclude(email__isnull=True)
            .exclude(email__exact="")
            .values_list("email", flat=True)
        )
        recipient_list = sorted(set(emails))
        if not recipient_list:
            self.message_user(
                request,
                "No active recipients in 'Trésorier' group. No email sent.",
                level=messages.WARNING,
            )
            return

        subject = f"New expense report: {obj}"

        beneficiary = obj.beneficiary
        if beneficiary and hasattr(beneficiary, "get_full_name"):
            who = (
                beneficiary.get_full_name()
                or getattr(beneficiary, "email", "")
                or "unknown user"
            )
        else:
            who = (
                getattr(beneficiary, "email", "")
                or getattr(beneficiary, "username", "unknown user")
                if beneficiary
                else "unknown user"
            )

        try:
            change_url = reverse("admin:accounts_expensereport_change", args=[obj.pk])
            link = request.build_absolute_uri(change_url)
        except Exception:
            link = None

        lines = [
            "Hello,",
            "",
            "A new expense report has been added.",
            f"Title: {obj.title}",
            f"ID: {obj.pk}",
            f"Beneficiary: {who}",
            f"Total: {obj.total}",
        ]
        if link:
            lines.append(f"Admin link: {link}")

        message = "\n".join(lines)
        from_email = settings.DEFAULT_FROM_EMAIL

        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=True)
        except Exception:
            # Only notify user if there is an issue.
            self.message_user(
                request,
                "Failed to send email to the 'Trésorier' group.",
                level=messages.WARNING,
            )

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
        if (
            request.user.groups.filter(name="Trésorier").exists()
            or request.user.is_superuser
        ):
            return qs

        return qs.filter(Q(beneficiary=request.user))

    def has_change_permission(self, request, obj=None):
        if obj:
            if obj.validated and not request.user.is_superuser:
                return False
            if obj.beneficiary == request.user or request.user.is_superuser:
                return True
        return False

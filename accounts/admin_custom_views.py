from django import views
from django.urls import reverse_lazy

from accounts.forms import LinkToBillForm, LinkToSignupForm, LinkToExpenseReportForm
from accounts.models import Operation, Bill, ExpenseReport
from signup2022.admin_views import AdminRequiredMixin


class LinkPaymentGenericView(AdminRequiredMixin, views.generic.FormView):
    success_url = reverse_lazy("admin:accounts_operation_changelist")
    model_class = None
    def get_context_data(self, **kwargs):
        return super().get_context_data(**{
            "title": f"Link a {self.model_class._meta.verbose_name} to a transaction.",
            "opts": Operation._meta,
        })

    def get_initial(self):
        """Return the initial data to use for forms on this view."""
        if operations := self.request.GET.get("operations"):
            return {
                **self.request.GET,
                "operations": operations.split(",")
            }
        return self.request.GET

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if operations := form.initial.get('operations'):
            form.fields['operations'].queryset = form.fields['operations'].queryset.filter(id__in=operations)
        return form


    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class LinkToBillView(LinkPaymentGenericView):
    template_name = "admin/operations/link_to_bill.html"
    form_class = LinkToBillForm
    model_class = Bill


class LinkToSignupView(LinkPaymentGenericView):
    template_name = "admin/operations/link_to_bill.html"
    form_class = LinkToSignupForm
    model_class = Bill


class LinkToExpenseReportView(LinkPaymentGenericView):
    template_name = "admin/operations/link_to_bill.html"
    form_class = LinkToExpenseReportForm
    model_class = ExpenseReport

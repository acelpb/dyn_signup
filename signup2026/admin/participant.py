from django.conf import settings
from django.contrib import admin
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from import_export import resources
from import_export.admin import ExportMixin

from ..admin_views import SyncMailingListFormView
from ..models import Participant, Signup
from .filters import (
    DAY_FIELDS,
    SignupDayFilter,
    SignupStatusFilter,
)


class ParticipantResource(resources.ModelResource):
    class Meta:
        model = Participant


@admin.register(Participant)
class ParticipantAdmin(ExportMixin, admin.ModelAdmin):
    """Data check and export; payment follow-up lives in PaymentParticipantAdmin."""

    resource_class = ParticipantResource
    import_export_change_list_template = "admin/signups/participant_changelist.html"

    ordering = ("last_name", "first_name")
    list_display = (
        "id",
        "signup_link",
        "first_name",
        "last_name",
        "birthday",
        "age",
        *DAY_FIELDS,
        "vae",
        "arrive_day_before",
        "takes_car_back",
        "country",
    )
    search_fields = ["first_name", "last_name"]
    list_filter = (
        SignupStatusFilter,
        SignupDayFilter,
        "vae",
        "country",
        "takes_car_back",
    )
    fields = []

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "mailinglist/",
                self.admin_site.admin_view(SyncMailingListFormView.as_view()),
                name="%s_%s_mailinglist" % self.get_model_info(),
            ),
        ]
        return my_urls + urls

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(signup_group__year=settings.DYNAMOBILE_LAST_DAY.year)
        )

    def age(self, obj: Participant):
        return obj.age_at_dynamobile_end()

    def signup_link(self, obj: Participant):
        signup: Signup = obj.signup_group
        link = "<a href={}>{}</a>".format(
            reverse(
                "admin:{}_{}_change".format(
                    signup._meta.app_label, signup._meta.model_name
                ),
                args=(signup.id,),
            ),
            str(signup),
        )
        return mark_safe(link)

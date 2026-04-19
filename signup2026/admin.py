from django.conf import settings
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.contenttypes.admin import GenericStackedInline
from django.core.mail import send_mail
from django.template.loader import get_template
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import localdate
from django_object_actions import DjangoObjectActions
from import_export import resources
from import_export.admin import ExportMixin
from import_export.resources import ModelResource

from accounts.models import OperationValidation

from .admin_views import SyncMailingListFormView
from .models import ExtraParticipantInfo, Participant, Signup


@admin.action(description="Send place on waiting list")
def waiting_list(modeladmin, request, queryset):
    for el in queryset:
        if el.signup_group.on_hold:
            send_mail(
                subject="Dynamobile place sur la liste d'attente",
                message=get_template("signup/email/waiting_list.txt").render(),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[
                    el.signup_group.owner.email,
                    settings.EMAIL_HOST_USER,
                ],
                html_message=get_template("signup/email/waiting_list.html").render(
                    {"signup": el.signup_group}
                ),
            )


class ParticipantInfoInline(admin.StackedInline):
    verbose_name = "Information Participants"
    model = Participant
    extra = 0
    fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "birthday",
        "city",
        "country",
        "vae",
        "arrive_day_before",
    )


class ParticipantDaysInline(admin.TabularInline):
    verbose_name = "Présences Participants"
    model = Participant
    extra = 0
    fields = (
        "day1",
        "day2",
        "day3",
        "day4",
        "day5",
        "day6",
        "day7",
        "day8",
        "day9",
    )


@admin.register(Signup)
class SignupAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "participants",
        "validated_at",
        "cancelled_at",
        "on_hold",
        "on_hold_vae",
        "on_hold_partial",
    )
    fields = (
        "owner",
        "validated_at",
        "cancelled_at",
        "on_hold",
        "on_hold_vae",
        "on_hold_partial",
    )
    list_filter = ("on_hold", "year")
    inlines = [ParticipantInfoInline, ParticipantDaysInline]

    change_actions = ("validate",)

    def validate(self, request, obj):
        obj.validated_at = localdate()
        obj.calculate_amounts()
        self.message_user(request, "Amounts calculated and signup validated.")

    def get_queryset(self, request):
        return super().get_queryset(request).with_amounts()

    def participants(self, obj: Signup):
        return obj.participants_set.count()


class SignupStatusFilter(SimpleListFilter):
    title = "Statut de l'inscription"
    parameter_name = "statut"

    def lookups(self, request, model_admin):
        return [
            ("started", "Inscription en cours"),
            ("on_hold", "Liste d'attente"),
            ("on_hold_vae", "Liste d'attente VAE"),
            ("partial", "Liste d'attente partielle"),
            ("validated", "Confirmé"),
            ("cancelled", "Annulé"),
        ]

    def queryset(self, request, queryset):
        filters = {
            "started": {
                "signup_group__validated_at__isnull": True,
                "signup_group__cancelled_at__isnull": True,
            },
            "on_hold": {
                "signup_group__on_hold": True,
                "signup_group__validated_at__isnull": False,
                "signup_group__cancelled_at__isnull": True,
            },
            "on_hold_vae": {
                "signup_group__on_hold_vae": True,
                "signup_group__validated_at__isnull": False,
                "signup_group__cancelled_at__isnull": True,
            },
            "partial": {
                "signup_group__on_hold_partial": True,
                "signup_group__validated_at__isnull": False,
                "signup_group__cancelled_at__isnull": True,
            },
            "validated": {
                "signup_group__validated_at__isnull": False,
                "signup_group__on_hold": False,
                "signup_group__cancelled_at__isnull": True,
            },
            "cancelled": {"signup_group__cancelled_at__isnull": False},
            None: {},
        }
        return queryset.distinct().filter(**filters[self.value()])


class SignupDayFilter(SimpleListFilter):
    title = "Participant au jour"
    parameter_name = "date"

    def lookups(self, request, model_admin):
        return [
            ("day1", "17 Juillet"),
            ("day2", "18 Juillet"),
            ("day3", "19 Juillet"),
            ("day4", "20 Juillet"),
            ("day5", "21 Juillet"),
            ("day6", "22 Juillet"),
            ("day7", "23 Juillet"),
            ("day8", "24 Juillet"),
            ("day9", "25 Juillet"),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.distinct().filter(**{self.value(): True})


class ParticipantResource(resources.ModelResource):
    class Meta:
        model = Participant


@admin.register(Participant)
class ParticipantAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ParticipantResource
    import_export_change_list_template = "admin/signups/participant_changelist.html"

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

    ordering = ("last_name", "first_name")

    list_display = (
        "id",
        "signup_link",
        "first_name",
        "last_name",
        "birthday",
        "age",
        "day1",
        "day2",
        "day3",
        "day4",
        "day5",
        "day6",
        "day7",
        "day8",
        "day9",
        "vae",
        "arrive_day_before",
        "country",
    )
    search_fields = ["first_name", "last_name"]
    list_filter = (
        SignupStatusFilter,
        SignupDayFilter,
        "vae",
        "country",
    )
    fields = []

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

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(signup_group__year=settings.DYNAMOBILE_LAST_DAY.year)
        )


class PaymentInline(GenericStackedInline):
    model = OperationValidation
    extra = 0
    ct_field_name = "content_type"
    id_field_name = "object_id"

    def get_formset(self, request, obj=None, **kwargs):
        self.fields = ("operation", "amount")
        return super().get_formset(request, obj, **kwargs)

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ExtraInfoRessource(ModelResource):
    class Meta:
        model = ExtraParticipantInfo
        fields = (
            "id",
            "participant__signup_group_id",
            "participant__last_name",
            "participant__first_name",
            "participant",
            "full_address",
            "emergency_contact",
            "share_contact_info",
            "image_rights",
            "road_captain",
            "mechanicien",
            "healthpro",
            "animator",
            "comments",
        )


@admin.register(ExtraParticipantInfo)
class ExtraParticipantInfoAdmin(ExportMixin, admin.ModelAdmin):
    resource_classes = [ExtraInfoRessource]

    list_display = (
        "id",
        "participant__signup_group",
        "participant__last_name",
        "participant__first_name",
        "participant",
        "full_address",
        "emergency_contact",
        "share_contact_info",
        "image_rights",
        "road_captain",
        "mechanicien",
        "healthpro",
        "animator",
        "comments",
    )

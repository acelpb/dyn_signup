from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.core.exceptions import PermissionDenied
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from import_export import resources
from import_export.admin import ExportMixin

from .admin_views import SyncMailingListFormView
from .models import Participant, Signup, Bill


# Register your models here.

class ParticipantInfoInline(admin.StackedInline):
    verbose_name = "Information Participants"
    model = Participant
    extra = 0
    fields = (
        "first_name", "last_name", "email", "birthday", "city", "country", "vae"
    )


class ParticipantDaysInline(admin.TabularInline):
    verbose_name = "Présences Participants"
    model = Participant
    extra = 0
    fields = (
        "d2022_07_18",
        "d2022_07_19",
        "d2022_07_20",
        "d2022_07_21",
        "d2022_07_22",
        "d2022_07_23",
        "d2022_07_24",
        "d2022_07_25",
    )


@admin.register(Signup)
class SignupAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'validated_at', 'on_hold', 'on_hold_vae', 'on_hold_partial', "still_to_be_payed")
    fields = ('owner', 'validated_at', 'on_hold', 'on_hold_vae', 'on_hold_partial', 'still_to_be_payed')
    readonly_fields = ('still_to_be_payed',)
    inlines = [ParticipantInfoInline, ParticipantDaysInline]

    def still_to_be_payed(self, obj: Signup):
        if obj.bill:
            link = "<a href={}>{}</a>".format(
                reverse(
                    'admin:{}_{}_change'.format(Bill._meta.app_label, Bill._meta.model_name),
                    args=(obj.bill.id,)),
                str(obj.bill.ballance)
            )
            return mark_safe(link)



class SignupStatusFilter(SimpleListFilter):
    title = "Statut de l'inscription"
    parameter_name = "statut"  # you can put anything here

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ("on_hold", "On Hold"),
            ("on_hold_vae", "On Hold VAE"),
            ("partial", "On Hold Partial"),
            ("validated", "Confirmé"),
            ("payed", "Payé"),
            ('cancelled', "Annulé")
        ]

    def queryset(self, request, queryset):
        filters = {
            "on_hold": {'signup_group__on_hold': True},
            "on_hold_vae": {'signup_group__on_hold_vae': True},
            "partial": {'signup_group__on_hold_partial': True},
            "validated": {
                'signup_group__validated_at__isnull': False,
                'signup_group__on_hold': False,
                'signup_group__cancelled_at__isnull': True,
            },
            "payed": {'signup_group__bill__ballance__lte': 0},
            "cancelled": {'signup_group__cancelled_at__isnull': False},
            None: {},
        }
        return queryset.distinct().filter(**filters[self.value()])


class SignupDayFilter(SimpleListFilter):
    title = "Participant au jour"
    parameter_name = "date"

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ("d2022_07_18", "18 Juillet"),
            ("d2022_07_19", "19 Juillet"),
            ("d2022_07_20", "20 Juillet"),
            ("d2022_07_21", "21 Juillet"),
            ("d2022_07_22", "22 Juillet"),
            ("d2022_07_23", "23 Juillet"),
            ("d2022_07_24", "24 Juillet"),
            ("d2022_07_25", "25 Juillet"),
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
    change_list_template = 'admin/signups/participant_changelist.html'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('mailinglist/',
                 self.admin_site.admin_view(SyncMailingListFormView.as_view()),
                 name='%s_%s_mailinglist' % self.get_model_info()),
        ]
        return my_urls + urls

    ordering = ("last_name", "first_name")

    list_display = (
        'id',
        "signup_link",
        'first_name',
        'last_name',
        'birthday',
        'd2022_07_18',
        'd2022_07_19',
        'd2022_07_20',
        'd2022_07_21',
        'd2022_07_22',
        'd2022_07_23',
        'd2022_07_24',
        'd2022_07_25',
        "vae",
        'country',
    )
    search_fields = ["first_name", "last_name"]
    list_filter = (
        SignupStatusFilter,
        SignupDayFilter,
        "vae",
        "country",
    )
    fields = []

    def signup_link(self, obj: Participant):
        signup: Signup = obj.signup_group
        link = "<a href={}>{}</a>".format(
            reverse(
                'admin:{}_{}_change'.format(signup._meta.app_label, signup._meta.model_name),
                args=(signup.id,)),
            str(signup)
        )
        return mark_safe(link)




@admin.register(Bill)
class SignupAdmin(admin.ModelAdmin):
    list_display = ('id', "signup_link", 'amount', 'ballance', 'payed_at', 'created_at',)
    fields = ('signup', 'amount', 'ballance', 'payed_at', 'created_at',)
    readonly_fields = ('signup', 'created_at',)
    list_filter = (
        ("payed_at", admin.EmptyFieldListFilter),
    )

    def signup_link(self, obj: Bill):
        signup: Signup = obj.signup
        link = "<a href={}>{}</a>".format(
            reverse(
                'admin:{}_{}_change'.format(signup._meta.app_label, signup._meta.model_name),
                args=(obj.signup_id,)),
            str(signup)
        )
        return mark_safe(link)


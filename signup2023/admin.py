from django.conf import settings
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.contenttypes.admin import GenericStackedInline
from django.core.mail import send_mail
from django.db.models import F, Q, Sum
from django.template.loader import get_template
from django.urls import path, reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.timezone import localdate
from django_object_actions import DjangoObjectActions
from import_export import resources
from import_export.admin import ExportMixin
from import_export.resources import ModelResource

from accounts.models import OperationValidation

from .admin_views import SyncMailingListFormView
from .models import Bill, ExtraParticipantInfo, Participant, Signup


# Register your models here.
@admin.action(description="Send payment confirmation")
def confirmation(modeladmin, request, queryset):
    for signup in queryset:
        if (
            signup.validated_at is not None
            and signup.bill.payed_at is None
            and signup.cancelled_at is None
            and signup.on_hold is False
        ):
            signup.bill.send_payment_confirmation_mail()


@admin.action(description="Send place on waiting list")
def waiting_list(modeladmin, request, queryset):
    for el in queryset:
        if el.signup.on_hold:
            send_mail(
                subject="Dynamobile place sur la liste d'attente",
                message=get_template("signup/email/waiting_list.txt").render(),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[el.signup.owner.email, settings.EMAIL_HOST_USER],
                html_message=get_template("signup/email/waiting_list.html").render(
                    {"signup": el.signup}
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
        "birthday",
        "city",
        "country",
        "vae",
        "extra_activities",
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
        "still_to_be_payed",
    )
    fields = (
        "owner",
        "validated_at",
        "cancelled_at",
        "on_hold",
        "on_hold_vae",
        "on_hold_partial",
        "amount",
        "still_to_be_payed",
    )
    readonly_fields = (
        "amount",
        "still_to_be_payed",
    )
    list_filter = ("on_hold", "year")
    inlines = [ParticipantInfoInline, ParticipantDaysInline]

    change_actions = ("validate",)

    def validate(self, request, obj):
        obj.validated_at = localdate()
        obj.create_bill()
        self.message_user(request, "Bill created and confirmation sent.")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(payed=Sum("bill__payments__amount"))
            .annotate(ballance=F("bill__amount") - F("payed"))
        )

    def amount(self, obj: Signup):
        if obj.bill:
            return obj.bill.amount

    def participants(self, obj: Signup):
        return obj.participant_set.count()

    def still_to_be_payed(self, obj: Signup):
        if obj.bill:
            link = "<a href={}>{}</a>".format(
                reverse(
                    "admin:{}_{}_change".format(
                        Bill._meta.app_label, Bill._meta.model_name
                    ),
                    args=(obj.bill.id,),
                ),
                f"{obj.ballance:.2f} €" if obj.ballance else "0€",
            )
            return mark_safe(link)

    still_to_be_payed.admin_order_field = "ballance"


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
            ("needs_to_pay", "Impayé"),
            ("cancelled", "Annulé"),
        ]

    def queryset(self, request, queryset):
        filters = {
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
            "needs_to_pay": {
                "signup_group__validated_at__isnull": False,
                "signup_group__on_hold": False,
                "signup_group__cancelled_at__isnull": True,
                "signup_group__bill__payed_at__isnull": True,
            },
            "payed": {
                "signup_group__bill__payed_at__isnull": False,
                "signup_group__validated_at__isnull": False,
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
        # This is where you create filter options; we have two:
        return [
            ("day1", "18 Juillet"),
            ("day2", "19 Juillet"),
            ("day3", "20 Juillet"),
            ("day4", "21 Juillet"),
            ("day5", "22 Juillet"),
            ("day6", "23 Juillet"),
            ("day7", "24 Juillet"),
            ("day8", "25 Juillet"),
            ("day9", "26 Juillet"),
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
        return obj.age

    age.admin_order_field = "age"

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


class PriceIsOddFilter(SimpleListFilter):
    title = "Prix calculé"
    parameter_name = "price_diff"

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ("different", "Prix calculé et montant divergent."),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.annotate(diff=F("amount") - F("calculated_amount")).filter(
                ~Q(diff=0)
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


@admin.register(Bill)
class BillAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_display = (
        "id",
        "signup",
        "amount",
        "calculated_amount",
        "ballance",
        "created_at",
        "cancelled_at",
        "payed_at",
    )
    fields = (
        "signup",
        "amount",
        "calculated_amount",
        "ballance",
        "payed_at",
        "created_at",
        "calculation",
    )
    readonly_fields = (
        "signup",
        "ballance",
        "calculated_amount",
        "created_at",
        "payed_at",
        "amount_payed_at",
    )
    list_filter = (
        ("payed_at", admin.EmptyFieldListFilter),
        ("signup__cancelled_at", admin.EmptyFieldListFilter),
        ("signup__on_hold", admin.BooleanFieldListFilter),
        PriceIsOddFilter,
    )
    inlines = [PaymentInline]

    actions = ["send_reminder"]

    change_actions = (
        "recalculate",
        "send_payment_confirmation",
        "unblock_waiting_list",
    )

    @admin.action(description="Send payment reminder")
    def send_reminder(modeladmin, request, queryset):
        for bill in queryset:
            signup = bill.signup
            if (
                signup.cancelled_at is not None
                or signup.validated_at is None
                or signup.on_hold
            ):
                continue
            if bill.payed_at is not None or bill.calculated_amount == 0:
                continue
            send_mail(
                subject="Dynamobile paiement inscription",
                message=get_template("signup/email/payment_reminder.txt").render(),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[signup.owner.email, settings.EMAIL_HOST_USER],
                html_message=get_template("signup/email/payment_reminder.html").render(
                    {"signup": signup}
                ),
            )

    def unblock_waiting_list(self, request, obj: Bill):
        signup = obj.signup
        if signup.cancelled_at is not None or signup.validated_at is None:
            return
        if signup.on_hold:
            signup.on_hold = False
            signup.on_hold_vae = False
            signup.on_hold_partial = False
            signup.save()

        send_mail(
            subject="Dynamobile: vous avez une place.",
            message=get_template("signup/email/unblock_waitinglist.txt").render(),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[signup.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template("signup/email/unblock_waitinglist.html").render(
                {"signup": signup}
            ),
        )

    def send_payment_confirmation(self, request, obj):
        obj.send_payment_confirmation_mail()
        obj.payed_at = timezone.now()
        obj.save()
        self.message_user(request, "Mail de confirmation envoyé.")
        pass

    def recalculate(self, request, obj: Bill):
        obj.calculate_amount_and_explain()
        obj.save()
        self.message_user(request, "ok")
        pass

    def signup_link(self, obj: Bill):
        signup: Signup = obj.signup
        link = "<a href={}>{}</a>".format(
            reverse(
                "admin:{}_{}_change".format(
                    signup._meta.app_label, signup._meta.model_name
                ),
                args=(obj.signup_id,),
            ),
            str(signup),
        )
        return mark_safe(link)

    def cancelled_at(self, obj):
        return obj.signup.cancelled_at

    def ballance(self, obj):
        if obj.ballance is not None:
            return f"{obj.ballance:.2f}"

    ballance.admin_order_field = "ballance"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(signup__year=settings.DYNAMOBILE_LAST_DAY.year)
        )


class ExtraInfoRessource(ModelResource):
    class Meta:
        model = ExtraParticipantInfo
        fields = (
            "id",
            "participant__signup_group_id",
            "participant__last_name",
            "participant__first_name",
            "roadbook",
            "participant",
            "activite_21",
            "activite_25",
            "full_address",
            "emergency_contact",
            "share_contact_info_participants",
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
        "participant__last_name",
        "participant__first_name",
        "roadbook",
        "activite_21",
        "activite_25",
    )

    list_filter = (
        ("roadbook", admin.BooleanFieldListFilter),
        ("activite_21", admin.ChoicesFieldListFilter),
        ("activite_25", admin.ChoicesFieldListFilter),
    )

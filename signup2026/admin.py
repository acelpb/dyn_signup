from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.core.mail import send_mail
from django.db.models import Q
from django.forms.models import BaseModelFormSet
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import localdate
from django_object_actions import action
from import_export import resources
from import_export.admin import ExportMixin
from import_export.resources import ModelResource

from accounts.models import OperationValidation
from reunion.admin import (
    SignupAminMixin,
)

from .admin_views import SyncMailingListFormView
from .models import ExtraParticipantInfo, Participant, Signup, WaitingListParticipant


class _PassthroughFormSet(BaseGenericInlineFormSet):
    """Uses the queryset as-is without re-filtering by content_type/object_id."""

    def __init__(
        self,
        data=None,
        files=None,
        instance=None,
        save_as_new=False,
        prefix=None,
        queryset=None,
        **kwargs,
    ):
        self.instance = instance
        self.save_as_new = save_as_new
        opts = self.model._meta
        self.rel_name = (
            f"{opts.app_label}-{opts.model_name}"
            f"-{self.ct_field.name}-{self.ct_fk_field.name}"
        )
        if queryset is None:
            queryset = self.model._default_manager.none()
        BaseModelFormSet.__init__(
            self, data, files, prefix=prefix, queryset=queryset, **kwargs
        )


@admin.action(description="Send place on waiting list")
def waiting_list(modeladmin, request, queryset):
    for el in queryset:
        if el.signup_group.on_hold_at:
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


class SignupPaymentsInline(GenericTabularInline):
    model = OperationValidation
    ct_field = "content_type"
    fk_field = "object_id"
    formset = _PassthroughFormSet
    extra = 0
    can_delete = False
    verbose_name = "Paiement"
    verbose_name_plural = "Paiements (inscription + participants)"
    readonly_fields = (
        "operation",
        "amount",
        "validation_type",
        "event_display",
        "created_on",
        "created_by",
    )
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        from django.contrib.contenttypes.models import ContentType

        signup_pk = request.resolver_match.kwargs.get("object_id")
        if not signup_pk:
            return OperationValidation.objects.none()

        signup_ct = ContentType.objects.get_for_model(Signup)
        participant_ct = ContentType.objects.get_for_model(Participant)
        participant_pks = Participant.objects.filter(
            signup_group_id=signup_pk
        ).values_list("pk", flat=True)

        return (
            OperationValidation.objects.filter(
                Q(content_type=signup_ct, object_id=signup_pk)
                | Q(content_type=participant_ct, object_id__in=participant_pks)
            )
            .select_related("operation", "content_type", "created_by")
            .order_by("created_on")
        )

    def event_display(self, obj):
        return str(obj.event) if obj.event else "-"

    event_display.short_description = "Pour"


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
        "takes_car_back",
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
class SignupAdmin(SignupAminMixin, admin.ModelAdmin):
    inlines = [ParticipantInfoInline, ParticipantDaysInline, SignupPaymentsInline]

    change_actions = (
        "validate",
        "recalculate_amounts",
        "validate_signup",
        "cancel_signup",
        "put_on_hold_signup",
        "send_payment_confirmation",
    )

    def validate(self, request, obj):
        obj.validated_at = localdate()
        obj.calculate_amounts()
        self.message_user(request, "Amounts calculated and signup validated.")

    def get_change_actions(self, request, object_id, form_url):
        actions = list(super().get_change_actions(request, object_id, form_url) or [])
        if (
            object_id is not None
            and Signup.objects.filter(pk=object_id, validated_at__isnull=False).exists()
        ):
            actions.append("send_payment_confirmation")
        return actions

    @action(description="Send payment confirmation")
    def send_payment_confirmation(self, request, signup):
        signup.send_payment_confirmation_mail()
        messages.success(request, f"Payment confirmation sent to {signup.owner.email}.")
        return redirect("admin:signup2026_signup_change", signup.id)

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
                "signup_group__on_hold_at__isnull": False,
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
                "signup_group__on_hold_at__isnull": True,
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


@admin.action(description="Débloquer le(s) participant(s)")
def unblock_participant(modeladmin, request, queryset):
    signups_done = set()
    for participant in queryset.select_related("signup_group__owner"):
        signup = participant.signup_group
        if signup.id in signups_done:
            continue
        signups_done.add(signup.id)
        signup.on_hold_at = None
        signup.on_hold_vae = False
        signup.on_hold_partial = False
        signup.save()
        signup.calculate_amounts()
        send_mail(
            subject="Votre inscription à Dynamobile",
            message=get_template("signup2026/email/unblock_waitinglist.txt").render(
                {"signup": signup}
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[signup.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template(
                "signup2026/email/unblock_waitinglist.html"
            ).render({"signup": signup}),
        )
    modeladmin.message_user(
        request, f"{len(signups_done)} inscription(s) débloquée(s)."
    )


@admin.register(WaitingListParticipant)
class WaitingListParticipantAdmin(admin.ModelAdmin):
    actions = [unblock_participant]
    list_display = (
        "waiting_number",
        "first_name",
        "last_name",
        "on_hold_reason",
        "vae",
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
    ordering = ()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(
                signup_group__on_hold_at__isnull=False,
                signup_group__validated_at__isnull=False,
                signup_group__cancelled_at__isnull=True,
                signup_group__year=2026,
            )
            .select_related("signup_group")
        )

    @admin.display(description="N° d'attente")
    def waiting_number(self, obj):
        return obj.signup_group.waiting_number()

    @admin.display(description="Raison")
    def on_hold_reason(self, obj):
        signup = obj.signup_group
        if signup.on_hold_vae:
            return "VAE"
        if signup.on_hold_partial:
            return "Inscription partielle"
        return "Limite participants"


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

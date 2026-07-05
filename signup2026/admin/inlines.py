from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.forms.models import BaseModelFormSet

from accounts.models import OperationValidation

from ..models import Participant, Signup
from .filters import DAY_FIELDS


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

    @admin.display(description="Pour")
    def event_display(self, obj):
        return str(obj.event) if obj.event else "-"


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
        "amount_due_calculated",
        "amount_due_modified",
    )
    readonly_fields = ("amount_due_calculated",)


class ParticipantDaysInline(admin.TabularInline):
    verbose_name = "Présences Participants"
    model = Participant
    extra = 0
    fields = DAY_FIELDS

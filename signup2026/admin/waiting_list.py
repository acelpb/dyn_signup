from django.conf import settings
from django.contrib import admin

from ..models import WaitingListParticipant
from .filters import DAY_FIELDS


@admin.action(description="Débloquer le(s) participant(s)")
def unblock_participant(modeladmin, request, queryset):
    signups_done = set()
    for participant in queryset.select_related("signup_group__owner"):
        signup = participant.signup_group
        if signup.id in signups_done:
            continue
        signups_done.add(signup.id)
        signup.release_from_waiting_list()
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
        *DAY_FIELDS,
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
                signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
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

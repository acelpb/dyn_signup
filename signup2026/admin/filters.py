from django.conf import settings
from django.contrib.admin import SimpleListFilter
from django.utils.formats import date_format

from ..models import ExtraParticipantInfo, Signup

# Participant model day flags (day1 .. day9), one per Dynamobile day.
DAY_FIELDS = tuple(f"day{i}" for i in range(1, len(settings.DYNAMOBILE_DAYS) + 1))


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
            ("all", "Tout - (inclus annulés/en cours)"),
        ]

    def queryset(self, request, queryset):
        if queryset.model == Signup:
            prefix = ""
        elif queryset.model == ExtraParticipantInfo:
            prefix = "participant__signup_group__"
        else:
            prefix = "signup_group__"

        filters = {
            "all": {},
            None: {
                f"{prefix}validated_at__isnull": False,
                f"{prefix}on_hold_at__isnull": True,
                f"{prefix}cancelled_at__isnull": True,
            },
            "started": {
                f"{prefix}validated_at__isnull": True,
                f"{prefix}cancelled_at__isnull": True,
            },
            "on_hold": {
                f"{prefix}on_hold_at__isnull": False,
                f"{prefix}validated_at__isnull": False,
                f"{prefix}cancelled_at__isnull": True,
            },
            "on_hold_vae": {
                f"{prefix}on_hold_vae": True,
                f"{prefix}validated_at__isnull": False,
                f"{prefix}cancelled_at__isnull": True,
            },
            "partial": {
                f"{prefix}on_hold_partial": True,
                f"{prefix}validated_at__isnull": False,
                f"{prefix}cancelled_at__isnull": True,
            },
            "validated": {
                f"{prefix}validated_at__isnull": False,
                f"{prefix}on_hold_at__isnull": True,
                f"{prefix}cancelled_at__isnull": True,
            },
            "cancelled": {f"{prefix}cancelled_at__isnull": False},
        }
        return queryset.distinct().filter(**filters[self.value()])


class SignupDayFilter(SimpleListFilter):
    title = "Participant au jour"
    parameter_name = "date"

    def lookups(self, request, model_admin):
        return [
            (field, date_format(day, "j F"))
            for field, (day, _label) in zip(
                DAY_FIELDS, settings.DYNAMOBILE_DAYS, strict=True
            )
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.distinct().filter(**{self.value(): True})


class PayedFilter(SimpleListFilter):
    """Works on any queryset annotated with balance (Signup or Participant)."""

    title = "Payé"
    parameter_name = "is_payed_filter"

    def lookups(self, request, model_admin):
        return [
            ("yes", "Payé"),
            ("no", "Non payé"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(balance__lte=0)
        if self.value() == "no":
            return queryset.filter(balance__gt=0)
        return queryset

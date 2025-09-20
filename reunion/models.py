from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import (
    BooleanField,
    Case,
    DecimalField,
    F,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


class SignupQuerySet(models.QuerySet):
    def with_amounts(self):
        return (
            self.annotate(
                # Sums from related participants
                amount_due_modified_agg=Sum("participants_set__amount_due_modified"),
                amount_due_calculated_agg=Coalesce(
                    Sum("participants_set__amount_due_calculated"),
                    Value(0),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                ),
                amount_payed_agg=Coalesce(
                    Sum("participants_set__amount_payed"),
                    Value(0),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                ),
            )
            .annotate(
                # Coalesce of modified vs calculated amount due
                amount_due_agg=Coalesce(
                    F("amount_due_modified_agg"),
                    F("amount_due_calculated_agg"),
                ),
            )
            .annotate(
                ballance_agg=F("amount_due_agg") - F("amount_payed_agg"),
                is_payed_agg=Case(
                    When(amount_payed_agg__gte=F("amount_due_agg"), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
        )


class SignupManager(models.Manager.from_queryset(SignupQuerySet)):
    def get_queryset(self):
        # Always include the amount annotations by default
        return super().get_queryset().with_amounts()


class Signup(models.Model):
    # Custom manager with annotations
    objects = SignupManager()

    # Owner of the signup
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signups",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    payment_confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Reason for cancelling the signup.",
    )

    # On-hold: store a reason or be empty
    on_hold = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Reason for putting the signup on hold.",
    )

    status = models.GeneratedField(
        expression=Case(
            When(Q(cancelled_at__isnull=False), then=Value("cancelled")),
            When(Q(on_hold__isnull=False) & ~Q(on_hold=""), then=Value("on_hold")),
            When(Q(validated_at__isnull=True), then=Value("pending")),
            When(
                Q(payment_confirmation_sent_at__isnull=True),
                then=Value("payment_pending"),
            ),
            default=Value("validated"),
        ),
        output_field=models.CharField(max_length=32),
        db_persist=False,
        help_text="Status of the signup",
    )

    def __str__(self) -> str:
        return f"Signup #{self.pk} - {self.owner}"

    # ---- Aggregated (inherited) fields from participants ----

    @property
    def amount_due_modified(self) -> Decimal | None:
        """
        Sum of participants.amount_due_modified.
        Returns None if no participant has a modified amount set.
        """
        qs = self.participants_set.filter(amount_due_modified__isnull=False)
        if not qs.exists():
            return None
        return qs.aggregate(total=Sum("amount_due_modified"))["total"]

    @property
    def amount_due_calculated(self) -> Decimal:
        """
        Sum of participants.amount_due_calculated (treat missing as 0).
        """
        total = self.participants_set.aggregate(total=Sum("amount_due_calculated"))[
            "total"
        ]
        return total or Decimal("0.00")

    @property
    def amount_payed(self) -> Decimal:
        """
        Sum of participants.amount_payed (treat missing as 0).
        """
        total = self.participants_set.aggregate(total=Sum("amount_payed"))["total"]
        return total or Decimal("0.00")

    @property
    def is_payed(self) -> bool:
        """
        True when the total amount paid covers the amount due.
        """
        return self.amount_payed >= (self.amount_due or Decimal("0.00"))

    # ---- Calculated fields ----

    @property
    def amount_due(self) -> Decimal:
        """
        Coalesce: use sum of modified amounts when at least one is provided,
        otherwise use the calculated sum.
        """
        return (
            self.amount_due_modified
            if self.amount_due_modified is not None
            else self.amount_due_calculated
        )

    @property
    def ballance(self) -> Decimal:
        """
        amount_due - amount_payed
        """
        return (self.amount_due or Decimal("0.00")) - self.amount_payed

    def check_max_participants(self):
        nb_of_participants = (
            Participant.objects.filter(
                signup_group__validated_at__isnull=False,
                signup_group__on_hold=False,
                signup_group__cancelled_at__isnull=True,
                signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
            )
            | self.participants_set.all()
        ).count()
        if nb_of_participants > 200:
            self.on_hold = "TOO_MANY_PARTICIPANTS"
        return False


class Participant(models.Model):
    signup = models.ForeignKey(
        Signup,
        on_delete=models.CASCADE,
        related_name="participants_set",
    )

    ## Fist Form
    first_name = models.CharField("Prénom", max_length=150, blank=False)
    last_name = models.CharField("Nom", max_length=150, blank=False)
    email = models.EmailField(_("e-mail"), blank=True)
    phone = PhoneNumberField(_("N° tel"), blank=True, null=True)
    birthday = models.DateField(_("date de naissance"), blank=False)
    city = models.CharField(_("Ville"), max_length=150, blank=True)
    country = models.CharField(_("Pays"), max_length=150, blank=True)

    # Extra Form
    is_helping_friday = models.BooleanField(
        _("Aide pour le vendredi après-midi"),
        default=False,
        help_text="vendredi 3 octobre après-midi (installation matériel, déchargement courses, etc.)",
    )
    is_helping_saturday_morning = models.BooleanField(
        _("Aide pour le samedi matin"),
        default=False,
        help_text="samedi 4 octobre matin (installation matériel, déco, aide pour la convergence à vélo,...)",
    )
    is_helping_saturday_evening = models.BooleanField(
        _("Aide pour le samedi après-midi"),
        default=False,
        help_text="samedi 4 octobre en fin de journée (rangement)",
    )
    comments = models.TextField(_("Commentaires"), blank=True)

    ## Internal fields used for calculating stuff
    amount_due_modified = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    amount_due_calculated = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    amount_payed = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    is_payed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}- signup {self.signup_id}"

    def refresh_payment_state(self, save: bool = True) -> None:
        """
        Recompute is_payed based on amounts.
        """
        due = (
            self.amount_due_modified
            if self.amount_due_modified is not None
            else (self.amount_due_calculated or Decimal("0.00"))
        )
        self.is_payed = (self.amount_payed or Decimal("0.00")) >= (
            due or Decimal("0.00")
        )
        if save:
            self.save(update_fields=["is_payed"])

    def save(self, *args, **kwargs):
        # Keep is_payed in sync automatically
        self.refresh_payment_state(save=False)
        super().save(*args, **kwargs)

    def age_at_reunion(self):
        last_day = date(2025, 10, 3)
        birthday = self.birthday
        return (
            last_day.year
            - birthday.year
            - ((last_day.month, last_day.day) < (birthday.month, birthday.day))
        )

    @property
    def amount_due(self) -> Decimal:
        """
        Coalesce: use sum of modified amounts when at least one is provided,
        otherwise use the calculated sum.
        """
        return (
            self.amount_due_modified
            if self.amount_due_modified is not None
            else self.amount_due_calculated
        )


# ---- Automatic timestamp updates for Signup status changes ----


@receiver(pre_save, sender=Signup)
def set_signup_status_timestamps(sender, instance: Signup, **kwargs):
    """
    Set validated_at, payed_at, cancelled_at when status changes into those states.
    Timestamps are only set once (not cleared automatically).
    """
    old_status = None
    if instance.pk:
        try:
            old_status = sender._base_manager.only("status").get(pk=instance.pk).status
        except sender.DoesNotExist:
            old_status = None

    new_status = instance.status

    if old_status != new_status:
        if (
            new_status == Signup.Status.VALIDATED_BY_PARTICIPANT
            and not instance.validated_at
        ):
            instance.validated_at = timezone.now()

        if new_status == Signup.Status.PAYED and not instance.payed_at:
            instance.payed_at = timezone.now()

        if (
            new_status
            in (
                Signup.Status.CANCELLED,
                Signup.Status.CANCELLED_WITH_PENALTY,
            )
            and not instance.cancelled_at
        ):
            instance.cancelled_at = timezone.now()


def _update_signup_payment_state(signup_id: int) -> None:
    """
    Recalculate payment state for a signup after participant changes.
    If fully paid, mark the signup as PAYED (and set payed_at if needed).
    Does not downgrade status automatically.
    """
    try:
        s: Signup = Signup._base_manager.get(pk=signup_id)
    except Signup.DoesNotExist:
        return

    totals = s.participants_set.aggregate(
        modified_sum=Sum("amount_due_modified"),
        calculated_sum=Coalesce(
            Sum("amount_due_calculated"),
            Value(0),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        payed_sum=Coalesce(
            Sum("amount_payed"),
            Value(0),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    )

    amount_due = (
        totals["modified_sum"]
        if totals["modified_sum"] is not None
        else totals["calculated_sum"]
    ) or Decimal("0.00")

    fully_payed = totals["payed_sum"] >= amount_due

    if fully_payed and s.status != Signup.Status.PAYED:
        s.status = Signup.Status.PAYED
        if not s.payed_at:
            s.payed_at = timezone.now()
        s.save(update_fields=["status", "payed_at"])


@receiver(post_save, sender=Participant)
def participant_saved(sender, instance: Participant, **kwargs):
    _update_signup_payment_state(instance.signup_id)


@receiver(post_delete, sender=Participant)
def participant_deleted(sender, instance: Participant, **kwargs):
    _update_signup_payment_state(instance.signup_id)


# Reusable queryset for participant subsets
class ParticipantQuerySet(models.QuerySet):
    def validated(self):
        return self.filter(
            cancelled_at__isnull=True,
            signup__cancelled_at__isnull=True,
            signup__validated_at__isnull=False,
        )

    def unconfirmed(self):
        return self.filter(
            cancelled_at__isnull=True,
            signup__cancelled_at__isnull=True,
            signup__validated_at__isnull=True,
        )

    def cancelled(self):
        return self.filter(
            Q(cancelled_at__isnull=False) | Q(signup__cancelled_at__isnull=False)
        )


# Base manager to get the ParticipantQuerySet everywhere it's needed
class ParticipantManager(models.Manager.from_queryset(ParticipantQuerySet)):
    pass


# If you want the base Participant to also expose .validated(), .unconfirmed(), .cancelled()
# you can attach the queryset as its default manager (uncomment the next line if desired):
# Participant.add_to_class("objects", ParticipantManager())


# Managers for proxy models that auto-apply the intended filter
class ValidatedParticipantManager(ParticipantManager):
    def get_queryset(self):
        return super().get_queryset().validated()


class UnconfirmedParticipantManager(ParticipantManager):
    def get_queryset(self):
        return super().get_queryset().unconfirmed()


class CancelledParticipantManager(ParticipantManager):
    def get_queryset(self):
        return super().get_queryset().cancelled()


# Proxy models to provide dedicated admin entries and reusable filtered model classes
class ValidatedParticipant(Participant):
    objects = ValidatedParticipantManager()

    class Meta:
        proxy = True
        verbose_name = "Validated participant"
        verbose_name_plural = "Validated participants"


class UnconfirmedParticipant(Participant):
    objects = UnconfirmedParticipantManager()

    class Meta:
        proxy = True
        verbose_name = "Unconfirmed participant"
        verbose_name_plural = "Unconfirmed participants"


class CancelledParticipant(Participant):
    objects = CancelledParticipantManager()

    class Meta:
        proxy = True
        verbose_name = "Cancelled participant"
        verbose_name_plural = "Cancelled participants"

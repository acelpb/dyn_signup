from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
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
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from accounts.models import OperationValidation


class SignupQuerySet(models.QuerySet):
    def with_amounts(self):
        return (
            self.annotate(
                amount_due=Sum(
                    Coalesce(
                        "participants_set__amount_due_modified",
                        "participants_set__amount_due_calculated",
                    ),
                ),
                amount_payed=Sum("participants_set__payments__amount"),
            )
            .annotate(
                # Coalesce of modified vs calculated amount due
                amount_due=F("amount_due") - F("amount_payed"),
            )
            .annotate(
                status=Case(
                    When(cancelled_at__isnull=False, then=Value("cancelled")),
                    When(validated_at__isnull=True, then=Value("pending")),
                    When(on_hold_at__isnull=False, then=Value("on hold")),
                    When(amount_due__lte=Value(0), then=Value("payed")),
                    default=Value("waiting payment"),
                ),
                is_payed=Case(
                    When(amount_due__lte=Value(0), then=Value(True)),
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
    on_hold_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(_("Commentaires"), blank=True)

    def __str__(self) -> str:
        return f"Signup #{self.pk} - {self.owner}"

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

    def calculate_amounts(self):
        for participant in self.participants_set.all().order_by("birthday"):
            age = participant.age_at_reunion()
            if age >= 18:
                participant.amount_due_calculated = 25
            elif age >= 12:
                participant.amount_due_calculated = 15
            elif age >= 6:
                participant.amount_due_calculated = 10
            else:
                participant.amount_due_calculated = 0
            participant.save()
        return


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

    amount_due_remaining = models.GeneratedField(
        expression=Coalesce(F("amount_due_modified"), F("amount_due_calculated"))
        - F("amount_payed"),
        output_field=DecimalField(max_digits=10, decimal_places=2),
        db_persist=False,
    )
    is_payed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    payments = GenericRelation(OperationValidation)

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}- signup {self.signup_id}"

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

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import (
    BooleanField,
    Case,
    DecimalField,
    F,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from accounts.models import OperationValidation


class SignupQuerySet(models.QuerySet):
    def with_amounts(self):
        # Note: Cette méthode est inspirée de 'reunion', mais adaptée pour 'signup2026'
        # Elle suppose l'existence de relations et de champs similaires
        return (
            self.annotate(
                amount_due_total=Sum(
                    Coalesce(
                        "participants_set__amount_due_modified",
                        "participants_set__amount_due_calculated",
                        output_field=DecimalField(max_digits=10, decimal_places=2),
                    ),
                ),
                amount_payed_total=Coalesce(
                    Sum("participants_set__payments__amount"),
                    Value(0),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                ),
            )
            .annotate(
                balance=F("amount_due_total") - F("amount_payed_total"),
            )
            .annotate(
                status=Case(
                    When(cancelled_at__isnull=False, then=Value("cancelled")),
                    When(validated_at__isnull=True, then=Value("pending")),
                    When(on_hold_at__isnull=False, then=Value("on hold")),
                    When(balance__lte=Value(0), then=Value("payed")),
                    default=Value("waiting payment"),
                ),
                is_payed=Case(
                    When(balance__lte=Value(0), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
        )


class SignupManager(models.Manager.from_queryset(SignupQuerySet)):
    def get_queryset(self):
        return super().get_queryset()


class Signup(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signup2026_groups",
    )
    year = models.IntegerField(default=2026)
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(default=None, null=True, blank=True)
    cancelled_at = models.DateTimeField(default=None, null=True, blank=True)
    on_hold_at = models.DateTimeField(default=None, null=True, blank=True)
    on_hold_vae = models.BooleanField(default=False)
    on_hold_partial = models.BooleanField(default=False)
    comments = models.TextField(_("Commentaires"), blank=True)

    objects = SignupManager()

    class Meta:
        verbose_name = "Inscription 2026"
        verbose_name_plural = "Inscriptions 2026"
        unique_together = ("owner", "year")

    def __str__(self):
        return f"2026-{self.id} - {self.owner.username}"

    def create_bill(self):
        # Logique de création de facture/confirmation par mail
        # À adapter selon les besoins de 2026
        self.calculate_amounts()
        # On pourrait ajouter un modèle Bill ici ou utiliser les champs directs
        pass

    def has_vae(self):
        return self.participants_set.filter(vae=True).count()

    def complete_signup(self):
        for participant in self.participants_set.all():
            if not participant.complete_signup():
                return False
        return True

    def calculate_amounts(self):
        # Fusion de la logique de calcul de prix
        total_price = 0
        child_nb = 0
        participants = self.participants_set.all().order_by("birthday")
        for participant in participants:
            age = participant.age_at_dynamobile_end()
            price = 0
            for (
                min_age,
                max_age,
                all_days_price,
                upfront_price,
            ) in settings.DYNAMOBILE_PRICES:
                if min_age <= age < max_age:
                    if participant.complete_signup():
                        price = upfront_price + all_days_price
                    else:
                        nb_days = participant.nb_of_days()
                        price = upfront_price + (all_days_price / 8 * nb_days)

                    if age < 18:
                        reduction = 0
                        if child_nb == 1:
                            reduction = 0.25
                        elif child_nb >= 2:
                            reduction = 0.50
                        price *= 1 - reduction
                        child_nb += 1
                    break
            participant.amount_due_calculated = price
            participant.save()
            total_price += price
        return total_price

    def amount_due(self):
        return (
            self.participants_set.aggregate(
                total=Coalesce(
                    Sum(
                        Coalesce(
                            "amount_due_modified",
                            "amount_due_calculated",
                            output_field=DecimalField(max_digits=10, decimal_places=2),
                        )
                    ),
                    Value(0),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )["total"]
            or 0
        )

    def amount_payed(self):
        return (
            self.participants_set.aggregate(
                total=Coalesce(
                    Sum("payments__amount"),
                    Value(0),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )["total"]
            or 0
        )

    def balance(self):
        return self.amount_due() - self.amount_payed()

    def payed(self):
        return self.balance() <= 0

    def waiting_number(self):
        from django.db.models import Case, Value, When
        from django.db.models.expressions import Window
        from django.db.models.functions import RowNumber

        waiting_signups = Signup.objects.filter(on_hold_at__isnull=False, year=2026)
        ordered = waiting_signups.annotate(
            ranking=Case(
                When(
                    validated_at__lt=settings.DYNAMOBILE_START_PARTIAL_SIGNUP,
                    on_hold_partial=False,
                    then=Value(1),
                ),
                When(
                    validated_at__lt=settings.DYNAMOBILE_START_PARTIAL_SIGNUP,
                    on_hold_partial=True,
                    then=Value(2),
                ),
                default=Value(3),
            )
        ).annotate(
            final_ranking=Window(RowNumber(), order_by=["ranking", "validated_at"])
        )
        collect = {k: v for k, v in ordered.values_list("id", "final_ranking")}
        return collect.get(self.id, 0)

    def check_if_on_hold(self):
        # Vérification des limites (VAE, participants, partiels)
        if (
            not self.complete_signup()
            and settings.DYNAMOBILE_START_PARTIAL_SIGNUP > timezone.now()
        ):
            self.on_hold_partial = True
            self.on_hold_at = timezone.now()

        # VAE limit
        if additional_vae := self.has_vae():
            registered_vae = Participant.objects.filter(
                signup_group__validated_at__isnull=False,
                vae=True,
                signup_group__year=2026,
            ).count()
            if (
                registered_vae + additional_vae
                > settings.DYNAMOBILE_MAX_VAE_PARTICIPANTS
            ):
                self.on_hold_vae = True
                self.on_hold_at = timezone.now()

        # Total participants limit
        nb_participants = (
            Participant.objects.filter(
                signup_group__validated_at__isnull=False,
                signup_group__on_hold_at__isnull=True,
                signup_group__cancelled_at__isnull=True,
                signup_group__year=2026,
            ).count()
            + self.participants_set.count()
        )
        if nb_participants > settings.DYNAMOBILE_MAX_PARTICIPANTS:
            self.on_hold_at = timezone.now()


class ParticipantQuerySet(models.QuerySet):
    def with_amounts(self):
        return self.annotate(
            amount_due=Coalesce(
                "amount_due_modified",
                "amount_due_calculated",
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ),
            amount_payed=Coalesce(
                Sum("payments__amount"),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ),
        ).annotate(
            amount_due_remaining=F("amount_due") - F("amount_payed"),
        )


class ParticipantManager(models.Manager.from_queryset(ParticipantQuerySet)):
    def get_queryset(self):
        return super().get_queryset()


class Participant(models.Model):
    signup_group = models.ForeignKey(
        Signup, on_delete=models.CASCADE, related_name="participants_set"
    )
    first_name = models.CharField("Prénom", max_length=150, blank=False)
    last_name = models.CharField("Nom", max_length=150, blank=False)
    email = models.EmailField(_("e-mail"), blank=True)
    phone = PhoneNumberField(_("N° tel"), blank=True, null=True)
    birthday = models.DateField(_("date de naissance"), blank=False)
    city = models.CharField(_("ville de domicile"), max_length=150, blank=False)
    country = models.CharField(
        _("pays de résidence"), max_length=150, blank=False, default="Belgique"
    )
    vae = models.BooleanField(
        _("VAE"),
        choices=((False, "non"), (True, "oui")),
        default=False,
    )
    arrive_day_before = models.BooleanField(
        _("Arrivée la veille"),
        default=False,
        help_text=_("Le participant arrivera-t-il la veille de l'édition ?"),
    )
    takes_car_back = models.BooleanField(
        _("Rentre en car"),
        default=False,
        help_text=_(
            "Le participant rentre-t-il en car depuis Bastogne vers Namur ou Bruxelles ?"
        ),
    )
    extra_activities = models.CharField(
        _("Proposition d'aide"),
        default="",
        blank=True,
        max_length=300,
        help_text=_("Proposition d'aide"),
    )

    # Jours de participation
    day1 = models.BooleanField(_("17-07"), default=True)
    day2 = models.BooleanField(_("18-07"), default=True)
    day3 = models.BooleanField(_("19-07"), default=True)
    day4 = models.BooleanField(_("20-07"), default=True)
    day5 = models.BooleanField(_("21-07"), default=True)
    day6 = models.BooleanField(_("22-07"), default=True)
    day7 = models.BooleanField(_("23-07"), default=True)
    day8 = models.BooleanField(_("24-07"), default=True)
    day9 = models.BooleanField(_("25-07"), default=True)

    # Champs financiers (de 'reunion')
    amount_due_modified = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    amount_due_calculated = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    payments = GenericRelation(OperationValidation)
    objects = ParticipantManager()

    class Meta:
        verbose_name = "Participant 2026"
        verbose_name_plural = "Participants 2026"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def complete_signup(self):
        return all(
            [
                self.day1,
                self.day2,
                self.day3,
                self.day4,
                self.day5,
                self.day6,
                self.day7,
                self.day8,
                self.day9,
            ]
        )

    def nb_of_days(self):
        return sum(
            [
                self.day1,
                self.day2,
                self.day3,
                self.day4,
                self.day5,
                self.day6,
                self.day7,
                self.day8,
                self.day9,
            ]
        )

    def age_at_dynamobile_end(self):
        last_day = settings.DYNAMOBILE_FIRST_DAY
        birthday = self.birthday
        return (
            last_day.year
            - birthday.year
            - ((last_day.month, last_day.day) < (birthday.month, birthday.day))
        )


class ExtraParticipantInfo(models.Model):
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="extra_info"
    )
    full_address = models.CharField(
        "Addresse complète", max_length=255, default="", blank=True
    )
    emergency_contact = models.CharField(
        "Contact en cas d'urgence", max_length=255, default="", blank=True
    )
    share_contact_info = models.BooleanField("Partage de données", default=False)
    image_rights = models.BooleanField("Droit à l'image", default=False)
    comments = models.TextField("Commentaires", default="", blank=True)

    # Rôles bénévoles
    road_captain = models.BooleanField("Capitaine de route", default=False)
    mechanicien = models.BooleanField("Mécano", default=False)
    healthpro = models.BooleanField("Premiers soins", default=False)
    animator = models.BooleanField("Animations", default=False)

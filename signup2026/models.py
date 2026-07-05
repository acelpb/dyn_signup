from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import models, transaction
from django.db.models import (
    BooleanField,
    Case,
    DecimalField,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from accounts.models import IncomeChoices, OperationValidation


class SignupQuerySet(models.QuerySet):
    def with_amounts(self):
        # amount_payed_total uses a correlated subquery starting from Participant
        # (not from OperationValidation) so that OuterRef("pk") resolves to the
        # signup pk at exactly one nesting level, not to the OV row id.
        # This also removes the OV join from the main query, preventing the
        # multiplication bug where amount_due_total was counted once per OV row.
        payments_subq = Subquery(
            Participant.objects.filter(signup_group_id=OuterRef("pk"))
            .values("signup_group_id")
            .annotate(total=Sum("payments__amount"))
            .values("total")[:1],
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )

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
                    payments_subq,
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
    payment_confirmation_sent_at = models.DateTimeField(
        default=None, null=True, blank=True
    )
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

    def get_admin_url(self):
        from django.urls import reverse

        return reverse("admin:signup2026_signup_change", args=[self.id])

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
        description = ""
        total_price = 0
        child_nb = 0
        participants = self.participants_set.all().order_by("birthday")
        for participant in participants:
            age = participant.age_at_dynamobile_end()
            description += (
                f"prix pour {participant.first_name} {participant.last_name}: "
            )
            for (
                min_age,
                max_age,
                all_days_price,
                upfront_price,
            ) in settings.DYNAMOBILE_PRICES:
                if min_age <= age < max_age:
                    if participant.complete_signup():
                        price = upfront_price + all_days_price
                        description += f"(totalité) {upfront_price} + {all_days_price} "
                    else:
                        nb_days = participant.nb_of_days()
                        price = upfront_price + (all_days_price / 8 * nb_days)
                        description += f"(partiel) {upfront_price} + {all_days_price} / 8 * {nb_days} "

                    if age < 18:
                        reduction = 0
                        if child_nb == 1:
                            reduction = 0.25
                        elif child_nb >= 2:
                            reduction = 0.50
                        price *= 1 - reduction
                        child_nb += 1
                        description += f"enfant {child_nb} réduction {reduction:.0%} "

                    total_price += price
                    description += f"= {price:.2f}€\n"
                    break
            else:
                raise ValueError(
                    f"Aucune tranche de prix pour {participant} (âge {age})"
                )
            participant.amount_due_calculated = price
            participant.save()
        description += f"total: {total_price:.2f}€"
        self.comments = description
        self.save()
        return total_price

    def annotated(self):
        """Re-fetch this signup with the with_amounts() annotations.

        Balance and payment status must always come from the queryset
        annotations (balance, is_payed, ...), never be recomputed in Python.
        """
        return type(self).objects.with_amounts().get(pk=self.pk)

    def accept_excess_as_donation(self, user):
        """Convert a negative balance (overpayment) into a donation.

        Reduces the largest payment validation by the excess and books the
        excess as a donation on the same operation. Returns the converted
        amount. Raises ValueError when the balance is not negative or no
        suitable payment exists.
        """
        balance = self.annotated().balance
        if balance is None or balance >= 0:
            raise ValueError("Balance is not negative.")

        excess = -balance
        participant_ct = ContentType.objects.get_for_model(Participant)
        participant_pks = self.participants_set.values_list("pk", flat=True)
        target = (
            OperationValidation.objects.filter(
                content_type=participant_ct, object_id__in=participant_pks
            )
            .order_by("-amount")
            .first()
        )
        if target is None:
            raise ValueError("No payments found to convert.")
        if target.amount < excess:
            raise ValueError(
                f"The largest single payment validation ({target.amount}) is "
                f"smaller than the excess ({excess}). Please handle manually."
            )

        with transaction.atomic():
            target.amount -= excess
            target.save()
            # The donation is linked to the signup, not a participant: only
            # participant-linked validations count as payments in
            # with_amounts(), so this is what actually zeroes the balance.
            OperationValidation.objects.create(
                operation=target.operation,
                content_type=ContentType.objects.get_for_model(type(self)),
                object_id=self.id,
                amount=excess,
                validation_type=IncomeChoices.DONATION,
                created_by=user,
            )
        return excess

    def offer_refund(self, user):
        """Record refund placeholders for the overpaid participants.

        Checks each participant's balance annotation and creates one
        negative validation per participant whose balance is negative,
        then appends a note to the signup comments. Returns the total
        refund amount. Raises ValueError when no participant is overpaid.
        """
        participant_ct = ContentType.objects.get_for_model(Participant)
        overpaid = list(self.participants_set.with_amounts().filter(balance__lt=0))
        if not overpaid:
            raise ValueError("No participant with a negative balance to refund.")

        with transaction.atomic():
            for participant in overpaid:
                OperationValidation.objects.create(
                    operation=None,
                    content_type=participant_ct,
                    object_id=participant.id,
                    amount=participant.balance,
                    validation_type=IncomeChoices.SIGNUP,
                    created_by=user,
                )
            self.comments = (
                self.comments or ""
            ) + f"\n--- REFUND OFFERED on {timezone.localdate()} ---"
            self.save()
        return sum(-participant.balance for participant in overpaid)

    def release_from_waiting_list(self):
        """Take the signup off the waiting list, recalculate and notify."""
        self.on_hold_at = None
        self.on_hold_vae = False
        self.on_hold_partial = False
        self.save()
        self.calculate_amounts()
        context = {"signup": self.annotated()}
        send_mail(
            subject="Votre inscription à Dynamobile",
            message=get_template("signup2026/email/unblock_waitinglist.txt").render(
                context
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template(
                "signup2026/email/unblock_waitinglist.html"
            ).render(context),
        )

    def send_payment_confirmation_mail(self):
        context = {"signup": self.annotated()}
        send_mail(
            subject="Confirmation de paiement - Dynamobile",
            message=get_template("signup2026/email/email_confirmation.txt").render(
                context
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template(
                "signup2026/email/email_confirmation.html"
            ).render(context),
        )
        self.payment_confirmation_sent_at = timezone.now()
        self.save(update_fields=["payment_confirmation_sent_at"])

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
        return (
            self.annotate(
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
            )
            .annotate(
                balance=F("amount_due") - F("amount_payed"),
            )
            .annotate(
                is_payed=Case(
                    When(balance__lte=Value(0), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
        )

    def with_age(self):
        last_day = settings.DYNAMOBILE_LAST_DAY
        return self.annotate(
            age=(
                last_day.year
                - F("birthday__year")
                - models.ExpressionWrapper(
                    Q(birthday__month__gt=last_day.month)
                    | (
                        Q(birthday__month=last_day.month)
                        & Q(birthday__day__gt=last_day.day)
                    ),
                    output_field=models.IntegerField(),
                )
            )
        )


class ParticipantManager(models.Manager.from_queryset(ParticipantQuerySet)):
    pass


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

    class CarBackChoice(models.TextChoices):
        NO = "no", _("Non")
        BRUSSELS = "brussels", _("Bruxelles")
        NAMUR = "namur", _("Namur")

    takes_car_back = models.CharField(
        _("Rentre en car"),
        max_length=10,
        choices=CarBackChoice.choices,
        default=CarBackChoice.NO,
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

    def get_admin_url(self):
        from django.urls import reverse

        return reverse("admin:signup2026_participant_change", args=[self.id])

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
        last_day = settings.DYNAMOBILE_LAST_DAY
        birthday = self.birthday
        return (
            last_day.year
            - birthday.year
            - ((last_day.month, last_day.day) < (birthday.month, birthday.day))
        )

    @classmethod
    def active_emails(cls):
        """Emails of all active participants and signup owners for the year.

        :return: set of lowercased emails for every validated, non-cancelled,
            non-on-hold signup.
        """
        year = settings.DYNAMOBILE_LAST_DAY.year
        active = set(
            cls.objects.filter(
                signup_group__year=year,
                signup_group__validated_at__isnull=False,
                signup_group__on_hold_at__isnull=True,
                signup_group__cancelled_at__isnull=True,
            ).values_list("email", flat=True)
        )
        active |= set(
            Signup.objects.filter(
                year=year,
                validated_at__isnull=False,
                on_hold_at__isnull=True,
                cancelled_at__isnull=True,
            ).values_list("owner__email", flat=True)
        )
        active.discard("")
        return {email.lower() for email in active if email}


class WaitingListParticipant(Participant):
    class Meta:
        proxy = True
        verbose_name = "Participant en attente 2026"
        verbose_name_plural = "Participants en attente 2026"


class PaymentParticipant(Participant):
    class Meta:
        proxy = True
        verbose_name = "Payement Participant"
        verbose_name_plural = "Payements Participants"


class ExtraParticipantInfo(models.Model):
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="extra_info"
    )
    full_address = models.CharField(
        "Adresse complète", max_length=255, default="", blank=True
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
    tandem_pilot = models.BooleanField("Accompagner Claude (tandem)", default=False)

    class July20LoopChoice(models.TextChoices):
        ABSENT = "absent", _("Je ne suis pas à Dynamobile à cette date.")
        OPTION1 = (
            "option1",
            _(
                "Option 1 : réserve naturelle Haff Réimech "
                "et parc aquatique Erlefnis Baggerweier"
            ),
        )
        OPTION2 = (
            "option2",
            _("Option 2 : boucle sportive via Schengen et la Römer Route"),
        )

    july20_loop = models.CharField(
        _("Boucle du 20 juillet"),
        max_length=10,
        choices=July20LoopChoice.choices,
        blank=True,
        default="",
        help_text=_("Choix de la boucle pour la journée du lundi 20 juillet"),
    )

    def __str__(self):
        return f"Infos complémentaires - {self.participant}"

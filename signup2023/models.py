import decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.mail import send_mail
from django.db import models
from django.db.models import F, Q, Window
from django.db.models.fields import DecimalField
from django.db.models.functions import Coalesce, RowNumber
from django.template.loader import get_template
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from accounts.models import OperationValidation


class Signup(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    year = models.IntegerField(default=settings.DYNAMOBILE_LAST_DAY.year)
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(default=None, null=True, blank=True)
    cancelled_at = models.DateTimeField(default=None, null=True, blank=True)
    on_hold = models.BooleanField(default=False)
    on_hold_vae = models.BooleanField(default=False)
    on_hold_partial = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        unique_together = ("owner_id", "year")

    def __str__(self):
        return f"{self.id} - {self.owner.username}"

    def create_bill(self):
        bill = Bill(
            signup=self,
            created_at=timezone.now(),
        )
        bill.calculate_amount_and_explain()
        bill.amount = bill.calculated_amount
        bill.save()
        send_mail(
            subject="Votre inscription à dynamobile",
            message=get_template("signup/email/email.txt").render(),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template("signup/email/email.html").render(
                {
                    "signup": self,
                    "partial_open": settings.DYNAMOBILE_START_PARTIAL_SIGNUP,
                }
            ),
        )
        return bill

    def update_bill(self):
        new_amount = self.calculate_amount()
        if self.bill.amount != new_amount:
            self.bill.ballance += decimal.Decimal(new_amount) - decimal.Decimal(
                self.bill.amount
            )
            self.bill.amount = new_amount
            self.bill.save()
            send_mail(
                subject="Modification d'inscription à dynamobile",
                message=get_template("signup/email/email_modified.txt").render(),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[self.owner.email, settings.EMAIL_HOST_USER],
                html_message=get_template("signup/email/email_modified.html").render(
                    {"signup": self}
                ),
            )

    def has_vae(self):
        return self.participant_set.filter(vae=True).count()

    def complete_signup(self):
        for participant in self.participant_set.all():
            if not participant.complete_signup():
                return False
        return True

    def waiting_number(self):
        waiting_participants = Participant.objects.filter(
            signup_group__on_hold=True,
            signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
        )
        ordered_participants = waiting_participants.annotate(
            ranking=models.Case(
                models.When(
                    signup_group__validated_at__lt=settings.DYNAMOBILE_START_PARTIAL_SIGNUP,
                    signup_group__on_hold_partial=False,
                    then=models.Value(1),
                ),
                models.When(
                    signup_group__validated_at__lt=settings.DYNAMOBILE_START_PARTIAL_SIGNUP,
                    signup_group__on_hold_partial=True,
                    then=models.Value(2),
                ),
                default=models.Value(3),
            )
        ).annotate(
            final_ranking=Window(
                RowNumber(), order_by=["ranking", "signup_group__validated_at"]
            )
        )

        collect = {
            k: v
            for k, v in ordered_participants.values_list(
                "signup_group_id", "final_ranking"
            )[::-1]
        }
        return collect.get(self.id, 0)

    def check_on_hold_partial(self):
        if (
            not self.complete_signup()
            and settings.DYNAMOBILE_START_PARTIAL_SIGNUP > timezone.now()
        ):
            self.on_hold_partial = True
            self.on_hold = True
            return True

        return False

    def check_max_vae(self):
        if additional_vae := self.has_vae():
            registered_vae_bikes = Participant.objects.filter(
                signup_group__validated_at__isnull=False,
                vae=True,
                signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
            ).count()
            if (
                registered_vae_bikes + additional_vae
                > settings.DYNAMOBILE_MAX_VAE_PARTICIPANTS
            ):
                self.on_hold_vae = True
                self.on_hold = True
                return True

        return False

    def check_max_participants(self):
        nb_of_participants = (
            Participant.objects.filter(
                signup_group__validated_at__isnull=False,
                signup_group__on_hold=False,
                signup_group__cancelled_at__isnull=True,
                signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
            )
            | self.participant_set.all()
        ).count()
        if nb_of_participants > settings.DYNAMOBILE_MAX_PARTICIPANTS:
            self.on_hold = True
        return False

    def check_if_on_hold(self):
        return (
            self.check_on_hold_partial()
            or self.check_max_vae()
            or self.check_max_participants()
        )

    def payed(self):
        if self.bill and self.bill.payed_at is not None:
            return True
        else:
            return False


_TEXT = (
    "Nous cherchons des signaleurs, des capitaines de route. "
    "Si vous avez des talents de mécanicien, de secouriste, ou "
    "si vous vous proposez pour animer une activité en soirée, "
    "merci de nous le faire savoir."
)


class ParticipantManager(models.Manager):
    def get_queryset(self):
        last_day = settings.DYNAMOBILE_LAST_DAY
        return (
            super()
            .get_queryset()
            .annotate(
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
        )


class Participant(models.Model):
    signup_group = models.ForeignKey(Signup, on_delete=models.CASCADE)
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
        max_length=17,
        choices=(
            (False, "non"),
            (True, "oui"),
        ),
        default=False,
        help_text=_("Vélo à assistance électrique"),
        null=False,
    )
    extra_activities = models.CharField(
        "proposition d'aide", max_length=300, help_text=_TEXT, blank=True
    )
    pre_departure = models.BooleanField(
        _("veille"),
        choices=(
            (False, "Non"),
            (True, "Oui"),
        ),
        default=False,
        help_text=(
            "Je souhaite venir la veille du départ (petit-déjeuner et "
            "pique-nique seront prévus pour vous le jour du départ)"
        ),
    )
    day1 = models.BooleanField(_("18-07"), default=True)
    day2 = models.BooleanField(_("19-07"), default=True)
    day3 = models.BooleanField(_("20-07"), default=True)
    day4 = models.BooleanField(_("21-07"), default=True)
    day5 = models.BooleanField(_("22-07"), default=True)
    day6 = models.BooleanField(_("23-07"), default=True)
    day7 = models.BooleanField(_("24-07"), default=True)
    day8 = models.BooleanField(_("25-07"), default=True)
    day9 = models.BooleanField(_("26-07"), default=True)

    objects = ParticipantManager()

    class Meta:
        verbose_name = "Participant"
        verbose_name_plural = "Participants"

    def complete_signup(self):
        return (
            self.day1
            and self.day2
            and self.day3
            and self.day4
            and self.day5
            and self.day6
            and self.day7
            and self.day8
            and self.day9
        )

    def nb_of_days(self):
        return (
            self.day1
            + self.day2
            + self.day3
            + self.day4
            + self.day5
            + self.day6
            + self.day7
            + self.day8
            + self.day9
        )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def age_at_dynamobile_end(self):
        last_day = settings.DYNAMOBILE_FIRST_DAY
        birthday = self.birthday
        return (
            last_day.year
            - birthday.year
            - ((last_day.month, last_day.day) < (birthday.month, birthday.day))
        )

    @classmethod
    def active_emails(cls):
        """Get list of emails of all active particpants + signup_groups.

        :return: List of emails: str for all active participants
        """
        active_participants = set(
            cls.objects.filter(
                signup_group__year=settings.DYNAMOBILE_LAST_DAY.year,
                signup_group__validated_at__isnull=False,
                signup_group__on_hold=False,
                signup_group__cancelled_at__isnull=True,
            ).values_list("email", flat=True)
        )
        active_participants |= set(
            Signup.objects.filter(
                year=settings.DYNAMOBILE_LAST_DAY.year,
                validated_at__isnull=False,
                on_hold=False,
                cancelled_at__isnull=True,
            ).values_list("owner__email", flat=True)
        )
        active_participants.remove("")
        return {x.lower() for x in active_participants}


class BillManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(payed=models.Sum("payments__amount"))
            .annotate(
                ballance=F("amount")
                - Coalesce(F("payed"), 0, output_field=DecimalField())
            )
        )


class Bill(models.Model):
    signup = models.OneToOneField(Signup, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=2, default=0, max_digits=10)

    created_at = models.DateTimeField(auto_now_add=True)
    payed_at = models.DateTimeField(default=None, null=True, blank=True)
    amount_payed_at = models.DecimalField(decimal_places=2, default=0, max_digits=10)
    calculation = models.TextField(blank=True, default="")
    calculated_amount = models.DecimalField(
        decimal_places=2, default=0, max_digits=10, null=True
    )

    payments = GenericRelation(OperationValidation)

    objects = BillManager()

    class Meta:
        verbose_name = "paiement"
        verbose_name_plural = "paiements"

    def __str__(self):
        return f"Paiements pour {self.signup}"

    def send_confirmation_email(self):
        if timezone.now().date() > settings.DYNAMOBILE_LAST_DAY:
            # don't send emails after the end of dynamobile.
            return
        send_mail(
            subject="Confirmation d'inscription à dynamobile",
            message=get_template("signup/email/email_confirmation.txt").render(),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.signup.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template("signup/email/email_confirmation.html").render(
                {"signup": self.signup}
            ),
        )

    def send_payment_confirmation_mail(self):
        self.payed_at = now()
        self.save()
        return send_mail(
            subject="Confirmation de réception du paiement",
            message=get_template("signup/email/email_confirmation.txt").render(),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.signup.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template("signup/email/email_confirmation.html").render(
                {"signup": self.signup}
            ),
        )

    def calculate_amount_and_explain(self):
        description = ""
        child_nb = 0
        total_price = 0
        for participant in self.signup.participant_set.all().order_by("birthday"):
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
                        child_reduction = min(0.5, 0.25 * child_nb)
                        price *= 1 - child_reduction
                        child_nb += 1
                        description += (
                            f"enfant {child_nb} réduction {child_reduction:.0%} "
                        )

                    total_price += price
                    description += f"        = {price:.2f}€\n"
                    break
            else:
                raise Exception("Apparently participant is older than 999.")
        description += f"total: {total_price:.2f}€"
        self.calculation = description
        self.calculated_amount = total_price
        return (total_price, description)


class ExtraParticipantInfo(models.Model):
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE)
    full_address = models.CharField(
        "Addresse complète",
        default="",
        help_text="Nécessaire en cas d'urgence médicale",
    )
    emergency_contact = models.CharField(
        "Contact en cas d'urgence",
        default="",
        help_text="Personne à contacter en cas d'urgence (Nom + lien de parenté éventuel + téléphone)",
    )
    share_contact_info_participants = models.BooleanField(
        "partage de données",
        default=False,
        help_text="Acceptez-vous que nous partagions vos coordonnées avec les autres participant·es?",
    )

    image_rights = models.BooleanField(
        "droit à l'image",
        default=False,
        help_text="Acceptez-vous que des photos ou vidéos vous représentant soient diffusées sur les canaux de communication de Dynamobile (site, page Facebook privée)?",
    )

    comments = models.TextField(
        "commentaires", default="", blank=True, help_text="commentaires éventuels"
    )

    road_captain = models.BooleanField(
        "capitaine de route",
        default=False,
        help_text="Je propose mon aide comme capitaine de route (Age minimum 21 ans).",
    )
    mechanicien = models.BooleanField(
        "mécano",
        default=False,
        help_text="Je propose mon aide pour réparer les vélos.",
    )
    healthpro = models.BooleanField(
        "premiers soins",
        default=False,
        help_text="Je propose mon aide comme secouriste / infirmièr·e / médecin.",
    )
    animator = models.BooleanField(
        "Animations en fin de journée",
        default=False,
        help_text="Je propose une animation, précisez ci-dessous.",
    )

    activite_21 = models.TextField(
        "Activité choisie le 21/07",
        choices=(
            ("absent", "Je suis inscrit.e en partiel. Je ne suis pas là ce jour-là."),
            ("Wégimont", "Domaine provincial de Wégimont, avec piscine"),
            ("Boucle cycliste", "Boucle cycliste militante (65km)"),
        ),
        default="-",
        null=False,
        blank=False,
    )

    activite_25 = models.TextField(
        "Activité choisie le 25/07",
        choices=(
            ("absent", "Je suis inscrit.e en partiel. Je ne suis pas là ce jour-là."),
            ("-", "Pause de midi libre au grand air"),
            ("cidrerie", "Visite cidrerie (6,5 eur p/p)"),
            ("automates", "Visite musée des automates (5 eur p/p)"),
        ),
        default="-",
        null=False,
        blank=False,
    )

    roadbook = models.BooleanField(
        "carnet de route",
        default=False,
        help_text="Je souhaite recevoir le carnet de route en version pdf interactive.",
    )

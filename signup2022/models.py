import decimal
import time
from functools import cached_property

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import models
from django.db.models import Subquery, OuterRef, F

from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import SignupOperation, OperationValidation


# Create your models here.


class Signup(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(default=None, null=True)
    on_hold = models.BooleanField(default=False)
    on_hold_vae = models.BooleanField(default=False)
    on_hold_partial = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(default=None, null=True, blank=True)

    class Meta:
        verbose_name = 'Inscription'
        verbose_name_plural = 'Inscriptions'

    def __str__(self):
        return f"{self.owner.username}"

    def calculate_amount(self):
        return self.bill.amount or 0
        raise Exception("Don't use this anymore")

    def create_bill(self):
        amount = self.calculate_amount()
        bill = Bill.objects.create(
            signup=self,
            amount=amount,
            ballance=amount,
            created_at=timezone.now(),
        )
        send_mail(
            subject="Votre inscription à dynamobile",
            message=get_template('signup/email/email.txt').render(),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template('signup/email/email.html').render({"signup": self}),
        )
        return bill

    def update_bill(self):
        new_amount = self.calculate_amount()
        if self.bill.amount != new_amount:
            self.bill.ballance += decimal.Decimal(new_amount) - decimal.Decimal(self.bill.amount)
            self.bill.amount = new_amount
            self.bill.save()
            send_mail(
                subject="Modification d'inscription à dynamobile",
                message=get_template('signup/email/email_modified.txt').render(),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[self.owner.email, settings.EMAIL_HOST_USER],
                html_message=get_template('signup/email/email_modified.html').render({"signup": self}),
            )

    def has_vae(self):
        return self.participant_set.filter(vae=True).count()

    def complete_signup(self):
        for participant in self.participant_set.all():
            if not participant.complete_signup():
                return False
        return True

    def waiting_number(self):
        return Signup.objects.filter(validated_at__lt=self.validated_at, on_hold=True).count() + 1

    def check_on_hold_partial(self):
        if not self.complete_signup() and settings.DYNAMOBILE_START_PARTIAL_SIGNUP > timezone.now():
            self.on_hold_partial = True
            self.on_hold = True
            return True

        return False

    def check_max_vae(self):
        if additional_vae := self.has_vae():
            registered_vae_bikes = Participant.objects.filter(
                signup_group__validated_at__isnull=False,
                vae=True
            ).count()
            if registered_vae_bikes + additional_vae > settings.DYNAMOBILE_MAX_VAE_PARTICIPANTS:
                self.on_hold_vae = True
                self.on_hold = True
                return True

        return False

    def check_max_participants(self):
        nb_of_participants = (
                Participant.objects.filter(
                    signup_group__validated_at__isnull=False,
                    signup_group__on_hold=False,
                ) | self.participant_set.all()
        ).count()
        if nb_of_participants > settings.DYNAMOBILE_MAX_PARTICIPANTS:
            self.on_hold = True
        return False

    def check_if_on_hold(self):
        return (
                self.check_on_hold_partial() or
                self.check_max_vae() or
                self.check_max_participants()
        )


class Participant(models.Model):
    signup_group = models.ForeignKey(Signup, on_delete=models.CASCADE)
    first_name = models.CharField(_("Prénom"), max_length=150, blank=False)
    last_name = models.CharField(_("Nom de Famille"), max_length=150, blank=False)
    email = models.EmailField(_("adresse e-mail"), blank=True)
    birthday = models.DateField(_("date de naissance"), blank=False)
    city = models.CharField(_("ville de domicile"), max_length=150, blank=False)
    country = models.CharField(
        _("pays de résidence"), max_length=150, blank=False, default="Belgique"
    )
    vae = models.BooleanField(_('VAE'), help_text=_('Vélo à assistance électrique'), null=False)
    d2022_07_18 = models.BooleanField(_("18-07"), default=False)
    d2022_07_19 = models.BooleanField(_("19-07"), default=False)
    d2022_07_20 = models.BooleanField(_("20-07"), default=False)
    d2022_07_21 = models.BooleanField(_("21-07"), default=False)
    d2022_07_22 = models.BooleanField(_("22-07"), default=False)
    d2022_07_23 = models.BooleanField(_("23-07"), default=False)
    d2022_07_24 = models.BooleanField(_("24-07"), default=False)
    d2022_07_25 = models.BooleanField(_("25-07"), default=False)

    class Meta:
        verbose_name = 'Participant'
        verbose_name_plural = 'Participants'

    def complete_signup(self):
        return (
                self.d2022_07_18 and
                self.d2022_07_19 and
                self.d2022_07_20 and
                self.d2022_07_21 and
                self.d2022_07_22 and
                self.d2022_07_23 and
                self.d2022_07_24 and
                self.d2022_07_25
        )

    def nb_of_days(self):
        return (
                self.d2022_07_18 +
                self.d2022_07_19 +
                self.d2022_07_20 +
                self.d2022_07_21 +
                self.d2022_07_22 +
                self.d2022_07_23 +
                self.d2022_07_24 +
                self.d2022_07_25
        )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def age_at_dynamobile_end(self):
        last_day = settings.DYNAMOBILE_LAST_DAY
        birthday = self.birthday
        return last_day.year - birthday.year - (
                (last_day.month, last_day.day) < (birthday.month, birthday.day)
        )

    @classmethod
    def active_emails(cls):
        """Get list of emails of all active particpants + signup_groups.

        :return: List of emails: str for all active participants
        """
        active_participants = set(
            cls.objects.filter(signup_group__validated_at__isnull=False,
                               signup_group__cancelled_at__isnull=True).values_list("email", flat=True))
        active_participants |= set(
            Signup.objects.filter(validated_at__isnull=False,
                                  cancelled_at__isnull=True).values_list('owner__email', flat=True))
        active_participants.remove("")
        return {x.lower() for x in active_participants}


class BillManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().annotate(
            payed=models.Sum('payments__amount')
        ).annotate(
            ballance=F('amount') - F("payed")
        )


class Bill(models.Model):
    signup = models.OneToOneField(Signup, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=2, default=0, max_digits=10)

    created_at = models.DateTimeField(auto_now_add=True)
    payed_at = models.DateTimeField(default=None, null=True, blank=True)
    amount_payed_at = models.DecimalField(decimal_places=2, default=0, max_digits=10)
    calculation = models.TextField(blank=True, default="")
    calculated_amount = models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True)
    corrected_amount = models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True)

    payments = GenericRelation(OperationValidation)

    objects = BillManager()

    class Meta:
        verbose_name = 'paiement'
        verbose_name_plural = 'paiements'

    def __str__(self):
        return f"Paiements pour {self.signup}"

    def send_confirmation_email(self):
        if timezone.now().date() > settings.DYNAMOBILE_LAST_DAY:
            # don't send emails after the end of dynamobile.
            return
        send_mail(
            subject="Confirmation d'inscription à dynamobile",
            message=get_template('signup/email/email_confirmation.txt').render(),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[self.signup.owner.email, settings.EMAIL_HOST_USER],
            html_message=get_template('signup/email/email_confirmation.html').render({"signup": self.signup}),
        )

    def calculate_amount_and_explain(self):
        description = ""
        child_nb = 0
        total_price = 0
        for participant in self.signup.participant_set.all().order_by('birthday'):
            age = participant.age_at_dynamobile_end()
            description += f"prix pour {participant.first_name} {participant.last_name}: "
            for min_age, max_age, all_days_price, upfront_price in settings.DYNAMOBILE_PRICES:
                if age < max_age:
                    if participant.complete_signup():
                        price = upfront_price + all_days_price
                        description += f"(totalité) {upfront_price} + {all_days_price} "
                    else:
                        nb_days = participant.nb_of_days()
                        price = upfront_price + (all_days_price / 7 * nb_days)
                        description += f"(partiel) {upfront_price} + {all_days_price} / 7 * {nb_days} "

                    if age < 18:
                        child_reduction = min(0.5, 0.25 * child_nb)
                        price *= 1 - child_reduction
                        child_nb += 1
                        description += f"enfant {child_nb} réduction {child_reduction:.0%} "

                    total_price += price
                    description += f"        = {price:.2f}€\n"
                    break
            else:
                raise Exception('Apparently participant is older than 999.')
        description += f"total: {total_price:.2f}€"
        return (total_price, description)

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.


class Signup(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(default=None, null=True)
    cancelled_at = models.DateTimeField(default=None, null=True)


class Participant(models.Model):
    signup_group = models.ForeignKey(Signup, on_delete=models.CASCADE)
    first_name = models.CharField(_("Prénom"), max_length=150, blank=False)
    last_name = models.CharField(_("Nom de Famille"), max_length=150, blank=False)
    email = models.EmailField(_("adresse e-mail"), blank=True)
    birthday = models.DateField(_("date de naissance"), blank=False)
    city = models.CharField(_("ville de domicile"), max_length=150, blank=False)
    country = models.CharField(
        _("pays de résidence"), max_length=150, blank=False, default="Belgium"
    )
    vae = models.BooleanField(_('VAE'), help_text=_('Vélo à assistance électrique'), null=False)


class DaySignup(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    day = models.DateField(
        choices=settings.DYNAMOBILE_DAYS,
        validators=[
            MinValueValidator(settings.DYNAMOBILE_FIRST_DAY),
            MaxValueValidator(settings.DYNAMOBILE_LAST_DAY),
        ],
    )
    created_at = models.DateField(auto_now_add=True)
    cancelled = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "participant",
                    "day",
                ),
                name="no double counting",
            ),
        ]


class Bill(models.Model):
    signup = models.OneToOneField(Signup, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=2, default=0, max_digits=10)
    ballance = models.DecimalField(decimal_places=2, default=0, max_digits=10)
    created_at = models.DateTimeField(auto_now_add=True)
    payed_at = models.DateTimeField(default=None, null=True)

from django.conf import settings
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

    def __str__(self):
        return f"Groupe de {self.owner.username}"


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

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Bill(models.Model):
    signup = models.OneToOneField(Signup, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=2, default=0, max_digits=10)
    ballance = models.DecimalField(decimal_places=2, default=0, max_digits=10)
    created_at = models.DateTimeField(auto_now_add=True)
    payed_at = models.DateTimeField(default=None, null=True)

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.


class Signup(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )


class Participant(models.Model):
    signup_group = models.ForeignKey(Signup, on_delete=models.CASCADE)
    first_name = models.CharField(_("first name"), max_length=150, blank=False)
    last_name = models.CharField(_("last name"), max_length=150, blank=False)
    email = models.EmailField(_("email address"), blank=True)
    birthday = models.DateField(_("date of birth"), blank=False)
    city = models.CharField(_("city of residence"), max_length=150, blank=False)
    country = models.CharField(
        _("country of residence"), max_length=150, blank=False, default="Belgium"
    )


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

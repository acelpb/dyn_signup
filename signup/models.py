from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class Signup(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)


class Ride(models.Model):
    title = models.CharField(max_length=220)
    guide = models.CharField(max_length=220)
    description = models.TextField()
    max_participants = models.IntegerField()

    def __str__(self):
        return self.title

    def available(self):
        return max(int((self.max_participants * 0.9) - self.participant_set.count()), 0)

    class Meta:
        verbose_name = _("ride")


class Participant(models.Model):
    signup = models.ForeignKey(Signup, on_delete=models.CASCADE, verbose_name=_('signup'))
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, verbose_name=_('ride'))
    firstname = models.CharField(max_length=56, verbose_name=_('firstname'))
    lastname = models.CharField(max_length=56, verbose_name=_('lastname'))
    address = models.CharField(max_length=220, verbose_name=_('address'))
    adult = models.BooleanField(default=True, verbose_name=_('adult'))

    def __repr__(self):
        return f"{self.firstname} {self.lastname}"

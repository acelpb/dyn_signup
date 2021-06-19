from django.db import models
from django.conf import settings
from django.contrib.auth import apps


# Create your models here.
class Signup(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)


class Ballad(models.Model):
    title = models.CharField(max_length=220)
    description = models.TextField()
    max_participants = models.IntegerField()


class Participant(models.Model):
    signup = models.ForeignKey(Signup, on_delete=models.CASCADE)
    ballad = models.ForeignKey(Ballad, on_delete=models.CASCADE)
    firstname = models.CharField(max_length=56)
    lastname = models.CharField(max_length=56)
    address = models.CharField(max_length=220)
    adult = models.BooleanField(default=True)

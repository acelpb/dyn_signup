from django.contrib import admin

from .models import Participant, Signup

# Register your models here.


@admin.register(Signup)
class SignupAmin(admin.ModelAdmin):
    pass


@admin.register(Participant)
class ParticipantAmin(admin.ModelAdmin):
    pass

from django.contrib import admin

# Register your models here.
from .models import Signup, Ballad, Participant


@admin.register(Signup)
class SignupAdmin(admin.ModelAdmin):
    pass


@admin.register(Ballad)
class BalladAdmin(admin.ModelAdmin):
    pass


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    pass

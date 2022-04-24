from django.contrib import admin
from .models import Participant
# Register your models here.


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name')



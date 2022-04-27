from django.contrib import admin

from .models import Participant, Signup


# Register your models here.

class ParticipantInfoInline(admin.StackedInline):
    verbose_name = "Information Participants"
    model = Participant
    extra = 0
    fields = (
        "first_name", "last_name", "email", "birthday", "city", "country"
    )

class ParticipantDaysInline(admin.TabularInline):
    verbose_name = "Présences Participants"
    model = Participant
    extra = 0
    fields = (
        "d2022_07_18",
        "d2022_07_19",
        "d2022_07_20",
        "d2022_07_21",
        "d2022_07_22",
        "d2022_07_23",
        "d2022_07_24",
        "d2022_07_25",
    )


@admin.register(Signup)
class SignupAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'validated_at')
    inlines = [ParticipantInfoInline, ParticipantDaysInline]


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'first_name',
        'last_name',
        'd2022_07_18',
        'd2022_07_19',
        'd2022_07_20',
        'd2022_07_21',
        'd2022_07_22',
        'd2022_07_23',
        'd2022_07_24',
        'd2022_07_25',
        "vae",
    )
    list_filter = (
        'd2022_07_18',
        'd2022_07_19',
        'd2022_07_20',
        'd2022_07_21',
        'd2022_07_22',
        'd2022_07_23',
        'd2022_07_24',
        'd2022_07_25',
        "vae",
    )

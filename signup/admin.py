import csv

from django.contrib import admin
# Register your models here.
from django.http import HttpResponse

from .models import Signup, Ballad, Participant


@admin.register(Signup)
class SignupAdmin(admin.ModelAdmin):
    pass


@admin.register(Ballad)
class BalladAdmin(admin.ModelAdmin):
    pass


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        'ballad',
        'firstname',
        'lastname',
        'adult'
    )

    actions = ["export_as_csv"]

    def export_as_csv(self, request, queryset):
        fields = [
            'firstname',
            'lastname',
            'address',
            'ballad__title',
            'adult',
        ]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=participants.csv'
        writer = csv.writer(response)

        writer.writerow(fields)
        for values in queryset.values_list(*fields):
            row = writer.writerow(values)
        return response

    export_as_csv.short_description = "Export Selected"

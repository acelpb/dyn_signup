import csv

from django.contrib import admin
# Register your models here.
from django.db.models import F, TextField
from django.db.models.functions import Coalesce
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
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_responsable=Coalesce(F('signup__user__username'), F('signup_id'), output_field=TextField()))

    list_display = (
        'responsable',
        'firstname',
        'lastname',
        'ballad',
        'adult'
    )

    def responsable(self, obj):
        return obj._responsable

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

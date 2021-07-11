import csv

from django.contrib import admin
# Register your models here.
from django.db.models import F, Count
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .models import Signup, Ride, Participant


class ParticipantInline(admin.TabularInline):
    can_delete = True
    model = Participant
    fields = (
        'group_link',
        'firstname',
        'lastname',
        'email',
        'adult'
    )
    readonly_fields = ('group_link', )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_group=F('signup_id'))

    def group_link(self, obj):
        return mark_safe(
            '<a href="%s">%s</a>' % (reverse("admin:signup_signup_change", args=(obj._group,)), escape(obj._group)))

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Signup)
class SignupAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'firstname',
        'lastname',
    )
    inlines = [
        ParticipantInline,
    ]
    readonly_fields = ('user',)

    def firstname(self, obj):
        first_participant = obj.participant_set.first()
        if first_participant:
            return first_participant.firstname
        else:
            return ""

    def lastname(self, obj):
        first_participant = obj.participant_set.first()
        if first_participant:
            return first_participant.lastname
        else:
            return ""


@admin.register(Ride)
class BalladAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        "guide",
        'participants_inscrits',
        'max_participants',
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_participants=Count('participant'))

    def participants_inscrits(self, obj):
        return obj._participants

    inlines = [
        ParticipantInline
    ]


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    actions = ["export_as_csv"]
    list_display = (
        'group_link',
        'ride',
        'firstname',
        'lastname',
        'email',
        'adult'
    )
    list_display_links = ('firstname', 'lastname',)
    search_fields = ['firstname', 'lastname']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_group=F('signup_id'))

    def group(self, obj):
        return obj._group

    def group_link(self, obj):
        return mark_safe(
            '<a href="%s">%s</a>' % (reverse("admin:signup_signup_change", args=(obj._group,)), escape(obj._group)))

    group_link.allow_tags = True
    group_link.short_description = "Group"

    def export_as_csv(self, request, queryset):
        fields = [
            '_group',
            'firstname',
            'lastname',
            'address',
            'email',
            'ride__title',
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

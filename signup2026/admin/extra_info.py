from django.contrib import admin
from import_export.admin import ExportMixin
from import_export.resources import ModelResource

from ..models import ExtraParticipantInfo


class ExtraInfoRessource(ModelResource):
    class Meta:
        model = ExtraParticipantInfo
        fields = (
            "id",
            "participant__signup_group_id",
            "participant__last_name",
            "participant__first_name",
            "participant",
            "full_address",
            "emergency_contact",
            "participant__arrive_day_before",
            "participant__takes_car_back",
            "share_contact_info",
            "image_rights",
            "july20_loop",
            "road_captain",
            "mechanicien",
            "healthpro",
            "animator",
            "tandem_pilot",
            "comments",
        )


@admin.register(ExtraParticipantInfo)
class ExtraParticipantInfoAdmin(ExportMixin, admin.ModelAdmin):
    resource_classes = [ExtraInfoRessource]

    list_display = (
        "id",
        "participant__signup_group",
        "participant__last_name",
        "participant__first_name",
        "participant",
        "full_address",
        "emergency_contact",
        "share_contact_info",
        "image_rights",
        "july20_loop",
        "road_captain",
        "mechanicien",
        "healthpro",
        "animator",
        "tandem_pilot",
        "comments",
    )

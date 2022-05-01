from datetime import timezone

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Participant, Signup


@receiver(post_save, sender=Signup)
def create_bill(sender, *, instance, **kwargs):
    group = instance
    if group.validated_at is not None and group.on_hold is False:
        try:
            group.bill
        except Signup.bill.RelatedObjectDoesNotExist as err:
            if not group.complete_signup() and settings.DYNAMOBILE_START_PARTIAL_SIGNUP > timezone.now():
                group.on_hold_partial = True
                group.on_hold = True
                group.save()
                return

            nb_of_vae = group.has_vae()
            if nb_of_vae:
                registered_vae_bikes = Participant.objects.filter(signup_group__validated_at__isnull=False,
                                                                  vae=True).count()
                if registered_vae_bikes + nb_of_vae > settings.DYNAMOBILE_MAX_VAE_PARTICIPANTS:
                    group.on_hold_vae = True
                    group.on_hold = True
                    group.save()
                    return

            nb_of_participants = Participant.objects.filter(
                signup_group__validated_at__isnull=False,
                signup_group__on_hold=False,
            ).count()

            if nb_of_participants > settings.DYNAMOBILE_MAX_PARTICIPANTS:
                group.on_hold = True
                group.save()
                return

            instance.create_bill()


@receiver(post_save, sender=Participant)
def update_bill(sender, *, instance, **kwargs):
    if instance.signup_group.validated_at is not None:
        instance.update_bill()

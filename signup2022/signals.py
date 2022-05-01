from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Participant, Signup, Bill


@receiver(post_save, sender=Signup)
def create_bill(sender, *, instance, **kwargs):
    if instance.validated_at is not None:
        try:
            instance.bill
        except Signup.bill.RelatedObjectDoesNotExist as err:
            instance.create_bill()


@receiver(post_save, sender=Participant)
def update_bill(sender, *, instance, **kwargs):
    if instance.signup_group.validated_at is not None:
        instance.update_bill()

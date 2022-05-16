from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.template.loader import get_template
from django.utils import timezone

from .models import Participant, Signup, Bill


@receiver(post_save, sender=Signup)
def create_bill(sender, *, instance, **kwargs):
    group = instance
    if group.validated_at is not None and group.on_hold is False:
        try:
            group.bill
        except Signup.bill.RelatedObjectDoesNotExist as err:
            instance.create_bill()


@receiver(post_save, sender=Participant)
@receiver(post_delete, sender=Participant)
def update_bill(sender, *, instance, **kwargs):
    signup = instance.signup_group
    if signup.validated_at is not None and signup.on_hold is False and hasattr(signup, "bill"):
        instance.signup_group.update_bill()


@receiver(post_save, sender=Bill)
def confirm_payment(sender, *, instance: Bill, **kwargs):
    if instance.payed_at is None and instance.ballance <= 0:
        instance.payed_at = timezone.now()
        instance.save()
        instance.send_confirmation_email()

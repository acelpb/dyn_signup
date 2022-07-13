from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import SignupOperation
from .models import Participant, Signup, Bill


@receiver(post_save, sender=Signup)
def create_bill(sender, *, instance, **kwargs):
    group = instance
    if group.validated_at is not None and group.on_hold is False and group.cancelled_at is None:
        try:
            group.bill
        except Signup.bill.RelatedObjectDoesNotExist as err:
            instance.create_bill()
    if group.cancelled_at is not None:
        group.participant_set.delete()


@receiver(post_save, sender=Participant)
@receiver(post_delete, sender=Participant)
def update_bill(sender, *, instance, **kwargs):
    signup = instance.signup_group
    if signup.validated_at is not None and signup.on_hold is False and hasattr(signup, "bill"):
        instance.signup_group.update_bill()


@receiver(pre_save, sender=Bill)
def confirm_payment(sender, *, instance: Bill, **kwargs):
    if instance.payed_at is None and instance.ballance <= 0:
        instance.payed_at = timezone.now()
        instance.amount_payed_at = instance.amount - instance.ballance
        instance.save()
        instance.send_confirmation_email()


@receiver(post_save, sender=SignupOperation)
def confirm_payment(sender, *, instance: SignupOperation, **kwargs):
    bill = instance.event.bill
    if bill.payed_at and bill.amount_payed_at == instance.amount:
        pass
    else:
        bill.ballance -= instance.amount
        bill.save()

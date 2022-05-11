from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
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

            nb_of_participants = (
                    Participant.objects.filter(
                        signup_group__validated_at__isnull=False,
                        signup_group__on_hold=False,
                    ) | group.participant_set.all()
            ).count()

            if nb_of_participants > settings.DYNAMOBILE_MAX_PARTICIPANTS:
                group.on_hold = True
                group.save()
                send_mail(
                    subject="Inscription Validée",
                    message=get_template('signup/email/email.txt').render(),
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[instance.signup.owner.email],
                    html_message=get_template('signup/email/email.html').render({"signup": self}),
                )


@receiver(post_save, sender=Participant)
def update_bill(sender, *, instance, **kwargs):
    signup = instance.signup_group
    if signup.validated_at is not None and signup.on_hold is False:
        instance.signup_group.update_bill()


@receiver(post_save, sender=Bill)
def update_bill(sender, *, instance: Bill, **kwargs):
    if instance.payed_at is None and instance.ballance <= 0:
        instance.payed_at = timezone.now()
        instance.save()
        instance.send_confirmation_email()

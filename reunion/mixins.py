from django.conf import settings
from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseRedirect
from django.utils import timezone

from .models import Signup


class SignupStartedMixin(AccessMixin):
    """Verify that the current user is authenticated."""

    def get_object(self, queryset=None):
        signup, _ = Signup.objects.get_or_create(
            owner=self.request.user,
        )
        return signup

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return self.handle_no_permission()
        signup_not_started = timezone.now() < settings.DYNAMOBILE_START_SIGNUP
        user_can_pre_signup = user.groups.filter(name="préinscriptions").exists()
        if signup_not_started and not user_can_pre_signup:
            return HttpResponseRedirect("")

        signup = self.get_object()
        if signup.validated_at is not None:
            return HttpResponseRedirect("/review/")

        return super().dispatch(request, *args, **kwargs)

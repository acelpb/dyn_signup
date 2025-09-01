from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseRedirect
from django.urls import reverse

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

        signup = self.get_object()
        if signup.validated_at is not None:
            return HttpResponseRedirect(reverse("reunion:completed_signup"))

        return super().dispatch(request, *args, **kwargs)

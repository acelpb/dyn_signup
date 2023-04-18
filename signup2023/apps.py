from django.apps import AppConfig


class Signup2023Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "signup2023"
    verbose_name = "Inscriptions 2022"

    def ready(self):
        # Implicitly connect a signal handlers decorated with @receiver.
        from . import signals  # NOQA

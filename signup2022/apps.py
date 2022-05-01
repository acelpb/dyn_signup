from django.apps import AppConfig


class Signup2022Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'signup2022'

    def ready(self):
        # Implicitly connect a signal handlers decorated with @receiver.
        from . import signals  # NOQA

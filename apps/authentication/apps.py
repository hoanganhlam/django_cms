from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    name = 'apps.authentication'

    def ready(self):
        from apps.authentication import signals

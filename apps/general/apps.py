from django.apps import AppConfig


class GeneralConfig(AppConfig):
    name = 'apps.general'

    def ready(self):
        from apps.general import signals
        from apps.activity import registry
        from apps.activity.models import Action
        registry.register(Action)
